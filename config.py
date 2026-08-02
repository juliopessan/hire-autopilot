from pathlib import Path

from candidate import Candidate

# Dados pessoais reais ficam em profile_local.py, que esta no .gitignore.
# Sem esse arquivo, usa o perfil de exemplo (bom para testar o pipeline,
# nao para candidatura real).
try:
    from profile_local import CANDIDATE
    PERFIL_REAL = True
except ImportError:
    from importlib.util import spec_from_file_location, module_from_spec
    _spec = spec_from_file_location(
        "profile_example", Path(__file__).parent / "profile.example.py")
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    CANDIDATE = _mod.CANDIDATE
    PERFIL_REAL = False

# Alias historico usado em varios modulos
ARTHUR = CANDIDATE

# Configuração de busca
BASE_URL = "https://www.hospitalityjobsuk.com"
SEARCH_URLS = [
    f"{BASE_URL}/jobs/manchester/",
    f"{BASE_URL}/jobs/manchester/part-time-flexible/direct-employer/"
]

# Limites
MAX_JOB_PAGES = 30
MIN_SCORE = 30
MAX_APPLICATIONS = 5

# Diretórios
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"

# Criar diretórios se não existirem
for d in [DATA_DIR, RESULTS_DIR, SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Comportamento
AUTO_SUBMIT = True
HEADLESS = False  # 👀 VISUALIZAÇÃO EM TEMPO REAL
SCREENSHOT_EVERY_JOB = True
DELAY_BETWEEN_JOBS = 2  # segundos

# Proxy UK para o Chromium.
# Preencha com o endereço real do seu proxy/VPN UK, ex: "http://user:pass@host:porta".
# Se ficar None, o Chromium sai pelo IP local (sem VPN).
UK_PROXY = None

# Modelo de carta de apresentacao.
# Os campos entre chaves sao preenchidos a partir do perfil (profile_local.py).
COVER_LETTER_TEMPLATE = '''Dear Hiring Manager,

I am applying for the {job_title} position at {company}.

I recently completed my {education} and I am now seeking my first professional opportunity in hospitality. I am reliable, friendly, punctual and eager to learn from an experienced team.

Through independent projects, I have developed strong organisation, communication, attention to detail and problem-solving skills. I am comfortable following procedures, supporting colleagues and taking responsibility for completing tasks accurately.

I am based in {city} {postcode} and am available for {availability}.

Thank you for considering my application. I would welcome the opportunity to discuss how I could contribute to your team.

Kind regards,

{full_name}
'''


def build_cover_letter(job_title: str, company: str = "your company") -> str:
    """Monta a carta usando os dados do perfil carregado."""
    return COVER_LETTER_TEMPLATE.format(
        job_title=job_title,
        company=company or "your company",
        education=CANDIDATE.education,
        city=CANDIDATE.city,
        postcode=CANDIDATE.postcode,
        availability=CANDIDATE.availability_text.lower(),
        full_name=CANDIDATE.full_name,
    )
