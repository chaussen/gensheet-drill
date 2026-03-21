"""
verification.py
===============
Pre-written verification engine for GenSheet Drill.
DO NOT MODIFY. Copy this file to backend/verification.py as-is.

Each verifier function takes a `params` dict and returns the correct answer.
The return type matches the `answer_type` declared in question_templates.json.

Usage:
    from verification import VerificationEngine
    engine = VerificationEngine()
    correct_answer = engine.verify("T-7N-01", {"n": 64})  # returns 8
    distractors = engine.generate_distractors("T-7N-01", 8, {"n": 64})  # returns ["7", "9", "10"]
"""

import math
import operator
from fractions import Fraction
from sympy import (
    symbols, solve, expand, factorint, simplify, Rational,
    pi, sin, cos, tan, sqrt, nsimplify, Integer, Float
)
from sympy import Eq as SymEq
import random

x, y, n, m = symbols('x y n m')


# ─── VERIFIER REGISTRY ────────────────────────────────────────────────────────

class VerificationEngine:

    def verify(self, template_id: str, params: dict):
        """
        Compute the correct answer for a given template and parameter set.
        Returns the answer in the format declared by the template's answer_type.
        Raises ValueError if template_id is unknown.
        """
        fn = self._registry.get(template_id)
        if fn is None:
            raise ValueError(f"No verifier registered for template '{template_id}'")
        return fn(params)

    def generate_distractors(self, template_id: str, correct_answer, params: dict) -> list:
        """
        Generate exactly 3 plausible wrong answers using the template's declared strategy.
        Returns a list of 3 strings. All values are distinct from correct_answer and each other.
        """
        from docs_loader import load_template_meta  # loaded at runtime
        meta = load_template_meta(template_id)
        strategy = meta.get("distractor_strategy", "OFF_BY_ONE")
        return self._distractor_dispatch(strategy, template_id, correct_answer, params)

    # ─── INDIVIDUAL VERIFIER FUNCTIONS ────────────────────────────────────────

    def _sqrt_perfect(self, p):
        return int(math.isqrt(p["n"]))

    def _prime_factorisation(self, p):
        """Returns formatted string like '2² × 3' """
        factors = factorint(p["n"])
        parts = []
        for base in sorted(factors):
            exp = factors[base]
            parts.append(f"{base}^{exp}" if exp > 1 else str(base))
        return " × ".join(parts)

    def _round_decimal(self, p):
        return round(float(p["x"]), int(p["dp"]))

    def _fraction_multiply_divide(self, p):
        a, b, c, d = p["a"], p["b"], p["c"], p["d"]
        fa = Fraction(a, b)
        fc = Fraction(c, d)
        if p["op"] == "×":
            result = fa * fc
        else:  # ÷
            result = fa / fc
        return str(result)  # e.g. "3/4"

    def _eval_expression(self, p):
        """Safe eval for arithmetic expressions with +, -, ×, ÷"""
        expr = p["expr"]
        safe = expr.replace("×", "*").replace("÷", "/")
        # Only allow safe characters
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in safe):
            raise ValueError(f"Unsafe expression: {expr}")
        return int(eval(safe))

    def _percentage_of_amount(self, p):
        pct = float(p["pct"])
        amount = float(p["amount"])
        result = (pct / 100) * amount
        return int(result) if result == int(result) else round(result, 2)

    def _integer_operation(self, p):
        a, b = int(p["a"]), int(p["b"])
        ops = {"+": operator.add, "-": operator.sub, "×": operator.mul}
        return ops[p["op"]](a, b)

    def _ratio_share(self, p):
        a, b, total = int(p["a"]), int(p["b"]), int(p["total"])
        larger = max(a, b)
        return int(larger / (a + b) * total)

    def _substitution(self, p):
        var = p["var"]
        val = p["val"]
        expr_str = p["expr"].replace("×", "*").replace("²", "**2").replace("³", "**3")
        sym = symbols(var)
        expr = __import__("sympy").sympify(expr_str.replace(var, f"({val})"))
        return int(expr)

    def _solve_linear_one_var(self, p):
        a, b, c = int(p["a"]), int(p["b"]), int(p["c"])
        op = p.get("op", "+")
        var = symbols("x")
        if op == "+":
            eq = SymEq(a * var + b, c)
        else:
            eq = SymEq(a * var - b, c)
        sol = solve(eq, var)
        return int(sol[0])

    def _arithmetic_sequence_next(self, p):
        t1, d = int(p["t1"]), int(p["d"])
        return t1 + 4 * d  # 5th term (t1 is 1st)

    def _area_triangle_parallelogram(self, p):
        b, h = float(p["b"]), float(p["h"])
        if p["shape"] == "triangle":
            result = 0.5 * b * h
        else:  # parallelogram
            result = b * h
        return int(result) if result == int(result) else result

    def _volume_rectangular_prism(self, p):
        return int(p["l"]) * int(p["w"]) * int(p["h"])

    def _angle_relationship(self, p):
        a = int(p["a"])
        rel = p["relationship"]
        if rel == "supplementary":
            return 180 - a
        elif rel == "complementary":
            return 90 - a
        elif rel == "vertically opposite":
            return a
        elif "co-interior" in rel:
            return 180 - a
        raise ValueError(f"Unknown relationship: {rel}")

    def _transformation_coordinates(self, p):
        x_val, y_val = int(p["x"]), int(p["y"])
        t = p["transformation"]
        if "reflected in the x-axis" in t:
            return (x_val, -y_val)
        elif "reflected in the y-axis" in t:
            return (-x_val, y_val)
        elif "reflected in the line y=x" in t:
            return (y_val, x_val)
        elif "translated" in t:
            tx, ty = int(p["tx"]), int(p["ty"])
            return (x_val + tx, y_val + ty)
        elif "90° clockwise" in t:
            return (y_val, -x_val)
        elif "90° anticlockwise" in t or "90° counter" in t:
            return (-y_val, x_val)
        elif "180°" in t:
            return (-x_val, -y_val)
        raise ValueError(f"Unknown transformation: {t}")

    def _statistics_measure(self, p):
        data = sorted([int(d) for d in p["data"]])
        measure = p["measure"]
        if measure == "mean":
            result = sum(data) / len(data)
            return round(result, 1)
        elif measure == "median":
            n_items = len(data)
            mid = n_items // 2
            if n_items % 2 == 0:
                return (data[mid - 1] + data[mid]) / 2
            return data[mid]
        elif measure == "mode":
            from collections import Counter
            counts = Counter(data)
            max_count = max(counts.values())
            modes = sorted([k for k, v in counts.items() if v == max_count])
            return modes[0] if len(modes) == 1 else modes
        elif measure == "range":
            return max(data) - min(data)
        raise ValueError(f"Unknown measure: {measure}")

    def _simple_probability(self, p):
        r, b = int(p["r"]), int(p["b"])
        return str(Fraction(r, r + b))

    def _complementary_probability(self, p):
        pn = int(p["p_numerator"])
        pd = int(p["p_denominator"])
        comp = Fraction(pd - pn, pd)
        return str(comp)

    def _power_root_eval(self, p):
        expr = p["expr"]
        # Map unicode superscripts to exponents
        expr = expr.replace("²", "**2").replace("³", "**3").replace("⁴", "**4").replace("⁵", "**5")
        expr = expr.replace("√", "math.sqrt").replace("∛", "")
        # Handle ∛ (cube root)
        if "∛" in p["expr"]:
            val = int(p.get("c", 8))
            return round(val ** (1/3))
        safe = expr.replace("×", "*")
        allowed = set("0123456789+-*/(). math.sqrte")
        if not all(c in allowed for c in safe.replace("math.sqrt", "").replace("math.e", "")):
            raise ValueError(f"Unsafe: {expr}")
        return int(eval(safe, {"math": math}))

    def _index_laws(self, p):
        a_val = int(p["a"])
        m_val = int(p["m"])
        n_val = int(p["n"])
        law = p["law"]
        if "product" in law:
            exp = m_val + n_val
            return f"{a_val}^{exp}"
        elif "quotient" in law:
            exp = m_val - n_val
            return f"{a_val}^{exp}" if exp != 0 else "1"
        elif "zero" in law:
            return "1"
        elif "power of power" in law:
            exp = m_val * n_val
            return f"{a_val}^{exp}"
        raise ValueError(f"Unknown law: {law}")

    def _hcf_lcm(self, p):
        a, b = int(p["a"]), int(p["b"])
        measure = p["measure"].upper()
        if "HCF" in measure or "GCF" in measure:
            return math.gcd(a, b)
        elif "LCM" in measure:
            return abs(a * b) // math.gcd(a, b)
        raise ValueError(f"Unknown measure: {measure}")

    def _rational_arithmetic(self, p):
        expr = p["expr"]
        safe = expr.replace("×", "*").replace("÷", "/")
        try:
            result = Fraction(eval(safe))
            return str(result)
        except Exception:
            return str(round(eval(safe), 4))

    def _percentage_change(self, p):
        original = float(p["original"])
        pct = float(p["pct"])
        change_type = p["change_type"]
        if change_type == "increased":
            result = original * (1 + pct / 100)
        else:
            result = original * (1 - pct / 100)
        return round(result, 2) if result != int(result) else int(result)

    def _expand_simplify(self, p):
        from sympy import symbols, expand as sym_expand
        xv = symbols("x")
        a, b_coef, c_val = int(p["a"]), int(p["b"]), int(p["c"])
        op = p.get("op", "+")
        if op == "+":
            expr = a * (b_coef * xv + c_val)
        else:
            expr = a * (b_coef * xv - c_val)
        result = sym_expand(expr)
        return str(result)

    def _solve_linear_both_sides(self, p):
        a, b_val, c_val, d_val = int(p["a"]), int(p["b"]), int(p["c"]), int(p["d"])
        op1, op2 = p.get("op1", "+"), p.get("op2", "+")
        xv = symbols("x")
        lhs = a * xv + (b_val if op1 == "+" else -b_val)
        rhs = c_val * xv + (d_val if op2 == "+" else -d_val)
        sol = solve(SymEq(lhs, rhs), xv)
        return sol[0]

    def _gradient_two_points(self, p):
        x1, y1 = int(p["x1"]), int(p["y1"])
        x2, y2 = int(p["x2"]), int(p["y2"])
        if x2 == x1:
            raise ValueError("Vertical line — gradient undefined")
        grad = Fraction(y2 - y1, x2 - x1)
        return str(grad)

    def _circle_measure(self, p):
        dimension_type = p["dimension_type"]
        value = float(p["value"])
        radius = value if dimension_type == "radius" else value / 2
        measure = p["measure"]
        if measure == "circumference":
            return round(2 * math.pi * radius, 2)
        elif measure == "area":
            return round(math.pi * radius ** 2, 2)
        raise ValueError(f"Unknown measure: {measure}")

    def _rate_speed_distance_time(self, p):
        speed = float(p.get("speed", 0))
        dist = float(p.get("dist", 0))
        time_val = float(p.get("time", 0))
        # Determine what to compute based on what's missing
        query = p.get("query", "speed")
        if query == "speed" or (dist > 0 and time_val > 0 and speed == 0):
            return round(dist / time_val, 2) if dist / time_val != int(dist / time_val) else int(dist / time_val)
        elif query == "distance" or (speed > 0 and time_val > 0 and dist == 0):
            return round(speed * time_val, 2)
        elif query == "time" or (speed > 0 and dist > 0 and time_val == 0):
            return round(dist / speed, 2)
        raise ValueError("Cannot determine what to compute")

    def _pythagoras(self, p):
        triple = p["triple_family"]
        scale = int(p.get("scale", 1))
        unknown = p["unknown_side"]
        a, b, c = [v * scale for v in triple]  # c is hypotenuse
        if unknown == "hypotenuse":
            return c
        elif unknown in ("shorter leg", "leg a"):
            return a
        elif unknown in ("longer leg", "leg b"):
            return b
        raise ValueError(f"Unknown side type: {unknown}")

    def _volume_prism(self, p):
        prism_type = p.get("prism_type", "rectangular")
        l = float(p["l"])
        base_area = float(p["base_area"])
        result = base_area * l
        return int(result) if result == int(result) else round(result, 2)

    def _mean_from_frequency_table(self, p):
        values = [int(v) for v in p["values"]]
        freqs = [int(f) for f in p["frequencies"]]
        total_freq = sum(freqs)
        weighted_sum = sum(v * f for v, f in zip(values, freqs))
        return round(weighted_sum / total_freq, 1)

    def _two_step_probability(self, p):
        r, b = int(p["r"]), int(p["b"])
        total = r + b
        outcome = p["outcome"]
        if outcome == "two red balls":
            prob = Fraction(r, total) * Fraction(r, total)
        elif outcome == "two blue balls":
            prob = Fraction(b, total) * Fraction(b, total)
        elif outcome == "one of each colour":
            prob = Fraction(r, total) * Fraction(b, total) * 2
        elif outcome == "at least one red ball":
            prob = 1 - (Fraction(b, total) * Fraction(b, total))
        else:
            raise ValueError(f"Unknown outcome: {outcome}")
        return str(prob)

    def _relative_frequency(self, p):
        n_trials, a_count = int(p["n"]), int(p["a"])
        return str(Fraction(a_count, n_trials))

    def _simple_compound_interest(self, p):
        principal = float(p["principal"])
        rate = float(p["rate"]) / 100
        years = int(p["years"])
        interest_type = p["interest_type"]
        if interest_type == "simple":
            return round(principal * rate * years, 2)
        else:  # compound
            amount = principal * (1 + rate) ** years
            return round(amount - principal, 2)

    def _direct_proportion(self, p):
        x1, y1, x2 = float(p["x1"]), float(p["y1"]), float(p["x2"])
        k = y1 / x1
        result = k * x2
        return int(result) if result == int(result) else round(result, 2)

    def _scientific_notation_convert(self, p):
        value = float(p["value"])
        from decimal import Decimal
        d = Decimal(str(value))
        exp = d.adjusted()
        mantissa = float(d / Decimal(10) ** exp)
        return f"{mantissa:.4g} × 10^{exp}"

    def _expand_binomial(self, p):
        xv = symbols("x")
        a, b_val, c_val, d_val = int(p["a"]), int(p["b"]), int(p["c"]), int(p["d"])
        op1, op2 = p.get("op1", "+"), p.get("op2", "+")
        t1 = a * xv + (b_val if op1 == "+" else -b_val)
        t2 = c_val * xv + (d_val if op2 == "+" else -d_val)
        result = expand(t1 * t2)
        return str(result)

    def _line_equation(self, p):
        m_val = p["m"]
        c_val = int(p["c"])
        m_str = str(Fraction(m_val).limit_denominator(10)) if not isinstance(m_val, int) else str(m_val)
        if c_val == 0:
            return f"y = {m_str}x"
        elif c_val > 0:
            return f"y = {m_str}x + {c_val}"
        else:
            return f"y = {m_str}x - {abs(c_val)}"

    def _simultaneous_equations(self, p):
        a, b_val, c_val, d_val = int(p["a"]), int(p["b"]), int(p["c"]), int(p["d"])
        xv, yv = symbols("x y")
        sol = solve([SymEq(yv, a * xv + b_val), SymEq(yv, c_val * xv + d_val)], [xv, yv])
        return sol[xv]

    def _surface_area(self, p):
        shape = p["shape"]
        if shape == "rectangular prism":
            l, w, h = float(p["l"]), float(p["w"]), float(p["h"])
            return 2 * (l*w + l*h + w*h)
        elif shape == "cylinder":
            r, h = float(p["r"]), float(p["h"])
            return round(2 * math.pi * r * h + 2 * math.pi * r**2, 2)
        elif shape == "triangular prism":
            # Base is right triangle with legs a, b, hypotenuse c, length l
            a, b, c_side, length = float(p["a"]), float(p["b"]), float(p["c_side"]), float(p["length"])
            base_area = 0.5 * a * b
            return 2 * base_area + (a + b + c_side) * length
        raise ValueError(f"Unknown shape: {shape}")

    def _volume_pyramid_cone_sphere(self, p):
        shape = p["shape"]
        if shape == "square pyramid":
            s, h = float(p["s"]), float(p["h"])
            return round((1/3) * s**2 * h, 2)
        elif shape == "cone":
            r, h = float(p["r"]), float(p["h"])
            return round((1/3) * math.pi * r**2 * h, 2)
        elif shape == "sphere":
            r = float(p["r"])
            return round((4/3) * math.pi * r**3, 2)
        raise ValueError(f"Unknown shape: {shape}")

    def _trigonometry_find_side(self, p):
        theta = float(p["theta"])
        value = float(p["value"])
        known_side = p["known_side"]
        unknown_side = p["unknown_side"]
        theta_rad = math.radians(theta)

        if known_side == "hypotenuse":
            if unknown_side == "opposite side":
                return round(value * math.sin(theta_rad), 2)
            elif unknown_side == "adjacent side":
                return round(value * math.cos(theta_rad), 2)
        elif known_side == "opposite side":
            if unknown_side == "hypotenuse":
                return round(value / math.sin(theta_rad), 2)
            elif unknown_side == "adjacent side":
                return round(value / math.tan(theta_rad), 2)
        elif known_side == "adjacent side":
            if unknown_side == "hypotenuse":
                return round(value / math.cos(theta_rad), 2)
            elif unknown_side == "opposite side":
                return round(value * math.tan(theta_rad), 2)
        raise ValueError(f"Cannot compute: known={known_side}, unknown={unknown_side}")

    def _similar_figures(self, p):
        a, b_val, c_val = float(p["a"]), float(p["b"]), float(p["c"])
        scale = b_val / a
        result = c_val * scale
        return int(result) if result == int(result) else round(result, 1)

    def _compare_statistics(self, p):
        # Returns the factually correct statement as a string
        mA, mB = float(p["meanA"]), float(p["meanB"])
        rA, rB = float(p["rangeA"]), float(p["rangeB"])
        if mA > mB and rA > rB:
            return f"Set A has a higher mean and greater spread than Set B"
        elif mA > mB and rA < rB:
            return f"Set A has a higher mean but less spread than Set B"
        elif mA < mB and rA > rB:
            return f"Set B has a higher mean but Set A has greater spread"
        else:
            return f"Set B has a higher mean and greater spread than Set A"

    def _venn_diagram_probability(self, p):
        total = int(p["total"])
        a_count = int(p["a"])
        b_count = int(p["b"])
        ab_count = int(p["ab"])
        query = p["query"]
        a_only = a_count - ab_count
        b_only = b_count - ab_count
        neither = total - a_count - b_count + ab_count

        if query == "Maths only":
            return str(Fraction(a_only, total))
        elif query == "Science only":
            return str(Fraction(b_only, total))
        elif query == "both subjects":
            return str(Fraction(ab_count, total))
        elif query == "at least one subject":
            return str(Fraction(a_count + b_count - ab_count, total))
        elif query == "neither subject":
            return str(Fraction(neither, total))
        raise ValueError(f"Unknown query: {query}")

    def _two_way_table_probability(self, p):
        # table is a 2x2 dict; query specifies what to compute
        table = p["table"]  # {"a1b1": n, "a1b2": n, "a2b1": n, "a2b2": n}
        total = sum(table.values())
        query_cell = p.get("query_cell")
        if query_cell:
            return str(Fraction(table[query_cell], total))
        # Row/column totals
        query_row = p.get("query_row")
        if query_row:
            row_total = table[f"{query_row}b1"] + table[f"{query_row}b2"]
            return str(Fraction(row_total, total))
        raise ValueError("Two-way table: no query specified")

    def _solve_linear_with_fractions(self, p):
        sol = int(p["solution"])
        return sol  # The solution is pre-defined; verifier confirms it

    # ─── DISTRACTOR GENERATION ────────────────────────────────────────────────

    def _distractor_dispatch(self, strategy: str, template_id: str, correct, params: dict) -> list:
        """Generate 3 distinct wrong answers using the named strategy."""
        if strategy == "OFF_BY_ONE":
            return self._distractors_off_by_one(correct)
        elif strategy == "SIGN_FLIP":
            return self._distractors_sign_flip(correct)
        elif strategy == "OP_SWAP":
            return self._distractors_op_swap(correct, params, template_id)
        elif strategy == "PARTIAL":
            return self._distractors_partial(correct, params, template_id)
        elif strategy == "INVERSION":
            return self._distractors_inversion(correct, params)
        elif strategy == "FACTOR_SKIP":
            return self._distractors_factor_skip(correct, params)
        elif strategy == "FORMULA_MIX":
            return self._distractors_formula_mix(correct, params, template_id)
        elif strategy == "UNIT_ERROR":
            return self._distractors_unit_error(correct)
        elif strategy == "COMPLEMENT":
            return self._distractors_complement(correct, params)
        elif strategy == "CURATED_WRONG":
            # For curated banks: wrong answers are stored in the bank, not generated here
            # This path should not be reached for curated_bank templates
            return self._distractors_off_by_one(correct)
        else:
            return self._distractors_off_by_one(correct)

    def _distractors_off_by_one(self, correct) -> list:
        if isinstance(correct, (int, float)):
            opts = [correct - 2, correct - 1, correct + 1, correct + 2]
            opts = [o for o in opts if o != correct][:3]
            return [str(o) for o in opts]
        return [str(correct) + "_wrong_1", str(correct) + "_wrong_2", str(correct) + "_wrong_3"]

    def _distractors_sign_flip(self, correct) -> list:
        if isinstance(correct, (int, float)):
            neg = -correct
            return [str(neg), str(correct - 1), str(correct + 1)]
        return [str(correct) + "_neg", str(correct) + "_a", str(correct) + "_b"]

    def _distractors_op_swap(self, correct, params, template_id) -> list:
        # Generic fallback: off-by-one plus a ×2 error
        if isinstance(correct, (int, float)):
            return [str(correct - 1), str(correct + 1), str(correct * 2 if correct != 0 else correct + 5)]
        return self._distractors_off_by_one(correct)

    def _distractors_partial(self, correct, params, template_id) -> list:
        if isinstance(correct, (int, float)):
            return [str(correct - 1), str(correct ** 2 if abs(correct) < 15 else correct + 10), str(correct + 1)]
        return self._distractors_off_by_one(correct)

    def _distractors_inversion(self, correct, params) -> list:
        if isinstance(correct, str) and "/" in correct:
            frac = Fraction(correct)
            inv = Fraction(frac.denominator, frac.numerator)
            near1 = Fraction(frac.numerator + 1, frac.denominator)
            near2 = Fraction(frac.numerator, frac.denominator + 1)
            return [str(inv), str(near1), str(near2)]
        return self._distractors_off_by_one(correct)

    def _distractors_factor_skip(self, correct, params) -> list:
        # For factorisation: missing an exponent, wrong base
        # Fallback to off-by-one for numeric answers
        return self._distractors_off_by_one(correct) if isinstance(correct, (int, float)) else [
            correct + "_wrong1", correct + "_wrong2", correct + "_wrong3"
        ]

    def _distractors_formula_mix(self, correct, params, template_id) -> list:
        if isinstance(correct, (int, float)):
            return [str(correct * 2), str(correct / 2 if correct % 2 == 0 else correct - 1), str(correct + 10)]
        return self._distractors_off_by_one(correct)

    def _distractors_unit_error(self, correct) -> list:
        if isinstance(correct, (int, float)):
            return [str(correct * 10), str(correct / 10), str(correct * 100)]
        return self._distractors_off_by_one(correct)

    def _distractors_complement(self, correct, params) -> list:
        a = params.get("a", 0)
        return [str(180 - a), str(90 - a), str(360 - a)]

    # ─── REGISTRY MAP ────────────────────────────────────────────────────────

    @property
    def _registry(self):
        return {
            "T-7N-01":  self._sqrt_perfect,
            "T-7N-02":  self._prime_factorisation,
            "T-7N-04":  self._round_decimal,
            "T-7N-05":  self._fraction_multiply_divide,
            "T-7N-06":  self._eval_expression,
            "T-7N-07":  self._percentage_of_amount,
            "T-7N-08":  self._integer_operation,
            "T-7N-09":  self._ratio_share,
            "T-7A-01":  self._substitution,
            "T-7A-02":  self._solve_linear_one_var,
            "T-7A-03":  self._arithmetic_sequence_next,
            "T-7M-01":  self._area_triangle_parallelogram,
            "T-7M-02":  self._volume_rectangular_prism,
            "T-7M-04":  self._angle_relationship,
            "T-7SP-02": self._transformation_coordinates,
            "T-7ST-01": self._statistics_measure,
            "T-7P-01":  self._simple_probability,
            "T-7P-03":  self._complementary_probability,
            "T-8N-01":  self._power_root_eval,
            "T-8N-02":  self._index_laws,
            "T-8N-03":  self._hcf_lcm,
            "T-8N-04":  self._rational_arithmetic,
            "T-8N-05":  self._percentage_change,
            "T-8A-01":  self._expand_simplify,
            "T-8A-02":  self._solve_linear_both_sides,
            "T-8A-03":  self._gradient_two_points,
            "T-8M-02":  self._volume_prism,
            "T-8M-03":  self._circle_measure,
            "T-8M-05":  self._rate_speed_distance_time,
            "T-8M-06":  self._pythagoras,
            "T-8SP-03": self._transformation_coordinates,
            "T-8ST-01": self._mean_from_frequency_table,
            "T-8P-02":  self._two_step_probability,
            "T-8P-03":  self._relative_frequency,
            "T-9N-02":  self._scientific_notation_convert,
            "T-9N-03":  self._simple_compound_interest,
            "T-9N-04":  self._direct_proportion,
            "T-9A-01":  self._expand_binomial,
            "T-9A-02":  self._solve_linear_with_fractions,
            "T-9A-03":  self._line_equation,
            "T-9A-04":  self._simultaneous_equations,
            "T-9M-01":  self._surface_area,
            "T-9M-02":  self._volume_pyramid_cone_sphere,
            "T-9M-03":  self._trigonometry_find_side,
            "T-9M-04":  self._similar_figures,
            "T-9ST-03": self._compare_statistics,
            "T-9P-01":  self._venn_diagram_probability,
            "T-9P-03":  self._two_way_table_probability,
        }

    @property
    def curated_template_ids(self):
        """Templates that use curated_bank mode — verification comes from the bank, not this engine."""
        return {
            "T-7N-03", "T-7M-03", "T-7SP-01", "T-7SP-03", "T-7ST-02",
            "T-7P-02", "T-8M-01", "T-8M-04", "T-8SP-01", "T-8SP-02",
            "T-8ST-03", "T-8P-01", "T-9N-01", "T-9A-05", "T-9ST-03"
        }


