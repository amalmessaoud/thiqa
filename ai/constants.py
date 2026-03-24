from enum import Enum


class ScamType(str, Enum):
    GHOST_SELLER = "ghost_seller"
    ADVANCE_PAYMENT = "advance_payment"
    FAKE_PRODUCT = "fake_product"
    WRONG_ITEM = "wrong_item"
    NO_RESPONSE = "no_response"
    OTHER = "other"


# Screens/phrases OCR might extract that indicate the buyer was blocked or ignored
# Used by credibility scorer to recognize no_response evidence
NO_RESPONSE_PATTERNS = [
    "لا يمكنك الرد على هذه المحادثة",
    "تم حظرك",
    "لا يمكن إرسال رسائل إلى هذا الحساب",
    "هذا الحساب غير متاح",
    "المحادثة غير متاحة",
    "you can't reply to this conversation",
    "you've been blocked",
    "this account is unavailable",
    "message failed to send",
]

# Scam type weights used in trust score formula — defined once here
SCAM_TYPE_WEIGHTS = {
    ScamType.GHOST_SELLER: 25,
    ScamType.ADVANCE_PAYMENT: 25,
    ScamType.FAKE_PRODUCT: 20,
    ScamType.WRONG_ITEM: 10,
    ScamType.NO_RESPONSE: 10,
    ScamType.OTHER: 8,
}