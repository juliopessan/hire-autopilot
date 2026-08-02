"""
Scoring v2 - corrige os falsos positivos do v1.

Problemas do v1 (todos confirmados em dados reais):
  - Buscava palavras no corpo inteiro, incluindo menu do site e vagas vizinhas.
  - "Barista" descartada porque o texto dizia "report to the Manager on shift".
  - "Chef De Partie" casou com "Catering Assistant" vindo do widget "Next job".
  - "Young applicant signal" em 100% das vagas, vindo do menu "Apprenticeships".

Regras do v2:
  - Papel e senioridade sao decididos pelo TITULO.
  - O corpo e limpo (menu/navegacao/vagas vizinhas) antes de ser lido.
  - No corpo so contam frases inequivocas, nao palavras soltas.
"""

import re
from typing import List, Tuple

# Cargos senior: se aparecem no TITULO, a vaga nao e primeiro emprego.
SENIOR_NO_TITULO = [
    "head chef", "sous chef", "chef de partie", "chef d partie", "demi chef",
    "executive chef", "manager", "supervisor", "team leader", "assistant manager",
    "general manager", "duty manager", "head of", "director",
]

# Frases no corpo que realmente barram um candidato de 17 anos.
# Exigem construcao inequivoca - nao basta a palavra aparecer.
BARREIRAS_NO_CORPO = [
    r"must be (?:over )?18", r"18\+ only", r"over 18s only",
    r"aged 18 or over", r"minimum age(?: of)? 18",
    r"personal licence holder", r"must hold a personal licence",
    r"full(?:,)? clean driving licence required",
    r"minimum (?:of )?(?:2|3|4|5|two|three|four|five) years(?:')? experience",
]

# Sinais de vaga de entrada - frases, nao palavras soltas.
SINAIS_ENTRADA = [
    r"no experience (?:is )?(?:necessary|required|needed)",
    r"full training (?:is )?(?:provided|given)",
    r"training (?:is )?provided",
    r"entry[- ]level", r"school leaver", r"first job",
    r"we welcome applications from",
]

SINAIS_FLEXIVEL = [
    r"part[- ]time", r"flexible hours", r"flexible shifts",
    r"weekend work", r"zero hours",
]

# Alcool: sinaliza para revisao, nao bloqueia.
SINAIS_ALCOOL = [
    r"\bbar ?tender\b", r"\bbar staff\b", r"serving alcohol",
    r"licensed premises", r"\bmixology\b", r"cocktail",
    # "Bar and Waiting" e padrao em pubs UK e escapava dos padroes acima
    r"\bbar and waiting\b", r"\bbar & waiting\b",
    r"\bbar work\b", r"pulling pints", r"\bcellar\b",
    # "pub" sozinho e fraco demais: casava com nomes de marca no menu.
    # Exige a palavra ligada a funcao.
    r"work(?:ing)? in (?:a|our) pub", r"\bpub\b.{0,20}\b(?:team|staff|role)\b",
]

PERTO_DE_M50 = [
    "manchester", "salford", "mediacity", "media city",
    "trafford", "eccles", "stretford", "prestwich",
]

# Postcodes de Greater Manchester: M1-M90 e distritos vizinhos.
POSTCODE_GM = re.compile(r"\bM\d{1,2}\b", re.I)

# Termos genericos de vaga de entrada que valem mesmo fora da lista de papeis.
# "Team Member" sozinho e comum em fast food e nao casava com nenhum papel.
TERMOS_ENTRADA_TITULO = [
    "team member", "crew member", "team assistant",
    "kitchen assistant", "kitchen porter", "pot wash",
    "waiting staff", "front of house", "food runner",
    "barista", "catering assistant", "server", "runner",
]


