from fastapi import FastAPI, HTTPException, Response
from dekalb import ClientPayload, fetch_bill_sync
from gwinnet import ParcelRequest, download_parcel
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()


@app.post("/dekalb_automation")
async def generate_pdf(data: ClientPayload):
    parcel = data.parcel.strip()

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
