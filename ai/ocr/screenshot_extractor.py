import easyocr

reader = easyocr.Reader(['ar', 'en'], gpu=False)


def extract_text_from_screenshot(image_path: str) -> dict:
    """Extract text from a single image. Returns raw OCR result."""
    try:
        results = reader.readtext(image_path)

        if not results:
            return {
                "extracted_text": "",
                "confidence": 0.0,
                "word_count": 0,
                "extraction_successful": False
            }

        texts = [text for (_, text, conf) in results]
        confidences = [conf for (_, _, conf) in results]

        full_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences)

        return {
            "extracted_text": full_text,
            "confidence": round(avg_confidence, 2),
            "word_count": len(full_text.split()),
            "extraction_successful": True
        }

    except Exception as e:
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "word_count": 0,
            "extraction_successful": False,
            "error": str(e)
        }


def analyze_screenshots(image_paths: list[str]) -> dict:
    """
    OCR one or multiple screenshots, merge the text, run scam analysis.
    This is the function the backend calls for POST /api/analyze/screenshot/

    Args:
        image_paths: list of temp file paths saved by the backend

    Returns:
        {
            extracted_text: str,
            confidence: float,
            word_count: int,
            extraction_successful: bool,
            images_processed: int,
            images_failed: int,
            analysis: { label, scam_type, red_flags, verdict_darija, safe_to_proceed } | None
        }
    """
    # Import here to avoid circular import
    from ai.text_analyzer.llm_analyzer import analyze_text

    if not image_paths:
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "word_count": 0,
            "extraction_successful": False,
            "images_processed": 0,
            "images_failed": 0,
            "analysis": None
        }

    all_texts = []
    all_confidences = []
    failed = 0

    for path in image_paths:
        ocr_result = extract_text_from_screenshot(path)
        if ocr_result["extraction_successful"] and ocr_result["extracted_text"].strip():
            all_texts.append(ocr_result["extracted_text"])
            all_confidences.append(ocr_result["confidence"])
        else:
            failed += 1

    # Nothing extracted from any image
    if not all_texts:
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "word_count": 0,
            "extraction_successful": False,
            "images_processed": len(image_paths) - failed,
            "images_failed": failed,
            "analysis": None
        }

    # Merge all images' text with a separator so the LLM knows they're separate screenshots
    merged_text = "\n---\n".join(all_texts)
    avg_confidence = sum(all_confidences) / len(all_confidences)

    analysis = analyze_text(merged_text)

    return {
        "extracted_text": merged_text,
        "confidence": round(avg_confidence, 2),
        "word_count": len(merged_text.split()),
        "extraction_successful": True,
        "images_processed": len(image_paths) - failed,
        "images_failed": failed,
        "analysis": analysis
    }