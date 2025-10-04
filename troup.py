from fastapi import  HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import json
import re


class PropertyRequest(BaseModel):
    property_id: str
    tax_year: int = 2025


def fetch_all_bill_pdfs(property_id: str, tax_year: int):
    URL = f"https://pay.troupcountytax.com/details?current_bill_amt=&tax_year={tax_year}&property_id={property_id}&hashid=rq16ank7fo9"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        authcode = [None]
        grid_data = []

        def handle_request(request):
            a = request.headers.get("authcode")
            if a and not authcode[0]:
                authcode[0] = a

        def handle_response(response):
            try:
                if (
                    "api/grid/content" in response.url
                    and "application/json" in response.headers.get("content-type", "")
                ):
                    data = response.json()
                    if isinstance(data, dict) and "gridData" in data:
                        grid_data.extend(data["gridData"])
            except Exception:
                pass

        page.on("request", handle_request)
        page.on("response", handle_response)

        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if not authcode[0]:
            browser.close()
            raise HTTPException(status_code=400, detail="Could not capture authcode")
        if not grid_data:
            browser.close()
            raise HTTPException(status_code=404, detail="No gridData found")

        headers = {
            "content-type": "application/json; charset=UTF-8",
            "origin": "https://pay.troupcountytax.com",
            "referer": "https://pay.troupcountytax.com/",
            "authcode": authcode[0],
            "accept": "application/pdf,application/json,*/*",
            "user-agent": "Mozilla/5.0",
        }

        record = grid_data[0]
        bill_no = str(record["bill_no"])
        tax_year = str(record["tax_year"])
        property_id = record["property_id"]

        payload = {
            "fields": [
                {"fieldName": "bill_no", "fieldValue": bill_no},
                {"fieldName": "tax_year", "fieldValue": tax_year},
                {"fieldName": "property_id", "fieldValue": property_id},
            ]
        }

        # Fetch PDF and read before closing browser
        resp = page.request.fetch(
            "https://taxpaymentapi.bisclient.com/api/bill-details/bill/pdf",
            method="POST",
            headers=headers,
            data=json.dumps(payload),
        )

        if not resp or resp.status != 200:
            browser.close()
            raise HTTPException(status_code=500, detail="Failed to fetch PDF")

        # Read bytes BEFORE closing browser
        pdf_bytes = resp.body()

        browser.close()

        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", property_id)
        filename = f"Bill_{bill_no}_{tax_year}_{safe_name}.pdf"

        return filename, pdf_bytes


