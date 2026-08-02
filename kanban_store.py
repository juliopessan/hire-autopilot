"""
Kanban de acompanhamento do processo seletivo.

Diferente do dashboard "live" (que e regenerado do zero a cada execucao
de run_real.py), o Kanban precisa persistir entre execucoes: uma vaga
que entrou em "Entrevista" ontem nao pode voltar pra "Descoberta" so
porque rodamos o scraper de novo hoje.

Estado fica em results/kanban_state.json (fora do git - contem dados
pessoais do processo do Arthur: para qual vaga ele foi chamado, quando,
notas da entrevista etc).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

FASES = [
    "descoberta",      # veio do scraper, ainda nao candidatado
    "candidatado",     # formulario enviado
    "contato",         # empregador respondeu / ligou / e-mail
    "entrevista",      # entrevista marcada ou realizada
    "oferta",          # oferta recebida
    "recusado",        # empregador recusou
    "sem_retorno",     # candidatado ha muito tempo, sem resposta
    "aceito",          # Arthur aceitou a vaga - fim do processo
]

FASE_LABEL = {
    "descoberta": "Descoberta",
    "candidatado": "Candidatado",
    "contato": "Contato",
    "entrevista": "Entrevista",
    "oferta": "Oferta",
    "recusado": "Recusado",
    "sem_retorno": "Sem retorno",
    "aceito": "Aceito",
}


class KanbanBoard:
    def __init__(self, state_dir: Path = None):
        if state_dir is None:
            state_dir = Path(__file__).parent / "results"
        state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = state_dir / "kanban_state.json"
        self.cards: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.cards = data.get("cards", {})
            except (json.JSONDecodeError, OSError):
                self.cards = {}

    def _save(self):
        payload = {
            "updated_at": datetime.now().isoformat(),
            "cards": self.cards,
        }
        self.state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    def sync_new_jobs(self, jobs: List[dict]) -> int:
        """
        Adiciona vagas novas na fase 'descoberta'. Vagas ja existentes no
        board (mesmo job id) NAO sao tocadas - preserva a fase atual e o
        historico, mesmo que o scraper rode de novo e recolete a mesma vaga.
        """
        adicionadas = 0
        for job in jobs:
            job_id = job.get("id")
            if not job_id or job_id in self.cards:
                continue
            self.cards[job_id] = {
                "id": job_id,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "salary": job.get("salary", ""),
                "url": job.get("url", ""),
                "platform": job.get("platform", job.get("source", "")),
                "score": job.get("score", 0),
                "fase": "descoberta",
                "criado_em": datetime.now().isoformat(),
                "atualizado_em": datetime.now().isoformat(),
                "historico": [{"fase": "descoberta", "em": datetime.now().isoformat()}],
                "notas": "",
            }
            adicionadas += 1
        if adicionadas:
            self._save()
        return adicionadas

    def move(self, job_id_prefix: str, nova_fase: str, nota: str = "") -> Optional[dict]:
        if nova_fase not in FASES:
            raise ValueError(f"Fase invalida: {nova_fase}. Use uma de: {', '.join(FASES)}")

        card = self._find(job_id_prefix)
        if not card:
            return None

        card["fase"] = nova_fase
        card["atualizado_em"] = datetime.now().isoformat()
        card["historico"].append({"fase": nova_fase, "em": datetime.now().isoformat()})
        if nota:
            card["notas"] = (card["notas"] + "\n" if card["notas"] else "") + nota

        self._save()
        return card

    def add_note(self, job_id_prefix: str, nota: str) -> Optional[dict]:
        card = self._find(job_id_prefix)
        if not card:
            return None
        card["notas"] = (card["notas"] + "\n" if card["notas"] else "") + nota
        card["atualizado_em"] = datetime.now().isoformat()
        self._save()
        return card

    def _find(self, job_id_prefix: str) -> Optional[dict]:
        if job_id_prefix in self.cards:
            return self.cards[job_id_prefix]
        matches = [c for jid, c in self.cards.items() if jid.startswith(job_id_prefix)]
        return matches[0] if len(matches) == 1 else None

    def by_fase(self, fase: str) -> List[dict]:
        return sorted(
            [c for c in self.cards.values() if c["fase"] == fase],
            key=lambda c: c.get("score", 0), reverse=True
        )

    def board(self) -> Dict[str, List[dict]]:
        return {fase: self.by_fase(fase) for fase in FASES}

    def stats(self) -> Dict[str, int]:
        return {fase: len(self.by_fase(fase)) for fase in FASES}
