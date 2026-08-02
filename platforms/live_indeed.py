"""
Scraper REAL do Indeed UK.

Diferente das outras fontes: a pagina de DETALHE do Indeed bloqueia
navegacao direta (HTTP 403 "Additional Verification Required" -
confirmado em teste manual, este e um bloqueio real, nao um erro de
URL inventada). A pagina de LISTAGEM, porem, carrega normalmente e
cada card ja traz titulo, empresa, local e salario no proprio HTML
via atributos data-testid estaveis. Este scraper extrai tudo dali e
nunca visita /viewjob.
"""

import re
from typing import List, Dict
from playwright.async_api import async_playwright

from .base import PlatformScraper
from .geo_filter import em_greater_manchester

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


class LiveIndeed(PlatformScraper):
    BASE = "https://uk.indeed.com"

    def __init__(self, query: str = "hospitality", location: str = "Manchester",
                 max_jobs: int = 25, proxy: str = None):
        super().__init__("Indeed")
        self.query = query
        self.location = location
        self.max_jobs = max_jobs
        self.proxy = proxy

    @property
    def listing_url(self) -> str:
        q = self.query.replace(" ", "+")
        l = self.location.replace(" ", "+")
        return f"{self.BASE}/jobs?q={q}&l={l}"

    async def scrape(self) -> List[Dict]:
        jobs: List[Dict] = []
        fora = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                proxy={"server": self.proxy} if self.proxy else None,
            )
            context = await browser.new_context(
                locale="en-GB", timezone_id="Europe/London", user_agent=UA,
                viewport={"width": 1440, "height": 1000},
                extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
            )
            page = await context.new_page()

            try:
                await page.goto(self.listing_url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(3000)

                body_low = (await page.locator("body").inner_text()).lower()
                if any(s in body_low for s in
                       ["additional verification", "unusual traffic", "captcha"]):
                    print(f"   [{self.name}] listagem bloqueada (verificacao anti-bot)")
                    return jobs

                cards = await page.locator(".job_seen_beacon").all()
                print(f"   [{self.name}] {len(cards)} cards na listagem")

                vistos = set()
                for card in cards[:self.max_jobs]:
                    try:
                        jk = ""
                        title_el = card.locator('a[data-jk]').first
                        if await title_el.count():
                            jk = await title_el.get_attribute("data-jk") or ""
                        # jk valido e hex de 16 chars aleatorio. Descarta
                        # tambem padroes sequenciais obvios de placeholder
                        # (ex: "890abcdef0123456" = "0123456789abcdef" fatiado),
                        # que aparecem em cards de anuncio duplicados.
                        if not re.fullmatch(r"[0-9a-f]{16}", jk or ""):
                            continue
                        if jk in "0123456789abcdef0123456789abcdef":
                            continue

                        title = ""
                        tspan = card.locator('h3.jobTitle span, [id^="jobTitle-"]').first
                        if await tspan.count():
                            title = clean(await tspan.inner_text())

                        company = ""
                        cel = card.locator('[data-testid="company-name"]').first
                        if await cel.count():
                            company = clean(await cel.inner_text())

                        location = ""
                        lel = card.locator('[data-testid="text-location"]').first
                        if await lel.count():
                            location = clean(await lel.inner_text())

                        salary = ""
                        sel = card.locator('.salary-snippet-container').first
                        if await sel.count():
                            salary = clean(await sel.inner_text())

                        description = ""
                        del_ = card.locator('[data-testid="jobsnippet_footer"], .css-9446fg').first
                        if await del_.count():
                            description = clean(await del_.inner_text())

                        if not title:
                            continue

                        # o mesmo card pode aparecer 2x na pagina (ex: destaque + lista normal)
                        chave = (title, company, location)
                        if chave in vistos:
                            continue
                        vistos.add(chave)

                        if not em_greater_manchester(location):
                            fora.append(f"{title} ({location or '?'})")
                            continue

                        url = f"{self.BASE}/viewjob?jk={jk}" if jk else self.listing_url

                        jobs.append(self.normalize_job(
                            title=title, company=company or "N/A",
                            location=location, salary=salary,
                            url=url, description=description or title,
                        ))

                    except Exception as e:
                        print(f"   [{self.name}] falha em card: {str(e)[:45]}")

            except Exception as e:
                print(f"   [{self.name}] erro na listagem: {str(e)[:80]}")
            finally:
                await browser.close()

        if fora:
            print(f"   [{self.name}] {len(fora)} descartadas fora de Gtr Manchester:")
            for f in fora[:5]:
                print(f"      - {f}")

        return jobs


if __name__ == "__main__":
    import asyncio

    async def test():
        jobs = await LiveIndeed(query="hospitality", max_jobs=20).scrape()
        print(f"\n=== {len(jobs)} VAGAS ===\n")
        for j in jobs:
            print(f"  {j['title']} | {j['company']} | {j['location']} | {j['salary'] or '(sem salario)'}")
            print(f"    {j['url']}")

    asyncio.run(test())
