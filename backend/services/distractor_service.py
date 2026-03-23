"""
distractor_service.py
=====================
Thin wrapper around VerificationEngine's distractor generation.
Handles curated_bank templates and cleans up poor-quality fallback distractors.
"""
import re
import logging
from fractions import Fraction

from services.verification import VerificationEngine

logger = logging.getLogger(__name__)
_engine = VerificationEngine()


def _is_garbage_distractor(d: str) -> bool:
    """Return True if d is a known garbage fallback pattern from verification.py or padding."""
    return (
        "_wrong_" in d                          # off-by-one fallback: {answer}_wrong_N
        or d.endswith("_neg")                   # sign_flip fallback for non-numeric
        or d.endswith("_a") or d.endswith("_b") or d.endswith("_c")  # sign_flip fallback
    )


def _improve_string_distractors(correct_str: str, distractors: list) -> list:
    """
    Replace garbage distractors (_wrong_N, _neg, _a, _b, _c suffixes) produced by
    fallback paths in verification.py when the answer is non-numeric (e.g. Fraction).
    """
    if not any(_is_garbage_distractor(d) for d in distractors):
        return distractors

    alternatives = []

    # Case 1: fraction string (e.g. "3/2", "1/4")
    try:
        val = Fraction(correct_str)
        for delta in [Fraction(1), Fraction(-1), Fraction(1, 2), Fraction(-1, 2), Fraction(2)]:
            alt = str(val + delta)
            if alt != correct_str and alt not in alternatives:
                alternatives.append(alt)
    except (ValueError, ZeroDivisionError):
        pass

    # Case 2: polynomial string from sympy (e.g. "6*x + 10", "2*x**2 - 3*x")
    if not alternatives and ("*x" in correct_str or "x**" in correct_str):
        # Vary the constant term
        match = re.search(r'([+-]?\s*\d+)\s*$', correct_str)
        if match:
            const_str = match.group(1).replace(" ", "")
            try:
                const = int(const_str)
                prefix = correct_str[:match.start()].rstrip()
                for offset in [5, -5, 10, -10]:
                    new_c = const + offset
                    sign = " + " if new_c >= 0 else " - "
                    alt = f"{prefix}{sign}{abs(new_c)}"
                    if alt != correct_str and alt not in alternatives:
                        alternatives.append(alt)
            except ValueError:
                pass

    # Fallback: append a numeric suffix so at least they're distinct strings
    result = []
    alt_idx = 0
    for d in distractors:
        if _is_garbage_distractor(d):
            if alt_idx < len(alternatives):
                result.append(alternatives[alt_idx])
                alt_idx += 1
            else:
                result.append(f"{correct_str}?")  # visibly wrong but distinct
        else:
            result.append(d)

    return result


def generate_distractors(template_id: str, correct_answer, params: dict) -> list[str]:
    """
    Generate exactly 3 plausible wrong answers for the given template/answer.
    Returns a list of 3 distinct strings, none equal to str(correct_answer).
    """
    # Curated-bank templates: distractor data lives in the bank, not the engine.
    # TODO: implement curated bank data loading when bank files are available.
    if template_id in _engine.curated_template_ids:
        logger.warning(
            "Template %s is curated_bank — falling back to numeric distractors", template_id
        )
        distractors = _engine._distractors_off_by_one(correct_answer)
    else:
        try:
            distractors = _engine.generate_distractors(template_id, correct_answer, params)
        except Exception as e:
            logger.warning("Distractor generation failed for %s: %s", template_id, e)
            distractors = _engine._distractors_off_by_one(correct_answer)

    distractors = [str(d) for d in distractors]
    correct_str = str(correct_answer) if not isinstance(correct_answer, tuple) else \
        f"({correct_answer[0]}, {correct_answer[1]})"

    # Improve string distractors that fell back to _wrong_N pattern
    distractors = _improve_string_distractors(correct_str, distractors)

    # Deduplicate and remove any that equal the correct answer
    seen = {correct_str}
    clean = []
    for d in distractors:
        if d not in seen:
            seen.add(d)
            clean.append(d)

    # Pad to 3 if needed
    i = 0
    while len(clean) < 3:
        candidate = f"{correct_str}_{i}"
        if candidate not in seen:
            clean.append(candidate)
            seen.add(candidate)
        i += 1

    return clean[:3]
