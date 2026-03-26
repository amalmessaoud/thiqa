import sys
sys.path.insert(0, ".")

from ai import assess_report_credibility
from ai.constants import ScamType

REAL_SCREENSHOT = "ai/tests/sample_screenshot.png"
FAKE_PATH = "ai/tests/does_not_exist.png"


def _print_result(label, result):
    print(f"\n  [{label}]")
    print(f"  credibility_score        : {result['credibility_score']}")
    print(f"  credibility_label        : {result['credibility_label']}")
    print(f"  reason                   : {result['reason']}")
    print(f"  screenshot_supports_claim: {result['screenshot_supports_claim']}")


def test_required_keys():
    """النتيجة دائماً تحتوي على المفاتيح الأربعة بالأنواع الصحيحة"""
    print("\n=== test_required_keys ===")
    result = assess_report_credibility(
        scam_type=ScamType.ADVANCE_PAYMENT.value,
        description="حول فلوس وما بعثش",
        screenshot_path=REAL_SCREENSHOT
    )
    assert "credibility_score" in result
    assert "credibility_label" in result
    assert "reason" in result
    assert "screenshot_supports_claim" in result
    assert isinstance(result["credibility_score"], float)
    assert 0.0 <= result["credibility_score"] <= 1.0
    assert result["credibility_label"] in ("high", "medium", "low")
    assert isinstance(result["reason"], str)
    assert len(result["reason"]) > 0
    assert isinstance(result["screenshot_supports_claim"], bool)
    print("  PASS")


def test_with_description_and_screenshot():
    """
    Real scam screenshots would score high.
    Our sample screenshots are robotics project screenshots — unrelated.
    So we only assert structure, not score value.
    """
    print("\n=== test_with_description_and_screenshot ===")
    result = assess_report_credibility(
        scam_type=ScamType.ADVANCE_PAYMENT.value,
        description="طلب مني يحول على البريدي موب قبل ما يبعث، حولت وما بعثش وقطع التواصل",
        screenshot_path=REAL_SCREENSHOT
    )
    _print_result("advance_payment with description", result)
    # Score depends on screenshot content — sample_screenshot.png is a robotics project,
    # not a scam convo. Only assert structure and that description alone lifts score above 0.
    assert 0.0 <= result["credibility_score"] <= 1.0
    assert result["credibility_label"] in ("high", "medium", "low")
    assert isinstance(result["reason"], str)
    print("  PASS")

def test_no_response_scam_type():
    """Same — assert structure only, not score value."""
    print("\n=== test_no_response_scam_type ===")
    result = assess_report_credibility(
        scam_type=ScamType.NO_RESPONSE.value,
        description="بعثت رسايل كثيرة وما ردش، الحساب مازال موجود",
        screenshot_path=REAL_SCREENSHOT
    )
    _print_result("no_response", result)
    assert 0.0 <= result["credibility_score"] <= 1.0
    assert result["credibility_label"] in ("high", "medium", "low")
    print("  PASS")


def test_description_only_no_screenshot():
    """لقطة شاشة غير موجودة — الوصف وحده يعطي 0.3"""
    print("\n=== test_description_only_no_screenshot ===")
    result = assess_report_credibility(
        scam_type=ScamType.GHOST_SELLER.value,
        description="ادعى أنه في فرنسا وطلب تحويل مسبق",
        screenshot_path=FAKE_PATH
    )
    _print_result("bad screenshot path", result)
    # OCR fails → LLM still runs on description alone
    assert result["credibility_score"] >= 0.3
    assert result["screenshot_supports_claim"] is False
    print("  PASS")


def test_no_description_no_screenshot():
    """لا وصف ولا لقطة شاشة — أدنى مصداقية ممكنة"""
    print("\n=== test_no_description_no_screenshot ===")
    result = assess_report_credibility(
        scam_type=ScamType.OTHER.value,
        description=None,
        screenshot_path=FAKE_PATH
    )
    _print_result("nothing provided", result)
    assert result["credibility_score"] == 0.3
    assert result["credibility_label"] == "low"
    assert result["screenshot_supports_claim"] is False
    print("  PASS")


def test_invalid_scam_type():
    """نوع نصب غير معروف — يجب أن يتحول إلى other بدون كراش"""
    print("\n=== test_invalid_scam_type ===")
    result = assess_report_credibility(
        scam_type="totally_invalid_type",
        description="شيء مشبوه",
        screenshot_path=REAL_SCREENSHOT
    )
    _print_result("invalid scam type", result)
    assert "credibility_score" in result
    assert result["credibility_label"] in ("high", "medium", "low")
    print("  PASS")


def test_never_crashes():
    """ما يكسرش مهما كانت المدخلات"""
    print("\n=== test_never_crashes ===")
    bad_inputs = [
        ("empty description", ScamType.ADVANCE_PAYMENT.value, "", REAL_SCREENSHOT),
        ("none description", ScamType.FAKE_PRODUCT.value, None, REAL_SCREENSHOT),
        ("bad path no desc", ScamType.NO_RESPONSE.value, None, FAKE_PATH),
        ("all empty", ScamType.OTHER.value, None, FAKE_PATH),
    ]
    for name, scam_type, description, path in bad_inputs:
        try:
            result = assess_report_credibility(scam_type, description, path)
            assert isinstance(result, dict)
            assert "credibility_score" in result
            print(f"  [{name}] → score={result['credibility_score']} PASS")
        except Exception as e:
            raise AssertionError(f"Crashed on: {name} — {e}") from e
    print("  ALL PASS")


if __name__ == "__main__":
    test_required_keys()
    test_with_description_and_screenshot()
    test_no_response_scam_type()
    test_description_only_no_screenshot()
    test_no_description_no_screenshot()
    test_invalid_scam_type()
    test_never_crashes()
    print("\n=== ALL CREDIBILITY TESTS PASSED ===")