def limpar_corpo(texto: str) -> str:
    """
    Remove menu, rodape e widget de vagas vizinhas.
    Sem isso o scoring le o site inteiro em vez da vaga.
    """
    t = texto

    # Corta tudo antes da descricao real, quando ha marcador conhecido
    for marcador in [r"Job Description", r"About the role", r"The Role", r"Job Details"]:
        m = re.search(marcador, t, re.I)
        if m:
            t = t[m.start():]
            break

    # Remove o widget "Previous job X Next job Y" (fonte do falso Catering Assistant)
    t = re.sub(r"Previous job.{0,200}?Next job", " ", t, flags=re.I | re.S)
    t = re.sub(r"Similar jobs.{0,600}$", " ", t, flags=re.I | re.S)
    t = re.sub(r"Related searches.{0,400}$", " ", t, flags=re.I | re.S)

    # Remove itens de menu conhecidos (fonte do falso Apprenticeships)
    for item in [r"Run a Pub Apprenticeships", r"Careers Advice & News",
                 r"Create Job Alert", r"Sign in", r"Find Jobs", r"Role Insights"]:
        t = re.sub(item, " ", t, flags=re.I)

    # Menu "Our Brands" da Whitbread: lista Cookhouse and Pub, Beefeater,
    # Bar and Block etc. em TODA pagina. Marcava housekeeping como alcool.
    t = re.sub(r"Our Brands.{0,220}?(?:Contact Us|Whitbread Inns)", " ",
               t, flags=re.I | re.S)
    for marca in [r"Cookhouse and Pub", r"Bar and Block", r"Beefeater",
                  r"Brewers Fayre", r"Table Table", r"Whitbread Inns"]:
        t = re.sub(marca, " ", t, flags=re.I)

    return t


def _achou(padroes: List[str], texto: str) -> List[str]:
    return [p for p in padroes if re.search(p, texto, re.I)]


def score_job_v2(
    titulo: str,
    corpo: str,
    local: str,
    papeis_preferidos: List[str],
) -> Tuple[int, List[str], List[str], bool]:
    """
    Retorna (score, motivos, bloqueios, precisa_revisao_alcool).
    """
    t = (titulo or "").lower()
    body = limpar_corpo(corpo or "")
    loc = (local or "").lower()

    score = 0
    motivos: List[str] = []
    bloqueios: List[str] = []

    # --- Bloqueio 1: senioridade pelo TITULO ---
    for cargo in SENIOR_NO_TITULO:
        if cargo in t:
            bloqueios.append(f"cargo senior no titulo: {cargo}")
            break

    # --- Bloqueio 2: barreira legal/etaria no corpo (frase inequivoca) ---
    for achado in _achou(BARREIRAS_NO_CORPO, body):
        m = re.search(achado, body, re.I)
        bloqueios.append(f"requisito: {m.group(0)[:40]}")
        break

    # --- Papel preferido: so conta se estiver no TITULO ---
    casou_papel = False
    for papel in papeis_preferidos:
        if papel.lower() in t:
            score += 40
            motivos.append(f"papel no titulo: {papel}")
            casou_papel = True
            break

    # Fallback: termo generico de vaga de entrada no titulo.
    # Cobre "Team Member" solto, que nao consta na lista de papeis do perfil.
    if not casou_papel:
        for termo in TERMOS_ENTRADA_TITULO:
            if termo in t:
                score += 30
                motivos.append(f"funcao de entrada no titulo: {termo}")
                break

    # --- Sinais de vaga de entrada ---
    entrada = _achou(SINAIS_ENTRADA, body)
    if entrada:
        score += 25
        m = re.search(entrada[0], body, re.I)
        motivos.append(f"vaga de entrada: \"{m.group(0)}\"")

    # --- Flexibilidade ---
    flex = _achou(SINAIS_FLEXIVEL, body)
    if flex:
        score += 15
        m = re.search(flex[0], body, re.I)
        motivos.append(f"horario flexivel: \"{m.group(0)}\"")

    # --- Localizacao: usa o campo de local, nao o corpo ---
    if any(p in loc for p in PERTO_DE_M50):
        score += 20
        motivos.append("perto de M50")
    elif POSTCODE_GM.search(loc):
        # Postcode M** = Greater Manchester (ex: M30 9LL, M25 3AJ)
        score += 20
        motivos.append(f"postcode Greater Manchester: {POSTCODE_GM.search(loc).group(0)}")

    # --- Alcool: sinaliza, nao bloqueia ---
    alcool = bool(_achou(SINAIS_ALCOOL, body) or _achou(SINAIS_ALCOOL, t))
    if alcool:
        motivos.append("envolve alcool - revisar regras para menor de 18")

    if bloqueios:
        score = 0

    return score, motivos, bloqueios, alcool
