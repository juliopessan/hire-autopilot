#!/usr/bin/env python3
"""
Pipeline REAL: coleta vagas de verdade, deduplica, pontua e mostra no dashboard.
Nao envia candidatura - apenas coleta e ranqueia para revisao.
"""

import asyncio
import pandas as pd
from datetime import datetime

from config import ARTHUR, RESULTS_DIR, UK_PROXY
from platforms.live_hospitality import LiveHospitalityJobsUK
from platforms.live_whitbread import LiveWhitbread
from platforms.live_reed import LiveReed
from platforms.live_indeed import LiveIndeed
from platforms.live_caterer import LiveCaterer
from job_deduplicator import JobDeduplicator
from scoring import score_job_v2
from visualizer_pro import ProVisualizer, create_html_file
from kanban_store import KanbanBoard

MAX_POR_PLATAFORMA = 25


async def main():
    viz = ProVisualizer(RESULTS_DIR)
    viz.start()

    print("=" * 80)
    print("ARTHUR JOB ASSISTANT - COLETA REAL")
    print("=" * 80)
    print(f"Candidato: {ARTHUR.full_name} | {ARTHUR.city} {ARTHUR.postcode} | {ARTHUR.age} anos")
    print(f"Proxy: {UK_PROXY or 'nenhum (IP local)'}")
    print("=" * 80)
    print()

    # --- Coleta ---
    print("PASSO 1: Coletando vagas reais")
    print("-" * 80)

    scrapers = [
        LiveHospitalityJobsUK(max_jobs=MAX_POR_PLATAFORMA, proxy=UK_PROXY),
        LiveWhitbread(location="manchester", max_jobs=MAX_POR_PLATAFORMA, proxy=UK_PROXY),
        LiveReed(max_jobs=MAX_POR_PLATAFORMA, proxy=UK_PROXY),
        LiveIndeed(query="hospitality", max_jobs=MAX_POR_PLATAFORMA, proxy=UK_PROXY),
        LiveCaterer(max_jobs=MAX_POR_PLATAFORMA, proxy=UK_PROXY),
    ]

    all_jobs = []
    for s in scrapers:
        jobs = await s.scrape()
        all_jobs.extend(jobs)
        viz.add_platform_stat(s.name, len(jobs))
        print(f"   {s.name}: {len(jobs)} vagas")

    if not all_jobs:
        print("\nNenhuma vaga coletada.")
        return

    print(f"\n   Total: {len(all_jobs)} vagas")
    print()

    # --- Deduplicacao ---
    print("PASSO 2: Deduplicacao")
    print("-" * 80)
    dedup = JobDeduplicator(similarity_threshold=0.85)
    unique, dups = dedup.deduplicate(all_jobs)
    stats = dedup.get_dedup_stats(len(all_jobs), len(unique))
    print(f"   {stats['original_count']} -> {stats['unique_count']} "
          f"({stats['duplicates_removed']} duplicadas, {stats['dedup_ratio']})")
    print()

    # --- Scoring ---
    print("PASSO 3: Pontuacao contra o perfil do Arthur")
    print("-" * 80)

    scored = []
    for j in unique:
        score, reasons, blocked, alcohol = score_job_v2(
            j["title"], j.get("description", ""), j.get("location", ""),
            ARTHUR.preferred_roles
        )
        scored.append({**j, "score": score, "reasons": "; ".join(reasons),
                       "blocked": "; ".join(blocked), "alcohol_review": alcohol})

    df = pd.DataFrame(scored).sort_values("score", ascending=False).reset_index(drop=True)
    suitable = df[(df["score"] >= 30) & (df["blocked"] == "")].copy()
    rejected = df[df["blocked"] != ""]

    print(f"   Pontuadas:  {len(df)}")
    print(f"   Adequadas:  {len(suitable)}  (score >= 30, sem bloqueio)")
    print(f"   Descartadas por regra: {len(rejected)}")
    print()

    for _, j in df.iterrows():
        viz.add_job(j.to_dict())

    # --- Kanban: vagas adequadas entram em "descoberta" ---
    # Vagas ja no board mantem a fase atual, mesmo recoletadas.
    kanban = KanbanBoard(RESULTS_DIR)
    novas = kanban.sync_new_jobs(suitable.to_dict("records"))
    viz.set_kanban(kanban.board(), kanban.stats())
    create_html_file(viz)

    # --- Resultado ---
    print("=" * 80)
    print("MELHORES VAGAS PARA O ARTHUR")
    print("=" * 80)
    if suitable.empty:
        print("Nenhuma vaga passou nos criterios.")
    else:
        for i, (_, j) in enumerate(suitable.head(10).iterrows(), 1):
            flag = " [ALCOOL - revisar]" if j["alcohol_review"] else ""
            print(f"\n{i}. {j['title']}   [score {j['score']}]{flag}")
            print(f"   {j['company']} | {j['location']} | {j['salary'] or 'salario nao informado'}")
            print(f"   {j['reasons']}")
            print(f"   {j['url']}")

    if not rejected.empty:
        print()
        print("=" * 80)
        print("DESCARTADAS (regra de exclusao do perfil)")
        print("=" * 80)
        for _, j in rejected.head(8).iterrows():
            print(f"  {j['title'][:55]:<55} motivo: {j['blocked']}")

    # --- Salvar ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_csv = RESULTS_DIR / f"real_all_{ts}.csv"
    fit_csv = RESULTS_DIR / f"real_suitable_{ts}.csv"
    df.to_csv(all_csv, index=False)
    suitable.to_csv(fit_csv, index=False)

    viz.complete()
    html = create_html_file(viz)

    print()
    print("=" * 80)
    print("KANBAN DO PROCESSO")
    print("=" * 80)
    print(f"   {novas} vaga(s) nova(s) adicionada(s) em 'Descoberta'")
    for fase, qtd in kanban.stats().items():
        if qtd:
            print(f"   {fase:<14} {qtd}")
    print("\n   Mover uma vaga de fase:")
    print("     python3 kanban_cli.py list")
    print("     python3 kanban_cli.py move <id> contato \"ligaram hoje\"")

    print()
    print("=" * 80)
    print(f"Todas as vagas:  {all_csv.name}")
    print(f"Adequadas:       {fit_csv.name}")
    print(f"Dashboard:       {html}")
    print("=" * 80)
    print("\nNenhuma candidatura foi enviada. Revise a lista antes de decidir.")


if __name__ == "__main__":
    asyncio.run(main())
