"""
Scraper REAL do HospitalityJobsUK.
Coleta links /job/<id>/<slug>/ da listagem e visita cada pagina de detalhe.
"""

import re
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright

from .base import PlatformScraper

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


class LiveHospitalityJobsUK(PlatformScraper):
    """Scraper real (nao mockado) do HospitalityJobsUK"""

    BASE = "https://www.hospitalityjobsuk.com"
    LISTING = f"{BASE}/jobs/manchester/"

    def __init__(self, max_jobs: int = 25, proxy: str = None):
        super().__init__("HospitalityJobsUK")
        self.max_jobs = max_jobs
        self.proxy = proxy

    async def scrape(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                proxy={"server": self.proxy} if self.proxy else None,
            )
            context = await browser.new_context(
                locale="en-GB", timezone_id="Europe/London", user_agent=UA,
                viewport={"width": 1440, "height": 900},
                extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
            )
            page = await context.new_page()

            try:
                await page.goto(self.LISTING, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2500)

                # Coleta URLs de vaga: padrao /job/<id>/<slug>/
                raw = await page.eval_on_selector_all(
                    'a[href*="/job/"]',
                    "els => els.map(e => e.getAttribute('href'))"
                )

                seen, urls = set(), []
                for href in raw:
                    if not href:
                        continue
                    href = clean(href)
                    if not re.search(r"/job/\d+/", href):
                        continue
                    full = href if href.startswith("http") else self.BASE + href
                    full = full.split("?")[0]
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)

                print(f"   [{self.name}] {len(urls)} vagas unicas na listagem")

                for i, url in enumerate(urls[:self.max_jobs], 1):
                    detail = await context.new_page()
                    try:
                        await detail.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await detail.wait_for_timeout(700)

                        title = ""
                        if await detail.locator("h1").count():
                            title = clean(await detail.locator("h1").first.inner_text())

                        body = clean(await detail.locator("body").inner_text())

                        # A pagina expoe rotulos em sequencia:
                        # "Employer <X> Location <Y> Salary <Z> Closing date <D>"
                        # Ancorar em cada rotulo e parar no rotulo seguinte.
                        def field(label: str, nxt: str) -> str:
                            m = re.search(
                                rf"\b{label}\b\s+(.{{2,80}}?)\s+(?={nxt}\b)",
                                body, re.I
                            )
                            return clean(m.group(1)) if m else ""

                        company = field("Employer", "Location|Salary|Closing")
                        location = field("Location", "Salary|Closing|Sector") or "Manchester"
                        salary = field("Salary", "Closing|Sector|Contract|Hours")

                        # Fallback do salario: primeiro valor em libras do corpo
                        if not salary:
                            sal = re.search(
                                r"£\s?[\d,]+(?:\.\d{2})?\s*(?:-\s*£?\s?[\d,]+(?:\.\d{2})?)?"
                                r"\s*(?:per hour|an hour|ph|per annum|pa)?",
                                body, re.I
                            )
                            salary = clean(sal.group(0)) if sal else ""

                        if title:
                            jobs.append(self.normalize_job(
                                title=title,
                                company=company or "N/A",
                                location=location,
                                salary=salary,
                                url=url,
                                description=body[:6000],
                            ))

                        if i % 10 == 0:
                            print(f"   [{self.name}] {i}/{min(len(urls), self.max_jobs)} lidas")

                    except Exception as e:
                        print(f"   [{self.name}] falha em {url[:60]}: {str(e)[:50]}")
                    finally:
                        await detail.close()

            except Exception as e:
                print(f"   [{self.name}] erro na listagem: {str(e)[:80]}")
            finally:
                await browser.close()

        return jobs


if __name__ == "__main__":
    async def test():
        s = LiveHospitalityJobsUK(max_jobs=8)
        jobs = await s.scrape()
        print(f"\n=== {len(jobs)} VAGAS REAIS COLETADAS ===\n")
        for j in jobs:
            print(f"  {j['title']}")
            print(f"    empresa:  {j['company']}")
            print(f"    local:    {j['location']}")
            print(f"    salario:  {j['salary'] or '(nao informado)'}")
            print(f"    url:      {j['url']}")
            print()

    asyncio.run(test())
