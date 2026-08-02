"""
Scraper REAL do Caterer.com.

Listagem: /jobs/manchester
Vagas:    /job/<slug>/<empresa-slug>-job<id>

Nota: a listagem de hospitality do TotalJobs (totaljobs.com) redireciona
a maioria dos seus anuncios para caterer.com/job/... (mesmo grupo de
anuncios). Por isso nao escrevemos um scraper "TotalJobs" separado -
seria coletar as mesmas vagas duas vezes. Ficamos com Caterer como a
fonte nativa dos dois.
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


class LiveCaterer(PlatformScraper):
    BASE = "https://www.caterer.com"
    LISTING = f"{BASE}/jobs/manchester"

    def __init__(self, max_jobs: int = 25, proxy: str = None):
        super().__init__("Caterer")
        self.max_jobs = max_jobs
        self.proxy = proxy

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
                await page.goto(self.LISTING, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(3000)

                raw = await page.eval_on_selector_all(
                    'a[href*="/job/"]', "els => els.map(e => e.getAttribute('href'))"
                )
                seen, urls = set(), []
                for h in raw:
                    if not h or not re.search(r"/job/[a-z0-9-]+/[a-z0-9-]*\d{5,}", h):
                        continue
                    full = h if h.startswith("http") else self.BASE + h
                    full = full.split("?")[0]
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)

                print(f"   [{self.name}] {len(urls)} vagas na listagem")

                for i, url in enumerate(urls[:self.max_jobs], 1):
                    d = await context.new_page()
                    try:
                        await d.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await d.wait_for_timeout(700)

                        title = ""
                        if await d.locator("h1").count():
                            title = clean(await d.locator("h1").first.inner_text())

                        body = clean(await d.locator("body").inner_text())

                        def field(label: str, nxt: str) -> str:
                            m = re.search(
                                rf"\b{label}\b\s*:?\s+(.{{2,90}}?)\s+(?={nxt}\b)",
                                body, re.I
                            )
                            return clean(m.group(1)) if m else ""

                        company = field("Branch", "Location|Salary|Contract")
                        location = field("Location", "Salary|Contract|Hours|Posted")
                        salary = field("Salary/Benefits", "Contract|Hours|Posted|Closing")

                        # Formato alternativo (anuncios de agencia, ex: "Off To Work"):
                        # nao usa rotulos "Location:"/"Branch:" - usa
                        # "View Profile <Local>, <Regiao>, <Postcode> Published:"
                        if not location:
                            mv = re.search(
                                r"View Profile\s+(.{2,70}?)\s+Published:", body)
                            if mv:
                                location = clean(mv.group(1))

                        if not company:
                            # empresa costuma vir logo apos o titulo, antes de "View Profile"
                            mc = re.search(
                                rf"{re.escape(title)}\s+([A-Z][A-Za-z0-9&.,'\- ]{{2,50}}?)"
                                r"\s+View Profile", body)
                            if mc:
                                company = clean(mc.group(1))

                        if not salary:
                            ms = re.search(
                                r"£\s?[\d,]+(?:\.\d{2})?\s*(?:-\s*£?\s?[\d,]+(?:\.\d{2})?)?"
                                r"\s*(?:per hour|an hour|ph|per annum|pa)?", body, re.I)
                            salary = clean(ms.group(0)) if ms else ""

                        # Se a localidade nao foi extraida, usa o titulo como
                        # ultimo recurso antes de descartar (ex: "Kitchen
                        # Porter Manchester CC" tem a cidade no proprio titulo).
                        checar = location or title
                        if not em_greater_manchester(checar):
                            fora.append(f"{title} ({location or 'sem local, titulo nao ajudou'})")
                            continue

                        if title:
                            jobs.append(self.normalize_job(
                                title=title, company=company or "N/A",
                                location=location, salary=salary,
                                url=url, description=body[:6000],
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

        if fora:
            print(f"   [{self.name}] {len(fora)} descartadas fora de Gtr Manchester:")
            for f in fora[:5]:
                print(f"      - {f}")

        return jobs


if __name__ == "__main__":
    import asyncio

    async def test():
        jobs = await LiveCaterer(max_jobs=20).scrape()
        print(f"\n=== {len(jobs)} VAGAS ===\n")
        for j in jobs:
            print(f"  {j['title']} | {j['company']} | {j['location']} | {j['salary'] or '(sem salario)'}")
            print(f"    {j['url']}")

    asyncio.run(test())
