#!/usr/bin/env python3
"""
Sonda quais plataformas respondem sem proxy.
Nao coleta vagas - so verifica acesso e mede sinais de bloqueio.
"""

import asyncio
from playwright.async_api import async_playwright

TARGETS = [
    ("HospitalityJobsUK", "https://www.hospitalityjobsuk.com/jobs/manchester/"),
    ("Caterer",           "https://www.caterer.com/jobs/manchester"),
    ("Indeed",            "https://uk.indeed.com/jobs?q=kitchen+assistant&l=Manchester"),
    ("TotalJobs",         "https://www.totaljobs.com/jobs/hospitality/in-manchester"),
    ("Reed",              "https://www.reed.co.uk/jobs/hospitality-jobs-in-manchester"),
    ("Premier Inn",       "https://careers.whitbread.co.uk/search/?q=manchester"),
    ("PizzaExpress",      "https://pizzaexpress.careers/vacancies/"),
    ("Costa",             "https://www.costa.co.uk/careers"),
    ("Starbucks",         "https://apply.starbucks.co.uk/"),
    ("Nando's",           "https://careers.nandos.co.uk/vacancies"),
    ("McDonald's",        "https://people.mcdonalds.co.uk/vacancies/"),
    ("KFC",               "https://jobs.kfc.co.uk/vacancies"),
    ("Greggs",            "https://careers.greggs.co.uk/vacancies/"),
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

BLOCK_SIGNS = [
    "just a moment", "checking your browser", "access denied",
    "captcha", "are you a robot", "unusual traffic", "cf-challenge",
    "verify you are human", "request blocked",
]


async def probe(context, name, url):
    page = await context.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(2500)

        status = resp.status if resp else 0
        title = (await page.title()) or ""
        body = (await page.locator("body").inner_text())[:4000].lower()

        blocked = [s for s in BLOCK_SIGNS if s in body or s in title.lower()]

        # Conta ancoras que parecem vaga
        links = await page.locator('a[href*="job" i], a[href*="vacanc" i]').count()

        if blocked:
            verdict = f"BLOQUEADO ({blocked[0]})"
        elif status >= 400:
            verdict = f"HTTP {status}"
        elif links >= 5:
            verdict = f"OK - {links} links de vaga"
        else:
            verdict = f"ABRIU mas so {links} links (seletor/JS?)"

        return name, status, verdict, title[:60]

    except Exception as e:
        return name, 0, f"ERRO: {str(e)[:60]}", ""
    finally:
        await page.close()


async def main():
    print("=" * 88)
    print("SONDAGEM DE PLATAFORMAS - sem proxy, IP local")
    print("=" * 88)
    print(f"{'Plataforma':<20} {'HTTP':<6} {'Resultado':<40} {'Titulo'}")
    print("-" * 88)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            locale="en-GB",
            timezone_id="Europe/London",
            user_agent=UA,
            viewport={"width": 1440, "height": 900},
            extra_http_headers={
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        results = []
        for name, url in TARGETS:
            name, status, verdict, title = await probe(context, name, url)
            results.append((name, status, verdict))
            print(f"{name:<20} {status:<6} {verdict:<40} {title}")

        await browser.close()

    print("-" * 88)
    ok = [r for r in results if r[2].startswith("OK")]
    partial = [r for r in results if r[2].startswith("ABRIU")]
    bad = [r for r in results if not r[2].startswith(("OK", "ABRIU"))]

    print(f"\nAcessiveis com links de vaga: {len(ok)}")
    for r in ok:
        print(f"  + {r[0]}")
    print(f"\nAbrem mas precisam de seletor melhor: {len(partial)}")
    for r in partial:
        print(f"  ~ {r[0]}")
    print(f"\nBloqueados ou com erro: {len(bad)}")
    for r in bad:
        print(f"  - {r[0]}: {r[2]}")


if __name__ == "__main__":
    asyncio.run(main())
