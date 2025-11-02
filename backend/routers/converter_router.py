# backend/routers/converter_router.py
from fastapi import APIRouter, UploadFile, File, Form
from services import converter_service
from pathlib import Path
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/convert", tags=["converter"])

@router.post("/start")
async def start_conversion(
    uploaded_file: UploadFile,
    language: str = Form(...),
    user_id: str = Form(...)
):
    """
    Start a conversion for uploaded file/archive.
    """
    # Save uploaded file to temp folder
    upload_dir = Path("./temp_uploads") / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / uploaded_file.filename
    with open(file_path, "wb") as f:
        f.write(await uploaded_file.read())

    # Call service to start conversion
    session_id = converter_service.start_conversion(file_path, language, user_id)
    return {"session_id": session_id}


@router.get("/status/{session_id}")
async def conversion_status(session_id: str):
    """
    Check conversion status from metadata.json.
    """
    from utils.file_ops import read_json  # utility to read JSON safely
    session_path = Path("./sessions") / session_id
    metadata_file = session_path / "metadata.json"
    if not metadata_file.exists():
        return JSONResponse({"error": "Session not found"}, status_code=404)
    metadata = read_json(metadata_file)
    return metadata
