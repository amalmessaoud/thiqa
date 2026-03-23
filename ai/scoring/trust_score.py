def calculate_trust_score(signals: dict) -> dict:
    """
    STATUS: STUB
    Expected signals keys:
      report_count: int
      positive_reviews: int
      warning_group_mentions: int
      text_analysis: dict | None
      image_result: dict | None
      comment_sentiment: dict | None
      account_age_days: int | None
      post_count: int | None
    """
    return {
        "score": 23,
        "verdict": "Avoid",
        "verdict_darija": "تجنب هذا البائع، فيه علامات نصب واضحة",
        "verdict_color": "red",
        "penalties": [
            {"reason": "3+ community reports", "points": -40},
            {"reason": "AI-generated profile photo", "points": -20}
        ],
        "bonuses": []
    }