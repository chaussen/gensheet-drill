"""
Multi-select template data — curated question banks and registry constants.
Extracted from question_service.py to separate configuration from logic.
"""

# T-7N-02 is parametric; multi_select question is built from its `n` param.
MULTI_SELECT_PARAMETRIC: set[str] = {"T-7N-02"}

# Curated banks for the 4 curated_bank multi_select templates.
# Each item has 5 pre-authored options, with correct_indices for the multi_select answer.
MULTI_SELECT_BANKS: dict[str, dict] = {
    "T-7SP-01": {
        "vc_code": "VC2M7SP01",
        "year": 7,
        "strand": "Space",
        "topic": "Properties of 2D shapes",
        "items": [
            {
                "question_text": "Which properties does a rhombus have? Select all that apply.",
                "options": [
                    "All sides are equal",
                    "All angles are 90\u00b0",
                    "Opposite sides are parallel",
                    "Diagonals are equal in length",
                    "Diagonals are perpendicular",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A rhombus has all sides equal, opposite sides parallel, and perpendicular diagonals. Its angles are not necessarily 90\u00b0 and its diagonals are not necessarily equal.",
            },
            {
                "question_text": "Which properties does a rectangle have? Select all that apply.",
                "options": [
                    "All angles are 90\u00b0",
                    "All sides are equal",
                    "Opposite sides are equal",
                    "Diagonals are perpendicular",
                    "Diagonals are equal in length",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A rectangle has all right angles, equal opposite sides, and equal diagonals. Its sides are not all equal (unless it is a square) and its diagonals are not perpendicular.",
            },
            {
                "question_text": "Which properties does a kite have? Select all that apply.",
                "options": [
                    "Two pairs of consecutive equal sides",
                    "All sides are equal",
                    "Diagonals are perpendicular",
                    "Opposite sides are parallel",
                    "One diagonal bisects the other",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A kite has two pairs of consecutive equal sides, perpendicular diagonals, and one diagonal bisects the other. It does not have all sides equal or parallel opposite sides.",
            },
        ],
    },
    "T-8SP-02": {
        "vc_code": "VC2M8SP02",
        "year": 8,
        "strand": "Space",
        "topic": "Properties of quadrilaterals",
        "items": [
            {
                "question_text": "Select all true statements about a parallelogram.",
                "options": [
                    "Opposite sides are parallel",
                    "All angles are 90\u00b0",
                    "Opposite angles are equal",
                    "Diagonals are equal in length",
                    "Diagonals bisect each other",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A parallelogram has parallel opposite sides, equal opposite angles, and diagonals that bisect each other. It does not require right angles or equal-length diagonals.",
            },
            {
                "question_text": "Select all true statements about a square.",
                "options": [
                    "All sides are equal",
                    "Diagonals bisect each other at right angles",
                    "Diagonals are unequal in length",
                    "All angles are 90\u00b0",
                    "Opposite sides are not parallel",
                ],
                "correct_indices": [0, 1, 3],
                "explanation": "A square has all sides equal, all angles 90\u00b0, and diagonals that bisect each other at right angles. Its diagonals are equal (not unequal) and all sides are parallel.",
            },
            {
                "question_text": "Select all true statements about a trapezium.",
                "options": [
                    "Exactly one pair of parallel sides",
                    "Both pairs of opposite sides are parallel",
                    "Co-interior angles between parallel sides are supplementary",
                    "Diagonals always bisect each other",
                    "May have two equal non-parallel sides",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A trapezium has exactly one pair of parallel sides. Co-interior angles between the parallel sides sum to 180\u00b0. An isosceles trapezium has two equal non-parallel sides. Diagonals do not generally bisect each other.",
            },
        ],
    },
    "T-9N-01": {
        "vc_code": "VC2M9N01",
        "year": 9,
        "strand": "Number",
        "topic": "Rational and irrational numbers",
        "items": [
            {
                "question_text": "Select all irrational numbers.",
                "options": ["\u221a2", "\u221a9", "\u03c0", "0.4", "3/7"],
                "correct_indices": [0, 2],
                "explanation": "\u221a2 and \u03c0 are irrational \u2014 they cannot be expressed as p/q for integers p, q. \u221a9 = 3, 0.4 = 2/5, and 3/7 are all rational.",
            },
            {
                "question_text": "Select all irrational numbers.",
                "options": ["0.333\u2026", "\u221a5", "5/8", "\u221a7", "1.25"],
                "correct_indices": [1, 3],
                "explanation": "\u221a5 and \u221a7 are irrational. 0.333\u2026 = 1/3, 5/8, and 1.25 = 5/4 are all rational.",
            },
            {
                "question_text": "Select all irrational numbers.",
                "options": ["\u221a3", "\u221a4", "22/7", "\u221a6", "0.1"],
                "correct_indices": [0, 3],
                "explanation": "\u221a3 and \u221a6 are irrational. \u221a4 = 2, 22/7 is a rational approximation of \u03c0, and 0.1 = 1/10 are rational.",
            },
        ],
    },
    "T-9A-05": {
        "vc_code": "VC2M9A05",
        "year": 9,
        "strand": "Algebra",
        "topic": "Identify quadratic equations",
        "items": [
            {
                "question_text": "Select all quadratic equations.",
                "options": ["x\u00b2 + 3x \u2212 4 = 0", "2x + 5 = 0", "x\u00b2 = 9", "x\u00b3 \u2212 1 = 0", "y = x + 1"],
                "correct_indices": [0, 2],
                "explanation": "x\u00b2 + 3x \u2212 4 = 0 and x\u00b2 = 9 are quadratic (highest degree 2). 2x + 5 = 0 and y = x + 1 are linear; x\u00b3 \u2212 1 = 0 is cubic.",
            },
            {
                "question_text": "Which of the following are quadratic equations?",
                "options": ["y = x\u00b2", "y = 2x + 1", "3x\u00b2 \u2212 2x + 1 = 0", "y = 1/x", "x\u00b3 = 8"],
                "correct_indices": [0, 2],
                "explanation": "y = x\u00b2 and 3x\u00b2 \u2212 2x + 1 = 0 are quadratic. y = 2x + 1 is linear, y = 1/x is a hyperbola, and x\u00b3 = 8 is cubic.",
            },
            {
                "question_text": "Identify all quadratic equations from the list.",
                "options": ["x\u00b2 \u2212 5x + 6 = 0", "x = 4", "2x\u00b2 + x = 0", "y = 3/x", "4x \u2212 1 = 0"],
                "correct_indices": [0, 2],
                "explanation": "x\u00b2 \u2212 5x + 6 = 0 and 2x\u00b2 + x = 0 are quadratic. x = 4 is a constant equation, y = 3/x is a hyperbola, and 4x \u2212 1 = 0 is linear.",
            },
        ],
    },
}

MULTI_SELECT_TEMPLATE_IDS: set[str] = set(MULTI_SELECT_BANKS) | MULTI_SELECT_PARAMETRIC

T7N02_PRIME_POOL: list[int] = [2, 3, 5, 7, 11, 13, 17, 19]
