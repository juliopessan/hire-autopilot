"""
Perfil do candidato - MODELO.

Copie este arquivo para `profile_local.py` e preencha com os dados reais:

    cp profile.example.py profile_local.py

`profile_local.py` esta no .gitignore e nunca deve ser commitado: ele
contem nome completo, e-mail, telefone e caminho do CV de uma pessoa
real. Se `profile_local.py` nao existir, o sistema roda com os dados de
exemplo abaixo (funciona para testar o pipeline, mas nao serve para
candidatura de verdade).
"""

from candidate import Candidate

CANDIDATE = Candidate(
    full_name="Nome Sobrenome",
    email="email@exemplo.com",
    phone="+44 7000 000000",
    postcode="M50",
    city="Manchester",
    age=17,
    right_to_work_uk=True,
    first_job=True,
    education="High School Diploma",
    education_completed="July 2026",
    preferred_roles=[
        "Hospitality Team Member",
        "Front of House",
        "Kitchen Assistant",
        "Kitchen Porter",
        "Kitchen Team Member",
        "Catering Assistant",
        "Food Runner",
        "Waiting Staff",
        "Cafe Team Member",
        "Crew Member",
        "Customer Service Assistant",
        "Barista",
    ],
    exclude_keywords=[
        "18+",
        "over 18",
        "must be 18",
        "personal licence",
        "driving licence required",
        "night manager",
        "night shift",
        "experienced chef",
        "minimum 2 years",
        "minimum two years",
        "supervisor",
        "manager",
    ],
    availability_text=(
        "Available for part-time or full-time work, weekends, bank holidays "
        "and evening shifts within legally permitted hours."
    ),
    cv_filename="cv.pdf",
)
