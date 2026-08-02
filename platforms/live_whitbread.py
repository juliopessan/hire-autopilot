"""
Scraper REAL do portal Whitbread Careers (dono da marca Premier Inn).

Premier Inn NAO tem portal proprio: as vagas de hotel Premier Inn saem
pelo mesmo ATS da Whitbread em whitbreadcareers.com.

Listagem: /search-and-apply/?location=<cidade>
Vagas:    /job-details/<id>-<id>/<slug>
"""

import re
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright

from .base import PlatformScraper
from .geo_filter import em_greater_manchester

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


class LiveWhitbread(PlatformScraper):
    """Whitbread / Premier Inn - portal unico"""

    BASE = "https://www.whitbreadcareers.com"

    def __init__(self, location: str = "manchester", max_jobs: int = 25, proxy: str = None):
        super().__init__("Whitbread / Premier Inn")
        self.location = location
        self.max_jobs = max_jobs
        self.proxy = proxy

    @property
    def listing_url(self) -> str:
        return f"{self.BASE}/search-and-apply/?location={self.location}"

    async def scrape(self) -> List[Dict]:
        jobs: List[Dict] = []
        descartadas_fora: List[str] = []

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
                await page.wait_for_timeout(3500)

                raw = await page.eval_on_selector_all(
                    'a[href*="/job-details/"]',
                    "els => els.map(e => e.getAttribute('href'))"
                )
                seen, urls = set(), []
                for h in raw:
                    if not h:
                        continue
                    full = h if h.startswith("http") else self.BASE + h
                    full = full.split("?")[0]
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)

                print(f"   [{self.name}] {len(urls)} vagas na listagem ({self.location})")

                for i, url in enumerate(urls[:self.max_jobs], 1):
                    d = await context.new_page()
                    try:
                        await d.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await d.wait_for_timeout(800)

                        title = ""
                        if await d.locator("h1").count():
                            title = clean(await d.locator("h1").first.inner_text())
                        if not title:
                            # fallback: deriva do slug da URL
                            slug = url.rstrip("/").split("/")[-1]
                            title = slug.replace("_-_", " - ").replace("_", " ").title()

                        body = clean(await d.locator("body").inner_text())

                        # O ATS expoe rotulos em sequencia.
                        def field(label: str, nxt: str) -> str:
                            m = re.search(
                                rf"\b{label}\b\s*:?\s+(.{{2,90}}?)\s+(?={nxt}\b)",
                                body, re.I
                            )
                            return clean(m.group(1)) if m else ""

                        # A frase "We're currently recruiting in <LOCAL>" e a fonte
                        # mais confiavel; o rotulo Location arrasta texto vizinho.
                        location = ""
                        mrec = re.search(
                            r"currently recruiting (?:in|at) (?:our |the )?"
                            r"([A-Z][A-Za-z'\- ]{2,40}?)(?=\s+(?:Premier|hotel|Hotel|\.|,|We|Working))",
                            body
                        )
                        if mrec:
                            location = clean(mrec.group(1))

                        if not location:
                            loc_raw = field("Location", "Salary|Contract|Hours|Closing|Categor|Job Type")
                            # corta no primeiro marcador de frase nova
                            location = clean(re.split(r"\s+(?:We're|Categor|Working|Pay:)", loc_raw)[0])

                        if not location:
                            m = re.search(
                                r"\b(?:Manchester|Salford|Trafford|Stockport|Eccles|Prestwich)"
                                r"[A-Za-z ]{0,20}", body)
                            location = clean(m.group(0)) if m else ""

                        salary = field("Salary", "Contract|Hours|Closing|Job Type|Brand|Location")
                        if not salary:
                            m = re.search(
                                r"£\s?[\d,]+(?:\.\d{2})?\s*(?:-\s*£?\s?[\d,]+(?:\.\d{2})?)?"
                                r"\s*(?:per hour|an hour|ph|per annum|pa)?", body, re.I)
                            salary = clean(m.group(0)) if m else ""

                        # Marca: Premier Inn, Beefeater, Brewers Fayre...
                        brand = ""
                        mb = re.search(
                            r"\b(Premier Inn|Beefeater|Brewers Fayre|Bar\s*\+\s*Block|"
                            r"Table Table|Whitbread)\b", body, re.I)
                        if mb:
                            brand = clean(mb.group(1))

                        # Descarta vagas fora de Greater Manchester
                        if not em_greater_manchester(location):
                            descartadas_fora.append(f"{title} ({location or '?'})")
                            continue

                        jobs.append(self.normalize_job(
                            title=title,
                            company=brand or "Whitbread",
                            location=location,
                            salary=salary,
                            url=url,
                            description=body[:6000],
                        ))

                        if i % 10 == 0:
                            print(f"   [{self.name}] {i}/{min(len(urls), self.max_jobs)} lidas")

                    except Exception as e:
                        print(f"   [{self.name}] falha em {url[:55]}: {str(e)[:45]}")
                    finally:
                        await d.close()

            except Exception as e:
                print(f"   [{self.name}] erro na listagem: {str(e)[:80]}")
            finally:
                await browser.close()

        if descartadas_fora:
            print(f"   [{self.name}] {len(descartadas_fora)} descartadas fora de Gtr Manchester:")
            for d in descartadas_fora[:5]:
                print(f"      - {d}")

        return jobs


if __name__ == "__main__":
    async def test():
        s = LiveWhitbread(location="manchester", max_jobs=25)
        jobs = await s.scrape()
        print(f"\n=== {len(jobs)} VAGAS REAIS ===\n")
        for j in jobs:
            print(f"  {j['title']}")
            print(f"    marca:   {j['company']}")
            print(f"    local:   {j['location']}")
            print(f"    salario: {j['salary'] or '(nao informado)'}")
            print(f"    {j['url']}")
            print()

    asyncio.run(test())
