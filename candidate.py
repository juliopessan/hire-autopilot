"""
Estrutura do perfil do candidato.

Os dados reais NAO ficam aqui - ficam em profile_local.py (fora do git).
Ver profile.example.py.
"""

from dataclasses import dataclass, field
from typing import List
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Candidate:
    full_name: str
    email: str
    phone: str
    postcode: str
    city: str
    age: int
    right_to_work_uk: bool
    first_job: bool
    education: str
    education_completed: str
    preferred_roles: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    availability_text: str = ""
    cv_filename: str = "cv.pdf"

    @property
    def cv_path(self) -> str:
        return str(DATA_DIR / self.cv_filename)

    @property
    def is_minor(self) -> bool:
        return self.age < 18
