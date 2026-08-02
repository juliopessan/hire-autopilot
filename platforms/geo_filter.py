"""
Filtro geografico compartilhado entre scrapers.

Motivo de existir: descobrimos no Whitbread que o parametro de busca
"?location=manchester" de varios sites NAO filtra de fato - a listagem
volta com vagas do pais inteiro (Hitchin, Southampton, Warrington/Cheshire
etc). Cada scraper precisa aplicar este filtro no campo de localidade
antes de aceitar a vaga.
"""

import re

GREATER_MANCHESTER = [
    "manchester", "salford", "trafford", "stockport", "eccles", "prestwich",
    "stretford", "swinton", "worsley", "sale", "altrincham", "urmston",
    "bury", "bolton", "oldham", "rochdale", "wigan", "ashton", "denton",
    "middleton", "failsworth", "cheadle", "didsbury", "openshaw", "gorton",
    "chorlton", "levenshulme", "reddish", "whitefield", "radcliffe",
]

# Cidades grandes fora de Greater Manchester que contem substrings
# ambiguas (ex: "London Barking" contem nada de GM, mas o corpo da
# pagina sempre ecoa o termo buscado). Se aparecerem no campo de
# localidade, a vaga NAO e de Manchester mesmo que "manchester"
# apareca em outro lugar da pagina.
OUTRAS_REGIOES = [
    "london", "birmingham", "leeds", "liverpool", "glasgow", "bristol",
    "cardiff", "edinburgh", "newcastle", "sheffield", "nottingham",
    "warrington", "cheshire", "chester", "preston", "lancaster",
    "leicester", "coventry", "southampton", "york",
]


def _tem(termo: str, texto: str) -> bool:
    """Match por palavra inteira, nao substring.

    Sem isso 'chester' (em OUTRAS_REGIOES, para pegar a cidade Chester)
    casava dentro de 'Man-CHESTER' e rejeitava a propria Manchester.
    """
    return re.search(rf"\b{re.escape(termo)}\b", texto) is not None


def em_greater_manchester(local: str) -> bool:
    """
    True se `local` (campo de localidade da vaga, NAO o corpo inteiro)
    indica Greater Manchester.

    Checa GM primeiro: uma vaga em "Manchester, Lancashire" deve passar
    mesmo citando a regiao historica junto.
    """
    if not local:
        return False
    l = local.lower()

    if re.search(r"\bm\d{1,2}\b", l):
        return True
    if any(_tem(cidade, l) for cidade in GREATER_MANCHESTER):
        return True
    if any(_tem(regiao, l) for regiao in OUTRAS_REGIOES):
        return False
    return False
