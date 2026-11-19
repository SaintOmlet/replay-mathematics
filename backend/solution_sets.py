"""Exact, bounded parsers for finite roots and unions of real intervals.

An interval is (left, right, include_left, include_right). Finite endpoints
are Fractions. Only the two infinity sentinels are floats.
"""

from fractions import Fraction
import math
import re

from . import grading

NEGATIVE_INFINITY = -math.inf
POSITIVE_INFINITY = math.inf
EMPTY_NAMES = {"∅", "{}", "empty", "нет", "нет решений", "пусто"}
REAL_NAMES = {"r", "ℝ", "все действительные", "все числа"}
MAX_LENGTH = 512
MAX_COMPONENTS = 16


def text_input(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_LENGTH:
        raise grading.AnswerError("Укажи всё множество решений в формате под полем.")
    return raw.strip().replace("−", "-").replace("–", "-")


def parse_roots(raw):
    """Return an exact sorted tuple of distinct rational roots."""
    text = text_input(raw)
    if text.casefold() in EMPTY_NAMES:
        return ()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
        if not text.strip():
            return ()
    parts = text.split(";")
    if len(parts) > MAX_COMPONENTS:
        raise grading.AnswerError("В ответе слишком много отдельных корней.")
    values = [grading.parse_number(part) for part in parts]
    if any(value is None for value in values):
        raise grading.AnswerError("Разделяй корни точкой с запятой. Для отсутствия решений введи ∅.")
    if len(set(values)) != len(values):
        raise grading.AnswerError("Каждый корень укажи один раз.")
    return tuple(sorted(values))


def endpoint(text):
    text = text.strip().casefold().replace("∞", "inf")
    if text == "-inf":
        return NEGATIVE_INFINITY
    if text in ("inf", "+inf"):
        return POSITIVE_INFINITY
    number = grading.parse_number(text)
    if number is None:
        raise grading.AnswerError("Укажи обе границы промежутка.")
    return number


def normalize(intervals):
    """Merge exactly equal, overlapping or connected interval components."""
    ordered = sorted(intervals, key=lambda item: (item[0], not item[2], item[1]))
    result = []
    for left, right, closed_left, closed_right in ordered:
        if left > right:
            raise grading.AnswerError("Левая граница промежутка должна быть меньше правой.")
        if left == right and not (closed_left and closed_right):
            continue
        current = (left, right, closed_left, closed_right)
        if not result:
            result.append(current)
            continue
        old_left, old_right, old_closed_left, old_closed_right = result[-1]
        if left > old_right or left == old_right and not (closed_left or old_closed_right):
            result.append(current)
            continue
        end, include_end = (right, closed_right) if right > old_right else (old_right, old_closed_right)
        if right == old_right:
            include_end = old_closed_right or closed_right
        result[-1] = (old_left, end, old_closed_left, include_end)
    return tuple(result)


def parse_intervals(raw):
    """Parse unions without evaluating code or mathematical expressions."""
    text = text_input(raw)
    components = re.split(r"\s*(?:∪|\bunion\b|\bU\b)\s*", text, flags=re.IGNORECASE)
    if len(components) > MAX_COMPONENTS:
        raise grading.AnswerError("В ответе слишком много промежутков.")
    result = []
    for component in components:
        component = component.strip()
        if component.casefold() in EMPTY_NAMES:
            continue
        if component.casefold() in REAL_NAMES:
            result.append((NEGATIVE_INFINITY, POSITIVE_INFINITY, False, False))
            continue
        if component.startswith("{") and component.endswith("}"):
            result.extend((value, value, True, True) for value in parse_roots(component))
            continue
        match = re.fullmatch(r"([\[(])\s*([^;]+)\s*;\s*([^;]+)\s*([\])])", component)
        if not match:
            raise grading.AnswerError("Запиши промежутки через U, например (-inf;2] U [5;+inf). Для пустого множества введи ∅.")
        left, right = endpoint(match[2]), endpoint(match[3])
        closed_left, closed_right = match[1] == "[", match[4] == "]"
        if left == POSITIVE_INFINITY or right == NEGATIVE_INFINITY:
            raise grading.AnswerError("Проверь порядок бесконечных границ.")
        if left == NEGATIVE_INFINITY and closed_left or right == POSITIVE_INFINITY and closed_right:
            raise grading.AnswerError("Бесконечность не включают в промежуток. Используй круглую скобку.")
        result.append((left, right, closed_left, closed_right))
    return normalize(result)


def match(raw, response, target):
    if raw is None:
        return False
    parser = {"roots": parse_roots, "interval_set": parse_intervals}.get(response.get("kind"))
    if parser is None:
        raise grading.AnswerError("Неизвестный формат множества решений.")
    return parser(raw) == parser(str(target))


def contains(intervals, value):
    """Exact set membership, also usable by deterministic content checks."""
    return any((value > left or closed_left and value == left)
               and (value < right or closed_right and value == right)
               for left, right, closed_left, closed_right in intervals)


def intersect(first, second):
    result = []
    for left_a, right_a, closed_left_a, closed_right_a in first:
        for left_b, right_b, closed_left_b, closed_right_b in second:
            left, right = max(left_a, left_b), min(right_a, right_b)
            if left > right:
                continue
            closed_left = (left != left_a or closed_left_a) and (left != left_b or closed_left_b)
            closed_right = (right != right_a or closed_right_a) and (right != right_b or closed_right_b)
            if left < right or closed_left and closed_right:
                result.append((left, right, closed_left, closed_right))
    return normalize(result)


def value_text(value):
    if value == NEGATIVE_INFINITY:
        return "-inf"
    if value == POSITIVE_INFINITY:
        return "+inf"
    number = Fraction(value)
    return str(number)


def format_intervals(components):
    components = normalize(components)
    if not components:
        return "∅"
    return " U ".join(("[" if left_closed else "(") + value_text(left) + ";" + value_text(right)
                      + ("]" if right_closed else ")")
                      for left, right, left_closed, right_closed in components)


def format_roots(values):
    return ";".join(value_text(value) for value in sorted(set(values))) or "∅"
