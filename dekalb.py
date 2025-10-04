from fastapi import  HTTPException
from playwright.sync_api import sync_playwright
import httpx
from urllib.parse import urljoin

START_URL = "https://publicaccess.dekalbtax.org/Datalets/Datalet.aspx?sIndex=2&idx=1"

# ------------------------
# Playwright scraping (sync version)
# ------------------------
def fetch_bill_sync(parcel: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(START_URL, timeout=120000)

        # Accept agreement if present
        try:
            page.wait_for_selector("button#btAgree", timeout=5000)
            page.click("button#btAgree")
            page.wait_for_load_state("networkidle")
        except Exception:
            pass  # no button, continue

        # Fill parcel ID
        page.fill("input#inpParid", parcel)

        # Try multiple possible search button selectors
        search_selectors = [
            "input#btSearch",
            "button#btSearch",
            "input[name='btSearch']",
            "input[value='Search']",
            "button:has-text('Search')",
        ]
        clicked = False
        for sel in search_selectors:
            try:
                page.click(sel, timeout=3000)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            browser.close()
            raise HTTPException(status_code=500, detail="Search button not found")

        page.wait_for_load_state("networkidle")

        # Click result row with the parcel
        try:
            page.wait_for_selector(
                f"tr.SearchResults:has-text('{parcel}')", timeout=8000
            )
            page.click(f"tr.SearchResults:has-text('{parcel}')")
            page.wait_for_load_state("networkidle")
        except Exception:
            browser.close()
            raise HTTPException(status_code=404, detail="Parcel not found")

        # Find bill link
        bill_link = None
        try:
            page.wait_for_selector("div#datalet_div_7 table a", timeout=10000)
            element = page.query_selector("div#datalet_div_7 table a")
            bill_link = element.get_attribute("href") if element else None
        except Exception:
            bill_link = None

        if not bill_link:
            browser.close()
            raise HTTPException(status_code=404, detail="Bill link not found")

        # Normalize link
        bill_url = bill_link.replace("\\", "/")
        if bill_url.startswith("/"):
            bill_url = urljoin(page.url, bill_url)

        browser.close()

    # Fetch the PDF
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(bill_url)
        if resp.status_code != 200 or not resp.content:
            raise HTTPException(status_code=502, detail="Failed to download bill PDF")

    return resp.content


