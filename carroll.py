from fastapi import  HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import time

URL = "https://carrollproperty.assurancegov.com/Property/Search"


class ParcelRequest(BaseModel):
    parcel_id: str


def capture_tax_bill_image(parcel_id: str) -> bytes:
    """Capture the tax bill screenshot and return it as bytes (no file saved)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Load search page
            page.goto(URL, timeout=60000)
            page.wait_for_selector("#searchform", timeout=15000)

            # Select "Parcel"
            page.locator("#parcel").check(timeout=5000)
            page.wait_for_timeout(300)

            # Fill parcel number
            page.locator("#pt-search-editor-1").fill(parcel_id, timeout=5000)

            # Click Search
            page.locator("#pt-search-button").click()

            # Wait for grid
            row_locator = "#gridResults tbody tr"
            try:
                page.locator(row_locator).first.wait_for(state="visible", timeout=20000)
            except PlaywrightTimeoutError:
                raise HTTPException(status_code=404, detail=f"No results found for parcel '{parcel_id}'")

            # Find Details button
            first_row = page.locator(row_locator).first
            details_button = first_row.locator(
                "a:has-text('Details'), a:has-text('DETAILS'), button:has-text('Details'), button:has-text('DETAILS')"
            )
            if details_button.count() == 0:
                raise HTTPException(status_code=404, detail="No 'Details' button found")

            # Open details page
            with page.context.expect_page() as new_page_info:
                details_button.first.click()
            detail_page = new_page_info.value
            detail_page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Click "View Tax Bill"
            tax_bill_button = detail_page.locator("a:has-text('View Tax Bill'), button:has-text('View Tax Bill')")
            if tax_bill_button.count() == 0:
                raise HTTPException(status_code=404, detail="No 'View Tax Bill' button found")

            with detail_page.expect_popup() as popup_info:
                tax_bill_button.first.click()
            tax_page = popup_info.value
            tax_page.wait_for_load_state("domcontentloaded", timeout=25000)

            # Take screenshot in memory
            image_bytes = tax_page.screenshot(full_page=True, timeout=25000)
            return image_bytes

        finally:
            time.sleep(0.5)
            browser.close()



