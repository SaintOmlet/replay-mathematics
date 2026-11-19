"""Safe answer parsing, structured responses and SAT-specific formatting."""
import math
import random
import re
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from fractions import Fraction
from math import gcd

NUMBER = r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)"
PATTERN = re.compile(rf"({NUMBER})(?:\s*/\s*({NUMBER}))?\Z")


class AnswerError(ValueError):
    pass


def parse_number(raw):
    if raw is None:
        return None
    if not isinstance(raw, str) or len(raw) > 128:
        raise AnswerError("Ответ должен быть числом или дробью.")
    raw = raw.strip().replace("−", "-")
    if not raw:
        return None
    # Only unambiguous thousands groups, not mixed numbers such as '3 1/2'.
    grouped = r"([+-]?\d{1,3})(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?"
    if re.fullmatch(grouped, raw):
        raw = re.sub(r"[ \u00a0\u202f]", "", raw)
    match = PATTERN.fullmatch(raw)
    if not match:
        raise AnswerError("Введи число, например 12, −0,5 или 3/4.")
    value = Fraction(Decimal(match[1].replace(",", ".")))
    if match[2] is None:
        return value
    divisor = Fraction(Decimal(match[2].replace(",", ".")))
    if not divisor:
        raise AnswerError("Знаменатель дроби должен быть отличен от нуля.")
    return value / divisor


def number_matches(value, target):
    if value is None:
        return False
    exact = Fraction(str(target))
    return value == exact or isinstance(target, float) and math.isclose(
        float(value), target, rel_tol=1e-10, abs_tol=1e-10
    )


def rational(target):
    return Fraction(str(target)).limit_denominator(10_000_000)


def sat_input_available(target):
    """Whether the key has a usable student-produced response representation."""
    exact = rational(target)
    text = str(exact)
    limit = 6 if exact < 0 else 5
    return len(text) <= limit or exact.denominator != 1 and abs(exact) < 1000


def sat_matches(raw, target):
    if raw is None or raw == "":
        return False
    if not isinstance(raw, str):
        raise AnswerError("Введи ответ SAT числом или дробью.")
    text = raw.strip().replace("−", "-")
    if not text:
        return False
    syntax = r"-?(?:[0-9]+/[0-9]+|[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
    if len(text) > (6 if text.startswith("-") else 5) or not re.fullmatch(syntax, text):
        raise AnswerError("В SAT введи до 5 знаков для положительного ответа или до 6 с минусом. Используй точку или дробь.")
    value = parse_number(text)
    if number_matches(value, target):
        return True
    if "/" in text or "." not in text:
        return False
    # Decimal alternatives must fill the available positions (e.g. .6667 or 0.667).
    negative = text.startswith("-")
    body = text[1:] if negative else text
    whole, fractional = body.split(".")
    # Padding integer zeros cannot replace decimal precision.
    normalized = ("-" if negative else "") + (whole.lstrip("0") or ("0" if whole else "")) + "." + fractional
    if len(normalized) != (6 if negative else 5):
        return False
    places = len(text.rsplit(".", 1)[1])
    exact = rational(target)
    decimal = Decimal(exact.numerator) / Decimal(exact.denominator)
    quantum = Decimal(1).scaleb(-places)
    return any(value == Fraction(decimal.quantize(quantum, rounding=rounding))
               for rounding in (ROUND_DOWN, ROUND_HALF_UP))


def options(topic_id, variant, target, bounds=None):
    rng = random.Random(f"choices-v2:{topic_id}:{variant}")
    exact = rational(target)
    integral = exact.denominator == 1
    step = Fraction(max(1, abs(int(target)) // 17)) if integral else Fraction(1, 20)
    candidates = set()
    for offset in range(-12, 13):
        candidate = exact + step * offset
        if candidate == exact:
            continue
        domain = (0,1) if topic_id == "probability" else bounds
        if domain is not None and not domain[0] <= candidate <= domain[1]:
            continue
        candidates.add(candidate)
    selected = [exact] + rng.sample(sorted(candidates), 3)
    rng.shuffle(selected)
    # Same representation rule applies to the key and each distractor.
    return [str(value.numerator) if integral else f"{value.numerator}/{value.denominator}" for value in selected]


def structured_matches(raw, response, target):
    if raw is None:
        return False
    if not isinstance(raw, str) or len(raw) > 512:
        raise AnswerError("Проверь формат ответа.")
    kind = response["kind"]
    if kind == "data_plot":
        from .data_plots import matches
        return matches(raw,response,target)
    if kind == "expression":
        from .expressions import matches
        return matches(raw,response,target)
    if kind == "graph":
        from .graph_answers import matches
        return matches(raw,response,target)
    if kind in ("roots", "interval_set"):
        from .solution_sets import match
        return match(raw,response,target)
    if kind == "fraction":
        match = re.fullmatch(r"([+-]?[0-9]+)(?:\s*/\s*([0-9]+))?", raw.strip().replace("−", "-"))
        if not match:
            raise AnswerError("Введи точную несократимую дробь, например 3/11. Целый результат можно записать целым числом.")
        numerator, denominator = int(match[1]), int(match[2] or 1)
        if denominator == 0:
            raise AnswerError("Знаменатель дроби должен быть отличен от нуля.")
        if gcd(numerator, denominator) != 1:
            raise AnswerError("Сократи дробь перед отправкой.")
        return Fraction(numerator, denominator) == rational(target)
    if kind in ("choice", "sequence"):
        values = [part.strip() for part in raw.split(",")]
        valid = {option["value"] for option in response["options"]}
        if any(value not in valid for value in values) or len(values) != len(set(values)):
            raise AnswerError("Выбери допустимые варианты без повторов.")
        return ",".join(values) == str(target)
    if kind == "pair":
        text = raw.strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1]
        parts = text.split(";")
        expected = str(target).split(";")
        if len(parts) != 2:
            raise AnswerError("Введи пару через точку с запятой: 2; 3.")
        return all(parse_number(a) == Fraction(b.replace(",", ".")) for a, b in zip(parts, expected))
    if kind == "interval":
        def interval(text):
            text = text.strip().replace("−", "-").replace("∞", "inf")
            match = re.fullmatch(r"([\[(])\s*(.*?)\s*;\s*(.*?)\s*([\])])", text)
            if not match:
                raise AnswerError("Введи промежуток через точку с запятой: (2; 5].")
            ends = []
            for token in (match[2], match[3]):
                ends.append("inf" if token == "+inf" else token if token in ("-inf", "inf") else parse_number(token))
            if ends[0] == "inf" or ends[1] == "-inf":
                raise AnswerError("Проверь порядок границ.")
            if ends[0] is None or ends[1] is None:
                raise AnswerError("Укажи обе границы промежутка.")
            if ends[0] == "-inf" and match[1] != "(" or ends[1] == "inf" and match[4] != ")":
                raise AnswerError("У бесконечной границы используй круглую скобку.")
            return match[1], ends, match[4]
        return interval(raw) == interval(str(target))
    raise AnswerError("Неизвестный формат ответа.")
