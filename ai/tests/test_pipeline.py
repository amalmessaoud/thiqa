import sys
sys.path.insert(0, ".")

# Simulate exactly what the backend will do — import from ai only, never from submodules
from ai import analyze_text, analyze_screenshots

SINGLE_IMAGE = "ai/tests/sample_screenshot.png"
MULTI_IMAGES = [
    "ai/tests/sample_screenshot.png",
    "ai/tests/sample_screenshot_2.png",
]


def test_backend_text_endpoint():
    """
    Simulates POST /api/analyze/text/
    Backend receives: { "text": "..." }
    Backend calls: analyze_text(text)
    Backend returns: the result directly
    """
    print("\n=== test_backend_text_endpoint ===")

    # Single message
    payload_text = "دير التحويل على BaridiMob قبل ما نبعث ليك"
    result = analyze_text(payload_text)

    print(f"  text input : {payload_text}")
    print(f"  label      : {result['label']}")
    print(f"  scam_type  : {result['scam_type']}")
    print(f"  red_flags  : {result['red_flags']}")
    print(f"  verdict    : {result['verdict_darija']}")
    print(f"  safe       : {result['safe_to_proceed']}")

    assert result["label"] in ("scam", "legit", "unknown")
    assert isinstance(result["red_flags"], list)
    assert isinstance(result["safe_to_proceed"], bool)
    assert len(result["verdict_darija"]) > 0
    print("  PASS")


def test_backend_text_endpoint_convo():
    """
    Simulates POST /api/analyze/text/ with a pasted DM conversation.
    """
    print("\n=== test_backend_text_endpoint_convo ===")

    convo = """
    واش عندك iPhone؟
    ايه عندي 13 Pro
    بكاش؟
    بـ 55000 دج
    تقبل الدفع عند الاستلام؟
    لا خويا، دير التحويل على BaridiMob الأول، ثق فيا
    علاش؟
    هكذا كانشتغل دايما
    """

    result = analyze_text(convo)

    print(f"  label     : {result['label']}")
    print(f"  scam_type : {result['scam_type']}")
    print(f"  red_flags : {result['red_flags']}")
    print(f"  verdict   : {result['verdict_darija']}")

    assert result["label"] == "scam"
    assert result["scam_type"] == "advance_payment"
    print("  PASS")


def test_backend_screenshot_endpoint_single():
    """
    Simulates POST /api/analyze/screenshot/ with one uploaded file.
    Backend saves temp file → calls analyze_screenshots([path]) → deletes temp file.
    """
    print("\n=== test_backend_screenshot_endpoint_single ===")

    # Backend would do: path = save_temp(uploaded_file)
    temp_paths = [SINGLE_IMAGE]

    result = analyze_screenshots(temp_paths)

    print(f"  extracted_text (preview): {result['extracted_text'][:80]}...")
    print(f"  confidence      : {result['confidence']}")
    print(f"  images_processed: {result['images_processed']}")
    print(f"  images_failed   : {result['images_failed']}")
    print(f"  analysis.label  : {result['analysis']['label'] if result['analysis'] else None}")
    print(f"  analysis.verdict: {result['analysis']['verdict_darija'] if result['analysis'] else None}")

    assert result["extraction_successful"] is True
    assert result["analysis"] is not None
    assert "label" in result["analysis"]
    assert "red_flags" in result["analysis"]
    assert "verdict_darija" in result["analysis"]
    assert "safe_to_proceed" in result["analysis"]
    print("  PASS")


def test_backend_screenshot_endpoint_multi():
    """
    Simulates POST /api/analyze/screenshot/ with multiple uploaded files.
    """
    print("\n=== test_backend_screenshot_endpoint_multi ===")

    temp_paths = MULTI_IMAGES

    result = analyze_screenshots(temp_paths)

    print(f"  images_processed: {result['images_processed']}")
    print(f"  images_failed   : {result['images_failed']}")
    print(f"  word_count      : {result['word_count']}")
    print(f"  analysis.label  : {result['analysis']['label'] if result['analysis'] else None}")

    assert result["images_processed"] == 2
    assert result["extraction_successful"] is True
    assert result["analysis"] is not None
    print("  PASS")


def test_backend_never_crashes():
    """
    Robustness test — backend must never get a 500 from AI functions.
    Throws bad inputs at both functions.
    """
    print("\n=== test_backend_never_crashes ===")

    bad_inputs = [
        ("empty string", lambda: analyze_text("")),
        ("whitespace", lambda: analyze_text("   ")),
        ("empty list", lambda: analyze_screenshots([])),
        ("bad path", lambda: analyze_screenshots(["nonexistent.png"])),
        ("none-like", lambda: analyze_text("null")),
    ]

    for name, fn in bad_inputs:
        try:
            result = fn()
            assert isinstance(result, dict), f"[{name}] result is not a dict"
            print(f"  [{name}] → {result.get('label', result.get('extraction_successful'))} PASS")
        except Exception as e:
            print(f"  [{name}] CRASH: {e}")
            raise AssertionError(f"Function crashed on input: {name}") from e

    print("  ALL PASS")


if __name__ == "__main__":
    test_backend_text_endpoint()
    test_backend_text_endpoint_convo()
    test_backend_screenshot_endpoint_single()
    test_backend_screenshot_endpoint_multi()
    test_backend_never_crashes()
    print("\n=== ALL PIPELINE TESTS PASSED ===")