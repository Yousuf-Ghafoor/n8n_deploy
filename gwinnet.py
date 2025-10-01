from urllib.parse import quote
from playwright.sync_api import sync_playwright
from pydantic import BaseModel


class ParcelRequest(BaseModel):
    parcel_id: str

BASE = "https://www.gwinnetttaxcommissioner.com/PropTaxBill"

def make_candidates(parcel_id: str):
    p = parcel_id.strip()
    candidates = []

    candidates.append(f"{BASE}/{quote(p)}.pdf")

    if len(p) >= 3:
        candidates.append(f"{BASE}/{quote(p[:-3])}%20{quote(p[-3:])}.pdf")

    if len(p) >= 4:
        candidates.append(f"{BASE}/{quote(p[:-4])}%20{quote(p[-4:])}.pdf")

    seen, out = set(), []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_parcel(parcel_id: str, headless=True, timeout_ms=60_000) -> bytes | None:
    """
    Try downloading the PDF for a given parcel_id.
    Returns PDF bytes if found, else None.
    """
    urls = make_candidates(parcel_id)
    headers = {
        "Referer": "https://www.gwinnetttaxcommissioner.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        for url in urls:
            try:
                resp = page.request.get(url, headers=headers, timeout=timeout_ms)
            except Exception:
                continue

            status = resp.status
            body = resp.body() or b""
            length = len(body)
            ctype = resp.headers.get("content-type", "").lower()
            disp = resp.headers.get("content-disposition", "").lower()

            is_pdf = (
                status == 200 and (
                    ("pdf" in ctype)
                    or ("attachment" in disp)
                    or length > 2000
                )
            )

            if is_pdf:
                browser.close()
                return body  # return bytes directly

        browser.close()
    return None
