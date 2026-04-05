"""
companions.py
=============
Static mapping from (year_level, strand) tuples to lists of companion template IDs
drawn from adjacent year levels.

PURPOSE
-------
Some (year, strand) combinations have very few templates — as few as 1–4. With
random.choices (with replacement), a 10-question session can end up with 5 questions
from the same template, which feels repetitive to students.

Companion templates are on-topic templates from an adjacent year level (same strand)
that are injected into the selection pool when the native pool is too thin. They
provide variety without changing the difficulty or stranding a student on off-topic
material — they are revision / consolidation / gentle extension questions.

TRIGGER CONDITION
-----------------
Companions activate when:

    len(available_native) < count // COMPANION_TRIGGER_DIVISOR

For count=10 (default): triggers when native pool has fewer than 5 templates.
For count=5 (min):      triggers when native pool has fewer than 2 templates.

MAX COMPANION SLOTS
-------------------
At most COMPANION_FRACTION of the final pool may be companion templates (rounded
down, minimum 1). For count=10 this means at most 4 companions, so the session
is still dominated (≥60%) by on-year content.

ORDERING
--------
Templates listed earlier in each value list are preferred when the companion limit
is reached. Put the most pedagogically appropriate companions first.

HOW TO ADD A NEW MAPPING
------------------------
Add an entry to COMPANION_IDS:

    (year_level, strand): ["T-XY-01", "T-XY-02", ...]

All IDs must exist in docs/question_templates.json. No other file needs changing.
"""
from __future__ import annotations

# Maximum fraction of session slots that may be filled by companion templates.
COMPANION_FRACTION: float = 0.40

# Pool expansion triggers when native pool < count // this value.
COMPANION_TRIGGER_DIVISOR: int = 2


