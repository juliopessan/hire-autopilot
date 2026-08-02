"""
Scraper REAL do Reed.co.uk.

Listagem: /jobs/hospitality-jobs-in-manchester
Vagas:    /jobs/<slug>/<id>

Cuidado descoberto em teste manual: a listagem "in-manchester" do Reed
inclui vagas de Warrington/Cheshire (~30km de distancia, regiao
diferente). O filtro geografico e obrigatorio, nao opcional.
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


class LiveReed(PlatformScraper):
    BASE = "https://www.reed.co.uk"
    LISTING = f"{BASE}/jobs/hospitality-jobs-in-manchester"

    def __init__(self, max_jobs: int = 25, proxy: str = None):
        super().__init__("Reed")
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
                    'a[href*="/jobs/"]', "els => els.map(e => e.getAttribute('href'))"
                )
                seen, urls = set(), []
                for h in raw:
                    if not h or not re.search(r"/jobs/[a-z0-9-]+/\d{5,}", h):
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

                        # Formato observado: "by <Empresa> £X - £Y per hour <Local>, <Regiao> <Contrato>"
                        company = ""
                        mc = re.search(r"\bby\s+([A-Z][A-Za-z0-9&.,'\- ]{2,60}?)\s+£", body)
                        if mc:
                            company = clean(mc.group(1))

                        salary = ""
                        ms = re.search(
                            r"£\s?[\d,]+(?:\.\d{2})?\s*(?:-\s*£?\s?[\d,]+(?:\.\d{2})?)?"
                            r"\s*(?:per hour|an hour|per annum|a year)?", body)
                        if ms:
                            salary = clean(ms.group(0))

                        location = ""
                        if ms:
                            # localidade fica logo apos o salario, antes do tipo de contrato
                            resto = body[ms.end():ms.end() + 90]
                            ml = re.match(r"\s*([A-Z][A-Za-z ]+(?:,\s*[A-Z][A-Za-z ]+)?)", resto)
                            if ml:
                                location = clean(ml.group(1))

                        if not em_greater_manchester(location):
                            fora.append(f"{title} ({location or '?'})")
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
        jobs = await LiveReed(max_jobs=20).scrape()
        print(f"\n=== {len(jobs)} VAGAS ===\n")
        for j in jobs:
            print(f"  {j['title']} | {j['company']} | {j['location']} | {j['salary']}")
            print(f"    {j['url']}")

    asyncio.run(test())