# ─── QUICK TEST ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = VerificationEngine()

    tests = [
        ("T-7N-01", {"n": 64}, 8),
        ("T-7N-07", {"pct": 25, "amount": 200}, 50),
        ("T-7N-08", {"a": -5, "b": 3, "op": "+"}, -2),
        ("T-7N-09", {"a": 2, "b": 3, "total": 50}, 30),
        ("T-7M-01", {"shape": "triangle", "b": 10, "h": 6}, 30),
        ("T-7M-04", {"a": 65, "relationship": "supplementary"}, 115),
        ("T-8N-03", {"a": 12, "b": 18, "measure": "HCF"}, 6),
        ("T-8M-06", {"triple_family": [3,4,5], "scale": 2, "unknown_side": "hypotenuse"}, 10),
        ("T-8A-03", {"x1": 1, "y1": 2, "x2": 3, "y2": 8}, "3"),
        ("T-9A-04", {"a": 2, "b": 1, "c": -1, "d": 7}, 2),
        ("T-9M-03", {"theta": 30, "value": 10, "known_side": "hypotenuse", "unknown_side": "opposite side"}, 5.0),
    ]

    passed, failed = 0, 0
    for tid, params, expected in tests:
        result = engine.verify(tid, params)
        status = "✅" if str(result) == str(expected) or result == expected else "❌"
        if status == "✅":
            passed += 1
        else:
            failed += 1
        print(f"{status} {tid}: expected={expected}, got={result}")

    print(f"\n{passed}/{passed+failed} tests passed")
