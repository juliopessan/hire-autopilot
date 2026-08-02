"""
Professional dashboard visualizer inspired by AI Playbook design
Dark theme with neon accents (purple, green, orange)
"""

import json
import html
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class ProVisualizer:
    """Professional live visualizer with premium design"""

    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent / "results"
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / "live_status.json"
        self.jobs: List[Dict] = []
        self.applications: List[Dict] = []
        self.current_status = "IDLE"
        self.platforms_stats = {}
        self.kanban_board: Dict[str, List[Dict]] = {}
        self.kanban_stats: Dict[str, int] = {}

    def start(self):
        """Mark start of execution"""
        self.current_status = "COLLECTING JOBS"
        self.jobs = []
        self.applications = []
        self._save_state()

    def add_job(self, job: Dict):
        """Add job to list"""
        self.jobs.append(job)
        self._save_state()

    def add_platform_stat(self, platform: str, count: int):
        """Record platform statistics"""
        self.platforms_stats[platform] = count

    def set_kanban(self, board: Dict[str, List[Dict]], stats: Dict[str, int]):
        """Recebe o estado do KanbanBoard para renderizar no dashboard"""
        self.kanban_board = board
        self.kanban_stats = stats

    def start_applying(self):
        """Mark start of applications"""
        self.current_status = "APPLYING"
        self._save_state()

    def add_application(self, app: Dict):
        """Record application"""
        self.applications.append(app)
        self._save_state()

    def complete(self):
        """Mark completion"""
        self.current_status = "COMPLETED"
        self._save_state()

    def _save_state(self):
        """Save state to JSON"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "status": self.current_status,
            "jobs_collected": len(self.jobs),
            "applications_sent": len([a for a in self.applications if a.get("status") == "SUBMITTED"]),
            "applications_total": len(self.applications),
            "jobs": self.jobs,
            "applications": self.applications,
            "platforms": self.platforms_stats,
        }
        self.state_file.write_text(json.dumps(state, indent=2))

    def generate_html(self) -> str:
        """Generate premium dashboard HTML"""
        submitted = len([a for a in self.applications if a.get("status") == "SUBMITTED"])
        needs_review = len([a for a in self.applications if a.get("status") == "NEEDS_REVIEW"])
        failed = len([a for a in self.applications if a.get("status") == "FAILED"])
        total_apps = len(self.applications)

        def esc(v) -> str:
            return html.escape(str(v or ""), quote=True)

        jobs_sorted = sorted(self.jobs, key=lambda j: j.get("score", 0), reverse=True)

        jobs_html = "\n".join([
            f"""
            <a class="job-card" href="{esc(j.get('url', '#'))}" target="_blank" rel="noopener noreferrer">
                <div class="job-score">{j.get('score', 0)}</div>
                <div class="job-info">
                    <div class="job-title">{esc(j.get('title', 'N/A'))}</div>
                    <div class="job-company">{esc(j.get('company', 'N/A'))} — {esc(j.get('location', ''))}</div>
                    <div class="job-platform">{esc(j.get('platform', 'Unknown'))}</div>
                    <div class="job-reasons">{esc((j.get('reasons') or '')[:120])}</div>
                </div>
                <div class="job-side">
                    <div class="job-salary">{esc(j.get('salary', 'N/A') or 'N/A')}</div>
                    <div class="job-link">Abrir vaga ↗</div>
                </div>
            </a>
            """
            for j in jobs_sorted[:30]
        ]) or '<div class="empty-state">Coletando vagas...</div>'

        apps_html = "\n".join([
            f"""
            <a class="app-row" href="{esc(a.get('url', '#'))}" target="_blank" rel="noopener noreferrer">
                <div class="app-title">{esc(a.get('title', 'N/A'))}</div>
                <div class="app-company">{esc(a.get('company', 'N/A'))}</div>
                <div class="app-status {esc(a.get('status', 'unknown')).lower()}">{esc(a.get('status', 'UNKNOWN'))}</div>
                <div class="app-notes">{esc((a.get('notes') or '')[:80])}</div>
            </a>
            """
            for a in self.applications[-10:]
        ]) or '<div class="empty-state">Aguardando candidaturas...</div>'

        platforms_html = "\n".join([
            f'<div class="platform-stat"><span>{esc(p)}</span><span class="count">{c}</span></div>'
            for p, c in sorted(self.platforms_stats.items(), key=lambda x: x[1], reverse=True)[:6]
        ])

        # --- Kanban ---
        FASE_LABEL = {
            "descoberta": "Descoberta", "candidatado": "Candidatado",
            "contato": "Contato", "entrevista": "Entrevista",
            "oferta": "Oferta", "recusado": "Recusado",
            "sem_retorno": "Sem retorno", "aceito": "Aceito",
        }
        ORDEM_FASES = ["descoberta", "candidatado", "contato", "entrevista",
                       "oferta", "aceito", "recusado", "sem_retorno"]

        colunas = []
        for fase in ORDEM_FASES:
            cards = self.kanban_board.get(fase, [])
            cards_html = "\n".join([
                f"""
                <a class="kb-card" href="{esc(c.get('url', '#'))}" target="_blank" rel="noopener noreferrer">
                    <div class="kb-card-top">
                        <span class="kb-card-score">{c.get('score', 0)}</span>
                        <span class="kb-card-id">{esc(c.get('id', '')[:8])}</span>
                    </div>
                    <div class="kb-card-title">{esc(c.get('title', ''))}</div>
                    <div class="kb-card-meta">{esc(c.get('company', ''))}</div>
                    <div class="kb-card-meta">{esc(c.get('salary', '') or '')}</div>
                    {f'<div class="kb-card-note">{esc(c.get("notas", "")[:90])}</div>' if c.get('notas') else ''}
                </a>
                """
                for c in cards[:12]
            ]) or '<div class="kb-empty">—</div>'

            colunas.append(f"""
                <div class="kb-col kb-col-{fase}">
                    <div class="kb-col-head">
                        <span class="kb-col-title">{FASE_LABEL[fase]}</span>
                        <span class="kb-col-count">{len(cards)}</span>
                    </div>
                    <div class="kb-col-body">{cards_html}</div>
                </div>
            """)

        kanban_html = "\n".join(colunas)
        kanban_total = sum(self.kanban_stats.values()) if self.kanban_stats else 0

        progress = int((total_apps / max(1, len(self.jobs)) * 100)) if len(self.jobs) > 0 else 0

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="2">
            <title>Arthur Job Assistant — Multi-Platform</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}

                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: #0a0e27;
                    color: #e0e0e0;
                    padding: 40px 20px;
                    min-height: 100vh;
                }}

                .container {{ max-width: 1400px; margin: 0 auto; }}

                .header {{
                    margin-bottom: 50px;
                    border-bottom: 1px solid #1a2347;
                    padding-bottom: 30px;
                }}

                .header h1 {{
                    font-size: 48px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    background: linear-gradient(135deg, #fff 0%, #a78bfa 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}

                .header .subtitle {{
                    font-size: 14px;
                    color: #888;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}

                .status-badge {{
                    display: inline-block;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-top: 15px;
                    background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%);
                    color: white;
                    letter-spacing: 1px;
                }}

                .status-badge.completed {{
                    background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
                }}

                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 20px;
                    margin-bottom: 50px;
                }}

                .stat-card {{
                    background: #0f1437;
                    border: 1px solid #1a2347;
                    border-radius: 12px;
                    padding: 25px;
                    position: relative;
                    overflow: hidden;
                }}

                .stat-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #7c3aed, #a78bfa, #06b6d4);
                }}

                .stat-card .label {{
                    font-size: 12px;
                    color: #888;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 10px;
                }}

                .stat-card .number {{
                    font-size: 42px;
                    font-weight: 700;
                    background: linear-gradient(135deg, #a78bfa 0%, #06b6d4 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}

                .stat-card .sub {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 8px;
                }}

                .section {{
                    background: #0f1437;
                    border: 1px solid #1a2347;
                    border-radius: 12px;
                    padding: 30px;
                    margin-bottom: 30px;
                }}

                .section h2 {{
                    font-size: 20px;
                    font-weight: 600;
                    margin-bottom: 25px;
                    color: #e0e0e0;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}

                .section h2::before {{
                    content: '';
                    width: 8px;
                    height: 8px;
                    background: linear-gradient(135deg, #7c3aed, #a78bfa);
                    border-radius: 50%;
                }}

                .jobs-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                    gap: 15px;
                }}

                a.job-card {{
                    background: #141d3e;
                    border: 1px solid #1a2347;
                    border-radius: 10px;
                    padding: 15px;
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                    transition: all 0.15s ease;
                    text-decoration: none;
                    color: inherit;
                    cursor: pointer;
                }}

                a.job-card:hover {{
                    border-color: #7c3aed;
                    background: #18254f;
                    transform: translateY(-1px);
                }}

                .job-score {{
                    min-width: 46px;
                    height: 46px;
                    background: linear-gradient(135deg, #f97316 0%, #fb923c 100%);
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    color: white;
                    font-size: 17px;
                    flex-shrink: 0;
                }}

                .job-info {{
                    flex: 1;
                    min-width: 0;
                }}

                .job-title {{
                    font-weight: 600;
                    font-size: 13px;
                    color: #e0e0e0;
                    white-space: normal;
                    line-height: 1.3;
                }}

                .job-company {{
                    font-size: 11px;
                    color: #888;
                    margin-top: 4px;
                }}

                .job-platform {{
                    font-size: 10px;
                    color: #06b6d4;
                    margin-top: 4px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}

                .job-reasons {{
                    font-size: 10px;
                    color: #666;
                    margin-top: 6px;
                    line-height: 1.4;
                }}

                .job-side {{
                    text-align: right;
                    flex-shrink: 0;
                }}

                .job-salary {{
                    font-size: 11px;
                    color: #10b981;
                    font-weight: 600;
                    white-space: nowrap;
                }}

                .job-link {{
                    font-size: 10px;
                    color: #a78bfa;
                    margin-top: 8px;
                    white-space: nowrap;
                }}

                /* ---- Kanban ---- */
                .kb-scroll {{
                    overflow-x: auto;
                    padding-bottom: 8px;
                }}

                .kb-board {{
                    display: grid;
                    grid-auto-flow: column;
                    grid-auto-columns: minmax(210px, 1fr);
                    gap: 12px;
                    min-width: min-content;
                }}

                .kb-col {{
                    background: #0c1130;
                    border: 1px solid #1a2347;
                    border-radius: 10px;
                    padding: 12px;
                    display: flex;
                    flex-direction: column;
                    min-height: 120px;
                }}

                .kb-col-head {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #1a2347;
                }}

                .kb-col-title {{
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    color: #a78bfa;
                }}

                .kb-col-count {{
                    background: #1a2347;
                    color: #e0e0e0;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 2px 7px;
                    border-radius: 10px;
                }}

                .kb-col-entrevista .kb-col-title {{ color: #06b6d4; }}
                .kb-col-oferta .kb-col-title     {{ color: #10b981; }}
                .kb-col-aceito .kb-col-title     {{ color: #10b981; }}
                .kb-col-recusado .kb-col-title   {{ color: #ef4444; }}
                .kb-col-sem_retorno .kb-col-title{{ color: #6b7280; }}

                .kb-col-body {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}

                a.kb-card {{
                    display: block;
                    background: #141d3e;
                    border: 1px solid #1a2347;
                    border-radius: 8px;
                    padding: 10px;
                    text-decoration: none;
                    color: inherit;
                    transition: all 0.15s ease;
                }}

                a.kb-card:hover {{
                    border-color: #7c3aed;
                    background: #18254f;
                }}

                .kb-card-top {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 6px;
                }}

                .kb-card-score {{
                    background: linear-gradient(135deg, #f97316, #fb923c);
                    color: white;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 2px 7px;
                    border-radius: 5px;
                }}

                .kb-card-id {{
                    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                    font-size: 9px;
                    color: #4b5563;
                }}

                .kb-card-title {{
                    font-size: 11px;
                    font-weight: 600;
                    color: #e0e0e0;
                    line-height: 1.3;
                }}

                .kb-card-meta {{
                    font-size: 10px;
                    color: #888;
                    margin-top: 3px;
                }}

                .kb-card-note {{
                    font-size: 9px;
                    color: #a78bfa;
                    margin-top: 6px;
                    padding-top: 6px;
                    border-top: 1px solid #1a2347;
                    line-height: 1.35;
                }}

                .kb-empty {{
                    text-align: center;
                    color: #374151;
                    font-size: 13px;
                    padding: 14px 0;
                }}

                .kb-hint {{
                    margin-top: 16px;
                    padding: 12px 14px;
                    background: #0c1130;
                    border: 1px solid #1a2347;
                    border-radius: 8px;
                    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                    font-size: 11px;
                    color: #6b7280;
                    line-height: 1.7;
                }}

                .kb-hint code {{ color: #a78bfa; }}

                .apps-table {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}

                a.app-row {{
                    background: #141d3e;
                    border: 1px solid #1a2347;
                    border-radius: 8px;
                    padding: 12px 15px;
                    display: grid;
                    grid-template-columns: 1fr 0.8fr 0.6fr 0.8fr;
                    gap: 12px;
                    align-items: center;
                    font-size: 12px;
                    text-decoration: none;
                    color: inherit;
                    cursor: pointer;
                    transition: all 0.15s ease;
                }}

                a.app-row:hover {{
                    border-color: #7c3aed;
                    background: #18254f;
                }}

                .app-title {{
                    font-weight: 500;
                    color: #e0e0e0;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                .app-company {{
                    color: #888;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                .app-status {{
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: 600;
                    text-align: center;
                    font-size: 10px;
                    text-transform: uppercase;
                }}

                .app-status.submitted {{
                    background: #065f46;
                    color: #10b981;
                }}

                .app-status.needs_review {{
                    background: #7c2d12;
                    color: #f97316;
                }}

                .app-status.failed {{
                    background: #7f1d1d;
                    color: #ef4444;
                }}

                .app-notes {{
                    color: #666;
                    font-size: 11px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                .platforms-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                    gap: 12px;
                }}

                .platform-stat {{
                    background: #141d3e;
                    border: 1px solid #1a2347;
                    border-radius: 8px;
                    padding: 12px 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 12px;
                }}

                .platform-stat span:first-child {{
                    color: #e0e0e0;
                    font-weight: 500;
                }}

                .platform-stat .count {{
                    background: #7c3aed;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 11px;
                }}

                .progress-bar {{
                    width: 100%;
                    height: 6px;
                    background: #1a2347;
                    border-radius: 3px;
                    overflow: hidden;
                    margin-top: 15px;
                }}

                .progress-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #7c3aed, #a78bfa, #06b6d4);
                    width: {progress}%;
                    animation: pulse 2s ease-in-out infinite;
                }}

                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.7; }}
                }}

                .empty-state {{
                    text-align: center;
                    color: #666;
                    padding: 30px;
                    font-size: 13px;
                }}

                .footer {{
                    text-align: right;
                    color: #666;
                    font-size: 11px;
                    margin-top: 40px;
                    border-top: 1px solid #1a2347;
                    padding-top: 20px;
                }}

                @media (max-width: 768px) {{
                    .app-row {{ grid-template-columns: 1fr 1fr; }}
                    .job-card {{ flex-direction: column; }}
                    .header h1 {{ font-size: 32px; }}
                    .stats {{ grid-template-columns: repeat(2, 1fr); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="subtitle">Multi-Platform Job Aggregator</div>
                    <h1>Arthur Job Assistant</h1>
                    <span class="status-badge {('completed' if self.current_status == 'COMPLETED' else '')}">{self.current_status}</span>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <div class="label">Vagas Coletadas</div>
                        <div class="number">{len(self.jobs)}</div>
                        <div class="sub">De {len(self.platforms_stats)} plataformas</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">✅ Enviadas</div>
                        <div class="number">{submitted}</div>
                        <div class="sub">Com sucesso</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">⚠️ Revisão Manual</div>
                        <div class="number">{needs_review}</div>
                        <div class="sub">Aguardando</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">📊 Taxa Sucesso</div>
                        <div class="number">{int((submitted / max(1, total_apps) * 100)) if total_apps > 0 else 0}%</div>
                        <div class="sub">{total_apps} candidaturas</div>
                    </div>
                </div>

                <div class="section">
                    <h2>Plataformas Ativas</h2>
                    <div class="platforms-grid">
                        {platforms_html if platforms_html else '<div class="empty-state">Carregando plataformas...</div>'}
                    </div>
                </div>

                <div class="section">
                    <h2>Kanban do Processo &nbsp;<span style="font-size:12px;color:#666;font-weight:400">
                        {kanban_total} vaga(s) em acompanhamento</span></h2>
                    <div class="kb-scroll">
                        <div class="kb-board">
                            {kanban_html}
                        </div>
                    </div>
                    <div class="kb-hint">
                        Mover uma vaga de fase (o id aparece no canto do card):<br>
                        <code>python3 kanban_cli.py list</code><br>
                        <code>python3 kanban_cli.py move a1b2c3d4 contato "ligaram hoje as 14h"</code><br>
                        <code>python3 kanban_cli.py move a1b2c3d4 entrevista</code>
                    </div>
                </div>

                <div class="section">
                    <h2>Vagas em Destaque</h2>
                    <div class="jobs-grid">
                        {jobs_html}
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>

                <div class="section">
                    <h2>Candidaturas Recentes</h2>
                    <div class="apps-table">
                        {apps_html}
                    </div>
                </div>

                <div class="footer">
                    <div>Atualizado em {datetime.now().strftime('%H:%M:%S')} — Página auto-atualiza a cada 2 segundos</div>
                </div>
            </div>
        </body>
        </html>
        """


def create_html_file(visualizer: ProVisualizer, output_path: Path = None):
    """Create HTML file from visualizer"""
    if output_path is None:
        output_path = visualizer.output_dir / "live.html"

    html = visualizer.generate_html()
    output_path.write_text(html)
    return output_path
