import sys
sys.path.insert(0, ".")

from ai.ocr.screenshot_extractor import extract_text_from_screenshot, analyze_screenshots

SINGLE_IMAGE = "ai/tests/sample_screenshot.png"
MULTI_IMAGES = [
    "ai/tests/sample_screenshot.png",
    "ai/tests/sample_screenshot_2.png",
]
FAKE_PATH = "ai/tests/does_not_exist.png"


def _print_ocr(label, result):
    print(f"\n[{label}]")
    print(f"  success   : {result['extraction_successful']}")
    print(f"  confidence: {result['confidence']}")
    print(f"  word_count: {result['word_count']}")
    preview = result['extracted_text'][:120].replace("\n", " ")
    print(f"  text      : {preview}...")


def test_single_image():
    print("\n=== test_single_image ===")
    result = extract_text_from_screenshot(SINGLE_IMAGE)
    _print_ocr("single", result)
    assert result["extraction_successful"] is True
    assert len(result["extracted_text"]) > 0
    assert isinstance(result["confidence"], float)
    assert result["word_count"] > 0
    print("  PASS")


def test_bad_path():
    """Must not crash on missing file — returns extraction_successful=False."""
    print("\n=== test_bad_path ===")
    result = extract_text_from_screenshot(FAKE_PATH)
    _print_ocr("bad path", result)
    assert result["extraction_successful"] is False
    assert result["extracted_text"] == ""
    print("  PASS")


def test_analyze_screenshots_single():
    """analyze_screenshots with one image must return analysis."""
    print("\n=== test_analyze_screenshots_single ===")
    result = analyze_screenshots([SINGLE_IMAGE])
    _print_ocr("analyze_screenshots single", result)
    print(f"  images_processed: {result['images_processed']}")
    print(f"  images_failed   : {result['images_failed']}")
    print(f"  analysis.label  : {result['analysis']['label'] if result['analysis'] else 'None'}")
    assert result["extraction_successful"] is True
    assert result["images_processed"] == 1
    assert result["images_failed"] == 0
    assert result["analysis"] is not None
    assert "label" in result["analysis"]
    assert "verdict_darija" in result["analysis"]
    print("  PASS")


def test_analyze_screenshots_multi():
    """analyze_screenshots with two images — text merged, one combined analysis."""
    print("\n=== test_analyze_screenshots_multi ===")
    result = analyze_screenshots(MULTI_IMAGES)
    _print_ocr("analyze_screenshots multi", result)
    print(f"  images_processed: {result['images_processed']}")
    print(f"  images_failed   : {result['images_failed']}")
    print(f"  analysis.label  : {result['analysis']['label'] if result['analysis'] else 'None'}")
    assert result["extraction_successful"] is True
    assert result["images_processed"] == 2
    assert result["analysis"] is not None
    # merged text should contain the separator
    assert "---" in result["extracted_text"]
    print("  PASS")


def test_analyze_screenshots_empty_list():
    """Empty list must not crash — returns extraction_successful=False, analysis=None."""
    print("\n=== test_analyze_screenshots_empty_list ===")
    result = analyze_screenshots([])
    _print_ocr("empty list", result)
    assert result["extraction_successful"] is False
    assert result["analysis"] is None
    print("  PASS")


def test_analyze_screenshots_one_bad_path():
    """One real image + one fake path — processes 1, fails 1, still returns analysis."""
    print("\n=== test_analyze_screenshots_one_bad_path ===")
    result = analyze_screenshots([SINGLE_IMAGE, FAKE_PATH])
    _print_ocr("one bad path", result)
    print(f"  images_processed: {result['images_processed']}")
    print(f"  images_failed   : {result['images_failed']}")
    assert result["images_processed"] == 1
    assert result["images_failed"] == 1
    assert result["extraction_successful"] is True  # one succeeded
    assert result["analysis"] is not None
    print("  PASS")


if __name__ == "__main__":
    test_single_image()
    test_bad_path()
    test_analyze_screenshots_single()
    test_analyze_screenshots_multi()
    test_analyze_screenshots_empty_list()
    test_analyze_screenshots_one_bad_path()
    print("\n=== ALL OCR TESTS PASSED ===")