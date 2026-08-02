# hire-autopilot

**→ [juliopessan.github.io/hire-autopilot](https://juliopessan.github.io/hire-autopilot/)**

Agregador de vagas de hospitality em Greater Manchester (UK), com pontuação por perfil e Kanban de acompanhamento do processo seletivo.

Feito para quem procura o **primeiro emprego**: o scoring privilegia vagas de entrada e descarta cargos sênior, e sinaliza vagas que envolvem álcool — relevante para candidatos menores de 18 anos no Reino Unido.

A coleta roda sozinha todo dia às 07:00 UTC pelo GitHub Actions e republica a página. Quem só quer acompanhar as vagas usa a URL acima — não precisa instalar nada.

---

## A página pública

| O que tem | Detalhe |
|---|---|
| Quadro de fases | Toque num cartão para ver detalhes, abrir o anúncio ou mudar de fase |
| Guarda de CV | Fica no navegador (IndexedDB), não sobe para servidor nenhum |
| Origem das vagas | Quantas entraram por portal e quantas ficaram fora da região |
| Descartadas | O que foi filtrado e por qual regra — serve para pegar erro de filtro |
| Exportar | CSV com as fases e notas |

**Limite:** sem backend, as fases e o CV vivem no navegador de cada pessoa e **não sincronizam entre aparelhos**. Funciona bem para uma pessoa acompanhar o próprio processo. Duas pessoas acompanhando juntas exigiria banco de dados.

Vagas com processo em andamento **sobrevivem ao anúncio sair do ar** — sem isso, uma vaga em "Entrevista" desapareceria do quadro quando saísse da coleta. Ela reaparece marcada como arquivada. Vagas expiradas ainda em "Encontrada" somem, para não acumular lixo.

---

## O que faz

```
5 plataformas  →  deduplicação  →  pontuação por perfil  →  Kanban
```

1. **Coleta** vagas de 5 job boards reais, em paralelo
2. **Deduplica** anúncios que aparecem em mais de uma plataforma
3. **Pontua** cada vaga contra o perfil do candidato, com motivo explícito
4. **Filtra** por região (Greater Manchester) e por regras do perfil
5. **Acompanha** o processo num Kanban que persiste entre execuções

Nenhuma candidatura é enviada automaticamente. O pipeline coleta e ranqueia; a decisão de se candidatar é humana.

---

## Plataformas

| Plataforma | Tipo | Observação |
|---|---|---|
| HospitalityJobsUK | Job board | Especializado em hospitality |
| Caterer | Job board | Recebe também os anúncios do TotalJobs |
| Reed | Job board | — |
| Indeed UK | Job board | Extração pela listagem (detalhe bloqueia com 403) |
| Whitbread / Premier Inn | Carreiras | Portal único — Premier Inn não tem site próprio |

### Notas de campo

Coisas que só apareceram testando contra os sites reais:

- **O filtro de localidade dos sites não é confiável.** Buscar `?location=manchester` no Whitbread devolvia vagas em Hitchin, Southampton e Londres; o Reed devolvia Warrington e Cheshire. O filtro geográfico é aplicado no cliente ([`platforms/geo_filter.py`](platforms/geo_filter.py)), sobre o campo de localidade — nunca sobre o corpo da página, que sempre ecoa o termo buscado.
- **Ler o corpo inteiro da página quebra o scoring.** Menu de navegação e blocos de "vagas relacionadas" contaminam o texto: uma vaga de *Barista* era descartada porque a descrição dizia *"report to the Manager on shift"*, e vagas de *Housekeeping* eram marcadas como envolvendo álcool porque o rodapé listava a marca *"Cookhouse and Pub"*. O scoring decide cargo e senioridade pelo **título** e limpa o corpo antes de lê-lo.
- **Indeed bloqueia a página de detalhe** (`403 Additional Verification Required`), mas não a listagem — e os cards da busca já trazem título, empresa, local e salário.

---

## Instalação

```bash
git clone https://github.com/juliopessan/hire-autopilot.git
cd hire-autopilot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuração

Os dados pessoais **não estão no repositório**. Crie o seu perfil:

```bash
cp profile.example.py profile_local.py
```

Edite `profile_local.py` com nome, e-mail, telefone, postcode e cargos de interesse. O arquivo está no `.gitignore`.

Coloque o CV em `data/` e aponte `cv_filename` para ele no perfil. A pasta `data/` também está no `.gitignore`.

Sem `profile_local.py`, o sistema roda com os dados de exemplo — útil para testar o pipeline, inútil para uma candidatura real.

## Uso

```bash
python3 run_real.py
```

Gera:

| Arquivo | Conteúdo |
|---|---|
| `results/live.html` | Dashboard com vagas e Kanban |
| `results/real_all_*.csv` | Todas as vagas pontuadas |
| `results/real_suitable_*.csv` | Só as adequadas ao perfil |
| `results/kanban_state.json` | Estado do Kanban (persistente) |

Nenhum desses arquivos vai para o git.

---

## Kanban

Vagas adequadas entram automaticamente em **Descoberta**. As demais fases são movidas à mão, conforme o processo anda.

```
Descoberta → Candidatado → Contato → Entrevista → Oferta → Aceito
                                                  ↘ Recusado
                                                  ↘ Sem retorno
```

```bash
python3 kanban_cli.py list                    # ver o board
python3 kanban_cli.py list entrevista         # ver uma fase
python3 kanban_cli.py move a1b2c3d4 contato "ligaram 02/08, pediram disponibilidade"
python3 kanban_cli.py note a1b2c3d4 "pedir horário de sábado"
python3 kanban_cli.py fases                   # listar fases válidas
```

O id de cada vaga aparece no canto do card, no dashboard e no `list`. Basta o prefixo.

**O estado persiste entre execuções.** Rodar `run_real.py` de novo não move uma vaga que já está em *Entrevista* de volta para *Descoberta* — só acrescenta as vagas novas. Cada mudança de fase fica registrada com data no histórico do card.

---

## Scoring

Pontos somam; qualquer bloqueio zera a vaga.

| Sinal | Pontos |
|---|---|
| Cargo preferido no título | +40 |
| Função de entrada no título (`team member`, `crew member`, …) | +30 |
| Sinal de vaga de entrada no corpo (`no experience needed`, `training provided`) | +25 |
| Horário flexível / meio período | +15 |
| Em Greater Manchester | +20 |

| Bloqueio | Efeito |
|---|---|
| Cargo sênior no título (`manager`, `head chef`, `chef de partie`, `supervisor`, `team leader`) | zera |
| Barreira etária no corpo (`must be 18`, `personal licence`) | zera |

Vagas com álcool (`bar and waiting`, `bartender`, `licensed premises`) **não são bloqueadas** — recebem um marcador de revisão manual, já que a regra depende da idade do candidato e do tipo de estabelecimento.

Cada vaga carrega os motivos da sua pontuação, para o critério ser auditável em vez de um número opaco.

---

## Estrutura

```
platforms/
  base.py               interface comum dos scrapers
  geo_filter.py         filtro de Greater Manchester
  live_hospitality.py   HospitalityJobsUK
  live_whitbread.py     Whitbread / Premier Inn
  live_reed.py          Reed
  live_indeed.py        Indeed UK
  live_caterer.py       Caterer
scoring.py              pontuação por perfil
job_deduplicator.py     dedup entre plataformas
kanban_store.py         estado do Kanban (persistente)
kanban_cli.py           CLI de acompanhamento
visualizer_pro.py       dashboard HTML local
run_real.py             pipeline completo
build_site.py           gera a página pública
site/template.html      template da página
candidate.py            estrutura do perfil
profile.example.py      modelo de perfil
.github/workflows/
  recolha.yml           cron diário: coleta → build → publica
```

### Por que GitHub Pages e não Vercel

Playwright precisa de Chromium, que estoura o limite de tamanho das serverless functions da Vercel e o timeout de execução. O Actions roda o navegador sem essas restrições, gera a página estática e o Pages serve. Uma página no browser também não conseguiria fazer a coleta sozinha: os portais não liberam CORS.

Utilitários de diagnóstico, úteis ao adicionar uma plataforma nova:

```bash
python3 probe_platforms.py                    # quais sites respondem
python3 inspect_structure.py <url>            # descobrir seletores
python3 -m platforms.live_reed                # testar um scraper isolado
```

---

## Adicionar uma plataforma

1. `python3 inspect_structure.py <url_da_listagem>` para achar o padrão de link e os seletores
2. Criar `platforms/live_<nome>.py` herdando de `PlatformScraper`, usando `em_greater_manchester()` no campo de localidade
3. Testar isolado: `python3 -m platforms.live_<nome>`
4. Registrar em `run_real.py`

Ao adicionar uma fonte, **confira os motivos do score nas primeiras vagas**. Cada site tem um menu e um rodapé diferentes, e eles contaminam o texto de formas novas — foi assim que apareceram os falsos positivos de *"manager"* e *"Cookhouse and Pub"*.

---

## Limitações

- Nenhum envio automático de candidatura. É coleta e ranqueamento.
- Cobre Greater Manchester. Outras regiões exigem ajustar `geo_filter.py`.
- Scrapers dependem do HTML dos sites e quebram quando eles mudam.
- Alguns anúncios não expõem a empresa em formato reconhecível e saem como `N/A`.
- Respeite os termos de uso de cada plataforma.

## Licença

MIT