COMPANION_IDS: dict[tuple[int, str], list[str]] = {

    # ── Year 9 Number (4 native templates — most critical bottleneck) ──────────
    # Native: T-9N-01 (rational/irrational, curated), T-9N-02 (scientific notation),
    #         T-9N-03 (interest), T-9N-04 (proportion)
    # Companions: Year 8 Number — directly prerequisite content
    (9, "Number"): [
        "T-8N-01",   # integer powers and roots — supports sci-notation fluency
        "T-8N-02",   # index laws — prerequisite for T-9N-02 scientific notation
        "T-8N-05",   # percentage increase/decrease — bridges to T-9N-03 interest
        "T-8N-04",   # integer and rational number operations — foundational
        "T-8N-03",   # HCF and LCM — number theory consolidation
    ],

    # ── Year 9 Probability (2 native templates) ────────────────────────────────
    # Native: T-9P-01, T-9P-03
    # Companions: Year 8 Probability (same curriculum thread) + Year 7 review
    (9, "Probability"): [
        "T-8P-01",   # theoretical probability (Year 8)
        "T-8P-02",   # experimental probability (Year 8)
        "T-8P-03",   # two-step probability experiments (Year 8)
        "T-7P-01",   # listing sample spaces (Year 7 review)
        "T-7P-03",   # complementary events (Year 7 review)
    ],

    # ── Year 9 Space (2 native templates) ─────────────────────────────────────
    # Native: T-9SP-01, T-9SP-02
    # Companions: Year 8 transformations + Year 7 angle relationships
    (9, "Space"): [
        "T-8SP-03",  # transformations (parametric) — closely related to T-9SP-02
        "T-7SP-02",  # angle relationships (parametric) — foundational geometry
    ],

    # ── Year 9 Statistics (1 native template) ─────────────────────────────────
    # Native: T-9ST-03 only (Year 9 Statistics is restricted in session API)
    # Companions: Year 8 and Year 7 Statistics for maximal pool expansion
    (9, "Statistics"): [
        "T-8ST-01",  # frequency tables and mean/median/mode (Year 8)
        "T-7ST-01",  # mean, median, mode from raw data (Year 7 review)
    ],

    # ── Year 8 Algebra (3 native templates) ───────────────────────────────────
    # Native: T-8A-01, T-8A-02, T-8A-03
    # Companions: Year 7 Algebra revision
    (8, "Algebra"): [
        "T-7A-01",   # evaluating expressions (Year 7)
        "T-7A-02",   # solving one-step equations (Year 7)
        "T-7A-03",   # patterns and sequences (Year 7)
    ],

    # ── Year 8 Probability (3 native templates) ───────────────────────────────
    # Native: T-8P-01, T-8P-02, T-8P-03
    # Companions: Year 7 Probability review
    (8, "Probability"): [
        "T-7P-01",   # listing sample spaces (Year 7)
        "T-7P-03",   # complementary events (Year 7)
    ],

    # ── Year 8 Space (3 native templates, 2 curated_bank) ─────────────────────
    # Native: T-8SP-01 (curated), T-8SP-02 (curated), T-8SP-03 (parametric)
    # Companions: Year 7 angles + Year 9 congruence/similarity (mild extension)
    (8, "Space"): [
        "T-7SP-02",  # angle relationships (Year 7 parametric)
        "T-9SP-01",  # congruence and similarity (Year 9 — mild extension)
    ],

    # ── Year 8 Statistics (2 native templates) ────────────────────────────────
    # Native: T-8ST-01 (parametric), T-8ST-03 (curated_bank)
    # Companions: Year 7 review + Year 9 mild extension
    (8, "Statistics"): [
        "T-7ST-01",  # mean/median/mode from raw data (Year 7 review)
        "T-9ST-03",  # box plots and spread (Year 9 extension)
    ],

    # ── Year 7 Algebra (4 native templates) ───────────────────────────────────
    # Native: T-7A-01, T-7A-02, T-7A-03, T-7A-04
    # 4 templates triggers for count=10 (4 < 5). Companions: Year 8 extension.
    (7, "Algebra"): [
        "T-8A-01",   # expanding and simplifying expressions (Year 8)
        "T-8A-03",   # substitution into formulas (Year 8)
    ],

    # ── Year 7 Probability (3 native templates) ───────────────────────────────
    # Native: T-7P-01, T-7P-02, T-7P-03
    # Companions: Year 8 gentle extension
    (7, "Probability"): [
        "T-8P-01",   # theoretical probability (Year 8 extension)
        "T-8P-02",   # experimental probability (Year 8 extension)
    ],

    # ── Year 7 Space (3 native templates) ─────────────────────────────────────
    # Native: T-7SP-01 (curated), T-7SP-02 (parametric), T-7SP-03 (curated)
    # Companions: Year 8 transformations
    (7, "Space"): [
        "T-8SP-03",  # transformations (Year 8 parametric)
    ],

    # ── Year 7 Statistics (2 native templates) ────────────────────────────────
    # Native: T-7ST-01 (parametric), T-7ST-03 (curated_bank)
    # Companions: Year 8 frequency tables + Year 9 box plots (extension)
    (7, "Statistics"): [
        "T-8ST-01",  # frequency tables and averages (Year 8)
        "T-9ST-03",  # box plots (Year 9 mild extension)
    ],
}


def get_companion_ids(year_level: int, strand: str) -> list[str]:
    """Return companion template IDs for (year_level, strand), or [] if none defined."""
    return COMPANION_IDS.get((year_level, strand), [])


def should_expand(native_count: int, count: int) -> bool:
    """
    Return True if the native pool is thin enough to warrant companion expansion.

    Triggers when native_count < count // COMPANION_TRIGGER_DIVISOR.
    For count=10: triggers when native_count < 5 (i.e., 4 or fewer native templates).
    For count=5:  triggers when native_count < 2 (i.e., 1 native template only).
    """
    return native_count < (count // COMPANION_TRIGGER_DIVISOR)


def max_companions(count: int) -> int:
    """
    Maximum number of companion template slots to add to the pool.

    Capped at COMPANION_FRACTION * count (rounded down, minimum 1), so on-year
    content remains the dominant portion of each session.

    count=10 → max 4 companions (40%)
    count=5  → max 2 companions (40%)
    """
    return max(1, int(count * COMPANION_FRACTION))
