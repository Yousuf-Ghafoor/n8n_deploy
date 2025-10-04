from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from dekalb import  fetch_bill_sync
from gwinnet import ParcelRequest, download_parcel
from carroll import capture_tax_bill_image
from troup import fetch_all_bill_pdfs ,PropertyRequest
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re
import io

app = FastAPI()


@app.post("/dekalb_automation")
async def generate_pdf(data: ParcelRequest):
    parcel = data.parcel_id.strip()

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        pdf_bytes = await loop.run_in_executor(pool, fetch_bill_sync, parcel)

    headers = {"Content-Disposition": f'attachment; filename="{parcel}_bill.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/gwinnett_automation")
def post_tax_bill(request: ParcelRequest):
    """Download a parcel tax bill by POSTing a parcel_id in JSON."""
    parcel_id = request.parcel_id.strip()
    pdf_bytes = download_parcel(parcel_id, headless=True)

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Tax bill not found")

    headers = {"Content-Disposition": f'attachment; filename="{parcel_id}_bill.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/carroll_automation")
def get_tax_bill(request: ParcelRequest):
    image_bytes = capture_tax_bill_image(request.parcel_id)

    safe_id = re.sub(r'[^A-Za-z0-9_-]', "_", request.parcel_id)
    filename = f"{safe_id}.png"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers=headers
    )
    
@app.post("/troup_automation")
def get_property_bills(request: PropertyRequest):
    filename, pdf_bytes = fetch_all_bill_pdfs(request.property_id, request.tax_year)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
