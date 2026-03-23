"""
Tier configuration — single source of truth for all usage limits.

When subscription tiers are added, update TIER_CONFIGS here.
No other file should hardcode session limits or question-count caps.

For local development, set DEFAULT_TIER=dev in .env to bypass limits.
"""
import os

TIER_CONFIGS: dict[str, dict] = {
    "free": {
        "daily_session_limit": 3,
        "max_question_count": 10,
        "question_count_options": [5, 10],
    },
    "paid": {
        "daily_session_limit": 50,
        "max_question_count": 20,
        "question_count_options": [5, 10, 15, 20],
    },
    "dev": {
        "daily_session_limit": 9999,
        "max_question_count": 20,
        "question_count_options": [5, 10, 15, 20],
    },
}

DEFAULT_TIER = os.getenv("DEFAULT_TIER", "free")


def get_tier_config(tier: str = DEFAULT_TIER) -> dict:
    """Return the config dict for *tier*, falling back to the free tier."""
    cfg = TIER_CONFIGS.get(tier, TIER_CONFIGS[DEFAULT_TIER])
    return {"tier": tier if tier in TIER_CONFIGS else DEFAULT_TIER, **cfg}
