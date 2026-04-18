from fastapi import FastAPI, UploadFile, File, Form
import tempfile
import os
from graph import graph

app = FastAPI()

@app.post("/api/process")
async def process_claim(
    claim_id: str = Form(...),
    file: UploadFile = File(...)
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    result = graph.invoke({
        "pdf_path": tmp_path
    })

    os.remove(tmp_path)

    return {
        "claim_id": claim_id,
        "status": "success",
        "page_classifications": result["classifications"],
        "extracted_data": result["final_output"]
    }