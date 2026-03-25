import os
import sys
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List

from app.schemas.schemas import (
    TextAnalyzeRequest,
    TextAnalyzeResponse,
    ScreenshotAnalyzeResponse,
)
from ai import analyze_text, analyze_screenshots

router = APIRouter()


@router.post("/text/", response_model=TextAnalyzeResponse)
def analyze_text_endpoint(body: TextAnalyzeRequest):
    """
    Analyze a pasted DM, conversation, or listing text for scam patterns.
    No auth required.
    """
    try:
        result = analyze_text(body.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

    return TextAnalyzeResponse(
        label=result["label"],
        scam_type=result.get("scam_type"),
        red_flags=result.get("red_flags", []),
        verdict_darija=result["verdict_darija"],
        safe_to_proceed=result["safe_to_proceed"],
    )


@router.post("/screenshot/", response_model=ScreenshotAnalyzeResponse)
def analyze_screenshot_endpoint(
    screenshots: List[UploadFile] = File(..., description="One or more screenshot images")
):
    """
    Upload one or multiple screenshots. OCR extracts text, then scam analysis runs.
    No auth required.
    """
    if not screenshots:
        raise HTTPException(status_code=400, detail="At least one screenshot is required")

    # Validate file types
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    for file in screenshots:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Only JPEG, PNG, WEBP allowed."
            )

    temp_paths = []

    try:
        # Save each uploaded file to a temp file on disk
        for file in screenshots:
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = file.file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)

        # Run OCR + analysis pipeline
        result = analyze_screenshots(temp_paths)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot analysis failed: {str(e)}")

    finally:
        # Always clean up temp files — even if analysis crashed
        for path in temp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

    # Build analysis response if OCR succeeded
    analysis_response = None
    if result.get("analysis"):
        a = result["analysis"]
        analysis_response = TextAnalyzeResponse(
            label=a["label"],
            scam_type=a.get("scam_type"),
            red_flags=a.get("red_flags", []),
            verdict_darija=a["verdict_darija"],
            safe_to_proceed=a["safe_to_proceed"],
        )

    return ScreenshotAnalyzeResponse(
        extracted_text=result["extracted_text"],
        confidence=result["confidence"],
        word_count=result["word_count"],
        extraction_successful=result["extraction_successful"],
        images_processed=result["images_processed"],
        images_failed=result["images_failed"],
        analysis=analysis_response,
    )


# Keep image stub — will be replaced when fake detector is built
@router.post("/image/")
def analyze_image():
    """STATUS: STUB — fake image detector not yet implemented"""
    return {"is_fake": False, "fake_probability": 0.0, "verdict": "stub — not implemented yet"}