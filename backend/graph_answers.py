"""Exact, bounded validation of learner-controlled function parameters."""

import json
import math
from fractions import Fraction

from .grading import AnswerError


MODEL_KEYS = {"line": {"m", "b"}, "parabola": {"a", "h", "k"}}


def unique_object(pairs):
    values = dict(pairs)
    if len(values) != len(pairs):
        raise ValueError("Duplicate parameter")
    return values


def parameters(raw, response):
    if not isinstance(raw, str) or len(raw) > 512:
        raise AnswerError("Измени параметры графика и отправь построение.")
    try:
        values = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        raise AnswerError("Не удалось прочитать параметры графика. Проверь поля и повтори отправку.") from None
    expected = MODEL_KEYS.get(response.get("model"))
    if not isinstance(values, dict) or expected is None or set(values) != expected:
        raise AnswerError("Для построения нужны все параметры выбранной функции.")
    constraints = {item["key"]: item for item in response["parameters"]}
    result = {}
    for key in sorted(expected):
        value = values[key]
        if type(value) not in (int, float) or type(value) is float and not math.isfinite(value):
            raise AnswerError("Параметры графика должны быть конечными числами.")
        exact = Fraction(str(value))
        constraint = constraints[key]
        minimum, maximum = Fraction(str(constraint["min"])), Fraction(str(constraint["max"]))
        if not minimum <= exact <= maximum:
            raise AnswerError(f"Параметр {key} должен быть от {constraint['min']} до {constraint['max']}.")
        step = Fraction(str(constraint["step"]))
        if step <= 0 or ((exact-minimum)/step).denominator != 1:
            raise AnswerError(f"Для параметра {key} используй шаг {constraint['step']}.")
        result[key] = exact
    if response["model"] == "parabola" and result["a"] == 0:
        raise AnswerError("Для параболы коэффициент a должен отличаться от нуля.")
    return result


def matches(raw, response, target):
    if raw is None:
        return False
    return parameters(raw, response) == parameters(target, response)


def describe(target, response):
    values = parameters(target, response)
    if response["model"] == "line":
        return f"y = ({values['m']})x + ({values['b']})"
    return f"y = ({values['a']})(x − ({values['h']}))² + ({values['k']})"
