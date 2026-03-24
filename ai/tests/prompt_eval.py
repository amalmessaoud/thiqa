"""
تقييم دقة نظام تحليل النصوص
شغّل من جذر المشروع مع تفعيل البيئة الافتراضية:
    python ai/tests/prompt_eval.py
"""
import sys
sys.path.insert(0, ".")

from ai import analyze_text

# Format: (text, expected_label, expected_scam_type or None)
EVAL_SET = [
    # ADVANCE PAYMENT
    (
        "حول خمسة آلاف دينار على البريدي موب قبل ما نبعث ليك",
        "scam", "advance_payment"
    ),
    (
        "دير التحويل على البريدي موب وراه نبعث ليك",
        "scam", "advance_payment"
    ),
    (
        "والله صاحبي ثق فيا، دير التحويل الأول وراه نكملو",
        "scam", "advance_payment"
    ),
    (
        "البريدي موب فقط، ما نقبلش الدفع عند الاستلام",
        "scam", "advance_payment"
    ),
    (
        "عطيني ألفين مسبقاً ونكملو",
        "scam", "advance_payment"
    ),

    # GHOST SELLER
    (
        "أنا في الخارج نبعث بأمانة، دير التحويل",
        "scam", "ghost_seller"
    ),
    (
        "ما نقدرش نتلاقاو أنا بعيد، حول لي الفلوس",
        "scam", "ghost_seller"
    ),

    # FAKE PRODUCT
    (
        "عندي آيفون أوريجينال بسعر رخيص، ما نقدرش تجي تشوفه",
        "scam", "fake_product"
    ),
    (
        "جديد في الكرتون ما فتحتوش، نبعث ليك غير، ما نقدرش تشوفه",
        "scam", "fake_product"
    ),

    # LEGIT
    (
        "تقدر تجي تشوف البضاعة وتخلص كاش",
        "legit", None
    ),
    (
        "ندير الدفع عند الاستلام فقط",
        "legit", None
    ),
    (
        "عندي محل في باب الزوار، تعال تشوف",
        "legit", None
    ),
    (
        "نبعث بياليدين، تخلص عند الاستلام",
        "legit", None
    ),
    (
        "البضاعة في الدار، تقدر تجي في أي وقت",
        "legit", None
    ),
]


def run_eval():
    print("جاري تقييم النظام...\n")

    total = len(EVAL_SET)
    label_correct = 0
    scam_type_correct = 0
    scam_type_applicable = 0

    rows = []

    for text, expected_label, expected_scam_type in EVAL_SET:
        result = analyze_text(text)
        got_label = result["label"]
        got_scam_type = result["scam_type"]

        label_ok = got_label == expected_label

        scam_type_ok = None
        if expected_scam_type is not None:
            scam_type_applicable += 1
            scam_type_ok = got_scam_type == expected_scam_type
            if scam_type_ok:
                scam_type_correct += 1

        if label_ok:
            label_correct += 1

        status = "✓" if label_ok else "✗"
        rows.append((
            status,
            text[:45],
            expected_label,
            got_label,
            str(expected_scam_type),
            str(got_scam_type)
        ))

    # Print table
    print(f"{'':2} {'النص':<47} {'متوقع':<10} {'ناتج':<10} {'نوع متوقع':<20} {'نوع ناتج'}")
    print("-" * 105)
    for status, text, exp_label, got_label, exp_type, got_type in rows:
        print(f"{status}  {text:<47} {exp_label:<10} {got_label:<10} {exp_type:<20} {got_type}")

    label_accuracy = label_correct / total * 100
    scam_type_accuracy = (
        scam_type_correct / scam_type_applicable * 100
        if scam_type_applicable else 0
    )

    print("\n" + "=" * 55)
    print(f"دقة التصنيف (Label Accuracy)    : {label_correct}/{total}  ({label_accuracy:.1f}%)")
    print(f"دقة نوع النصب (Scam Type Acc.)  : {scam_type_correct}/{scam_type_applicable}  ({scam_type_accuracy:.1f}%)")
    print("=" * 55)

    return label_accuracy, scam_type_accuracy


if __name__ == "__main__":
    run_eval()