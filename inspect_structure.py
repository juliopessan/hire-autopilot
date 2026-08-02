#!/usr/bin/env python3
"""
Inspeciona a estrutura HTML real de um job board
para descobrir os seletores certos antes de escrever o scraper.
"""

import asyncio
import sys
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.hospitalityjobsuk.com/jobs/manchester/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            locale="en-GB", timezone_id="Europe/London", user_agent=UA,
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)

        print(f"URL: {URL}")
        print(f"Titulo: {await page.title()}\n")

        # Amostra de hrefs distintos
        print("=== AMOSTRA DE LINKS ===")
        hrefs = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.getAttribute('href'))"
        )
        from collections import Counter
        import re
        patterns = Counter()
        for h in hrefs:
            if not h:
                continue
            # generaliza: /job/12345/titulo -> /job/<n>/<slug>
            p2 = re.sub(r"/\d+", "/<n>", h)
            p2 = re.sub(r"[a-z0-9-]{20,}", "<slug>", p2)
            patterns[p2] += 1
        for pat, count in patterns.most_common(15):
            print(f"  {count:4d}x  {pat[:90]}")

        # Containers repetidos: procura elementos com muitas ocorrencias
        print("\n=== CONTAINERS CANDIDATOS ===")
        for sel in ["article", "li", "div[class*=job i]", "div[class*=card i]",
                    "div[class*=result i]", "div[class*=vacancy i]", "[data-testid]"]:
            n = await page.locator(sel).count()
            if 5 <= n <= 200:
                print(f"  {sel:35s} -> {n} elementos")

        # Texto do primeiro bloco que contenha um link de vaga
        print("\n=== PRIMEIRO ITEM (texto bruto) ===")
        for sel in ["article", "div[class*=job i]", "li"]:
            loc = page.locator(sel)
            n = await loc.count()
            for i in range(min(n, 12)):
                item = loc.nth(i)
                try:
                    txt = (await item.inner_text()).strip()
                    has_link = await item.locator('a[href*="job" i]').count()
                    if has_link and 40 < len(txt) < 600:
                        print(f"[seletor: {sel}, indice {i}]")
                        print(txt[:400])
                        print("\n--- classes do container ---")
                        print((await item.get_attribute("class") or "")[:200])
                        await browser.close()
                        return
                except Exception:
                    continue

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
