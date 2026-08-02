#!/usr/bin/env python3
"""
Gera o site estatico a partir da ultima recolha.

Le os CSV mais recentes em results/ (ou recebe os dados via run_real.py),
injeta no template e escreve site/dist/index.html - uma pagina unica, sem
dependencias externas, pronta para o GitHub Pages.

Uso:
    python3 build_site.py            # usa o CSV mais recente
    python3 build_site.py --vazio    # gera pagina sem vagas (primeiro deploy)
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).parent
TEMPLATE = RAIZ / "site" / "template.html"
DESTINO = RAIZ / "site" / "dist" / "index.html"
RESULTS = RAIZ / "results"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_legivel(dt: datetime) -> str:
    return f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}, {dt:%H:%M}"


def csv_mais_recente(padrao: str):
    arquivos = sorted(RESULTS.glob(padrao))
    return arquivos[-1] if arquivos else None


def carregar_kanban():
    """Estado do Kanban, se existir. Senao, deriva das vagas adequadas."""
    estado = RESULTS / "kanban_state.json"
    if estado.exists():
        try:
            dados = json.loads(estado.read_text())
            return list(dados.get("cards", {}).values())
        except (json.JSONDecodeError, OSError):
            pass
    return []


def montar_vagas(cards, df_adequadas):
    """Cards do Kanban tem prioridade; vagas novas do CSV entram como 'descoberta'."""
    vistos = set()
    vagas = []

    for c in cards:
        vagas.append({
            "id": c["id"][:8],
            "title": c.get("title", ""),
            "company": c.get("company") or "Não informado",
            "location": c.get("location") or "",
            "salary": c.get("salary") or "",
            "url": c.get("url", ""),
            "platform": c.get("platform") or "",
            "score": int(c.get("score", 0)),
            "fase": c.get("fase", "descoberta"),
            "notas": c.get("notas") or "",
        })
        vistos.add(c["id"][:8])

    if df_adequadas is not None and not df_adequadas.empty:
        for _, j in df_adequadas.iterrows():
            curto = str(j["id"])[:8]
            if curto in vistos:
                continue
            vagas.append({
                "id": curto,
                "title": str(j.get("title", "")),
                "company": str(j.get("company") or "Não informado"),
                "location": str(j.get("location") or ""),
                "salary": str(j.get("salary") or ""),
                "url": str(j.get("url", "")),
                "platform": str(j.get("platform") or ""),
                "score": int(j.get("score", 0)),
                "fase": "descoberta",
                "notas": "",
            })
            vistos.add(curto)

    vagas.sort(key=lambda v: -v["score"])
    return vagas


def montar_portais(df_todas, vagas):
    """Contagem por portal: quantas entraram no quadro."""
    aceites = {}
    for v in vagas:
        p = v["platform"] or "Outro"
        aceites[p] = aceites.get(p, 0) + 1

    total = {}
    if df_todas is not None and not df_todas.empty and "platform" in df_todas.columns:
        for p, n in df_todas["platform"].value_counts().items():
            total[str(p)] = int(n)

    nomes = set(aceites) | set(total)
    saida = []
    for nome in sorted(nomes):
        a = aceites.get(nome, 0)
        t = total.get(nome, a)
        saida.append({"nome": nome, "aceites": a, "fora": max(0, t - a)})
    saida.sort(key=lambda x: -x["aceites"])
    return saida


def montar_descartadas(df_todas, limite=25):
    if df_todas is None or df_todas.empty or "blocked" not in df_todas.columns:
        return []
    fora = df_todas[df_todas["blocked"].fillna("").astype(str).str.strip() != ""]
    itens = []
    for _, j in fora.head(limite).iterrows():
        itens.append({
            "title": str(j.get("title", ""))[:80],
            "motivo": str(j.get("blocked", ""))[:60],
        })
    return itens


def main():
    vazio = "--vazio" in sys.argv

    df_todas = df_ok = None
    if not vazio:
        f_todas = csv_mais_recente("real_all_*.csv")
        f_ok = csv_mais_recente("real_suitable_*.csv")
        if f_todas:
            df_todas = pd.read_csv(f_todas)
        if f_ok:
            df_ok = pd.read_csv(f_ok)

    cards = [] if vazio else carregar_kanban()
    vagas = montar_vagas(cards, df_ok)
    portais = montar_portais(df_todas, vagas)
    descartadas = montar_descartadas(df_todas)
    recolha = data_legivel(datetime.now())

    template = TEMPLATE.read_text()
    if "<!--DADOS-->" not in template:
        raise SystemExit("template sem marcador <!--DADOS-->")

    dados = (
        "<script>\n"
        f"const VAGAS = {json.dumps(vagas, ensure_ascii=False, separators=(',', ':'))};\n"
        f"window.PORTAIS = {json.dumps(portais, ensure_ascii=False, separators=(',', ':'))};\n"
        f"window.DESCARTADAS = {json.dumps(descartadas, ensure_ascii=False, separators=(',', ':'))};\n"
        f"window.RECOLHA = {json.dumps(recolha, ensure_ascii=False)};\n"
        "</script>"
    )

    html = template.replace("<!--DADOS-->", dados)

    # O template nasceu como Artifact (sem <html>/<head>). Para o Pages,
    # embrulhar num documento completo.
    if "<!doctype" not in html.lower():
        html = (
            "<!doctype html>\n<html lang=\"pt\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            "<link rel=\"icon\" href=\"data:image/svg+xml,"
            "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
            "%3Ctext y='.9em' font-size='90'%3E%F0%9F%8D%BD%EF%B8%8F%3C/text%3E%3C/svg%3E\">\n"
            f"{html}\n</body>\n</html>\n"
        ).replace("<title>", "<title>", 1)
        # fecha o head logo apos o title e abre o body antes do conteudo
        html = re.sub(r"(</title>)", r"\1\n</head>\n<body>", html, count=1)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(html)

    print(f"site gerado: {DESTINO}")
    print(f"  vagas:       {len(vagas)}")
    print(f"  portais:     {len(portais)}")
    print(f"  descartadas: {len(descartadas)}")
    print(f"  recolha:     {recolha}")
    print(f"  tamanho:     {DESTINO.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
