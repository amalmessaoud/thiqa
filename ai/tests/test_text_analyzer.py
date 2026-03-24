import sys
sys.path.insert(0, ".")

from ai.text_analyzer.llm_analyzer import analyze_text

# --- Test cases — all Arabic/Darija in Arabic letters ---

SCAM_CASES = [
    "حول خمسة آلاف دينار على البريدي موب قبل ما نبعث ليك",
    "أنا في الخارج، دير التحويل على البريدي موب ونبعث ليك بأمانة",
    "ثق فيا خويا، دير التحويل وراه نكملو، والله ما نكذبك",
]

LEGIT_CASES = [
    "البضاعة عندي في الدار، تقدر تجي تشوفها وتخلص كاش",
    "ندير الدفع عند الاستلام فقط، ما نقبلش تحويل مسبق",
]

CONVO_SCAM = """
واش البضاعة مازالت؟
ايه مازالت خويا
بكاش تبعث؟
خير دير التحويل الأول على البريدي موب وراه نبعث
علاش ما تديرش الدفع عند الاستلام؟
معندكش هاد الخدمة، ثق فيا خويا، ديما نبيع وما كانش مشكل
"""

CONVO_LEGIT = """
سلام، واش عندك قميص مقاس لارج؟
ايه عندي
بكاش؟
بألف وثمانمية دينار
كيفاش ندفع؟
تجي تشوف وتخلص، ولا نبعث ليك بياليدين وتخلص عند الاستلام
"""

EDGE_CASES = [
    ("سلسلة فارغة", "", "unknown"),
    ("مسافات فقط", "   ", "unknown"),
    ("نص طويل جداً", "خويا " * 500 + " دير التحويل على البريدي موب", "scam"),
]


def _print_result(label, text, result):
    preview = text[:60].replace("\n", " ") + ("..." if len(text) > 60 else "")
    print(f"\n  المدخل   : {preview}")
    print(f"  label    : {result['label']}")
    print(f"  scam_type: {result['scam_type']}")
    print(f"  red_flags: {result['red_flags']}")
    print(f"  verdict  : {result['verdict_darija']}")
    print(f"  safe     : {result['safe_to_proceed']}")


def test_required_keys():
    """كل نتيجة لازم تحتوي على المفاتيح الخمسة بالأنواع الصحيحة"""
    print("\n=== test_required_keys ===")
    result = analyze_text("اختبار")
    assert "label" in result
    assert "scam_type" in result
    assert "red_flags" in result
    assert isinstance(result["red_flags"], list)
    assert "verdict_darija" in result
    assert isinstance(result["verdict_darija"], str)
    assert len(result["verdict_darija"]) > 0
    assert "safe_to_proceed" in result
    assert isinstance(result["safe_to_proceed"], bool)
    print("  PASS")


def test_scam_detection():
    print("\n=== test_scam_detection ===")
    for text in SCAM_CASES:
        result = analyze_text(text)
        _print_result("SCAM", text, result)
        assert result["label"] == "scam", f"Expected scam, got: {result['label']}"
        print("  PASS")


def test_legit_detection():
    print("\n=== test_legit_detection ===")
    for text in LEGIT_CASES:
        result = analyze_text(text)
        _print_result("LEGIT", text, result)
        assert result["label"] == "legit", f"Expected legit, got: {result['label']}"
        print("  PASS")


def test_full_conversation_scam():
    print("\n=== test_full_conversation_scam ===")
    result = analyze_text(CONVO_SCAM)
    _print_result("CONVO SCAM", CONVO_SCAM, result)
    assert result["label"] == "scam", f"Expected scam, got: {result['label']}"
    print("  PASS")


def test_full_conversation_legit():
    print("\n=== test_full_conversation_legit ===")
    result = analyze_text(CONVO_LEGIT)
    _print_result("CONVO LEGIT", CONVO_LEGIT, result)
    assert result["label"] == "legit", f"Expected legit, got: {result['label']}"
    print("  PASS")


def test_edge_cases():
    print("\n=== test_edge_cases ===")
    for name, text, expected_label in EDGE_CASES:
        result = analyze_text(text)
        _print_result(f"EDGE:{name}", text, result)
        assert "label" in result
        assert isinstance(result["red_flags"], list)
        assert isinstance(result["safe_to_proceed"], bool)
        assert result["label"] == expected_label, \
            f"[{name}] Expected {expected_label}, got {result['label']}"
        print("  PASS")


if __name__ == "__main__":
    test_required_keys()
    test_scam_detection()
    test_legit_detection()
    test_full_conversation_scam()
    test_full_conversation_legit()
    test_edge_cases()
    print("\n=== ALL TEXT ANALYZER TESTS PASSED ===")