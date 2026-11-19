"""Explain verified answer differences without guessing the learner's reasoning."""

from fractions import Fraction
import json
import math

from . import grading, solution_sets
from .content import PARAMETER_VALUES, VARIANTS_PER_FAMILY


GRAPH_KEYS = {"line": {"m", "b"}, "parabola": {"a", "h", "k"}}


def _graph_parameters(raw, response):
    if not isinstance(response, dict) or not isinstance(response.get("model"), str):
        return None
    keys = GRAPH_KEYS.get(response["model"])
    if keys is None or not isinstance(raw, str) or len(raw) > 512:
        return None
    values = json.loads(raw)
    if not isinstance(values, dict) or set(values) != keys:
        return None
    result = {}
    for name, value in values.items():
        if type(value) in (int, float):
            if isinstance(value, float) and not math.isfinite(value):
                return None
            result[name] = Fraction(str(value))
        elif isinstance(value, str):
            result[name] = grading.parse_number(value)
            if result[name] is None:
                return None
        else:
            return None
    return result


def _number(value):
    return str(value).replace("-", "−")


def _constant(expression, value):
    if value == 0:
        return expression
    return expression + (" − " if value < 0 else " + ") + _number(abs(value))


def _multiple(value, expression):
    if value == 1:
        return expression
    if value == -1:
        return "−" + expression
    return _number(value) + "·" + expression


def graph_description(raw, response):
    """Describe serialized graph parameters for feedback and saved results."""
    try:
        values = _graph_parameters(raw, response)
        if values is None:
            return None
        if response["model"] == "line":
            if values["m"] == 0:
                return "y = " + _number(values["b"])
            expression = _multiple(values["m"], "x")
            return "y = " + _constant(expression, values["b"])
        if values["a"] == 0:
            return "y = " + _number(values["k"])
        square = "x²" if values["h"] == 0 else "(" + _constant("x", -values["h"]) + ")²"
        return "y = " + _constant(_multiple(values["a"], square), values["k"])
    except (ValueError, TypeError, OverflowError):
        return None


def _graph_difference(raw, question, response):
    actual = _graph_parameters(raw, response)
    expected = _graph_parameters(question.get("answer"), response)
    if actual is None or expected is None:
        return None
    if response["model"] == "parabola" and expected["a"] == 0:
        return None
    changed = [name for name in expected if actual[name] != expected[name]]
    if len(changed) != 1:
        return None
    parameter = changed[0]
    if response["model"] == "line":
        if parameter == "b":
            return "Наклон совпадает с условием. Проверь пересечение с осью Oy: при x=0 ордината равна b."
        if expected["m"] and actual["m"] == -expected["m"]:
            return "Пересечение с Oy выбрано верно, но знак наклона противоположный. При m>0 прямая поднимается слева направо, при m<0 опускается."
        return "Пересечение с Oy выбрано верно. Проверь наклон m: это изменение y при увеличении x на 1."
    if parameter == "h":
        if expected["h"] and actual["h"] == -expected["h"]:
            return "Растяжение и высота вершины совпадают с условием, но абсцисса вершины имеет противоположный знак. В y=a(x−h)²+k вершина находится при x=h."
        return "Растяжение и высота вершины совпадают с условием. Проверь горизонтальный сдвиг: ось симметрии параболы x=h."
    if parameter == "k":
        return "Ось симметрии и коэффициент a совпадают с условием. Проверь ординату вершины k: при x=h значение y равно k."
    if actual["a"] == 0:
        return "При a=0 получается постоянная функция. Для параболы коэффициент a должен отличаться от нуля."
    if actual["a"] == -expected["a"]:
        return "Вершина и растяжение совпадают с условием, но направление ветвей противоположное. Его определяет знак a."
    if actual["a"] * expected["a"] < 0:
        return "Вершина совпадает с условием. Проверь знак a и направление ветвей, затем вертикальное растяжение, которое задаёт |a|."
    return "Вершина и направление ветвей совпадают с условием. Проверь вертикальное растяжение: при x=h+1 приращение y относительно вершины равно a."


def _root_difference(raw, target):
    actual, expected = set(solution_sets.parse_roots(raw)), set(solution_sets.parse_roots(str(target)))
    missing, extra = expected - actual, actual - expected
    if not missing and not extra:
        return None
    if missing and not extra:
        return "Указанные корни подходят, но множество решений неполное. Проверь обе ветви модуля и все допустимые значения после замены переменной."
    if extra and not missing:
        return "В ответе есть лишние значения. Проверь каждый корень подстановкой в исходное уравнение и учти ограничения ветвей или замены переменной."
    return "В ответе есть лишние значения и пропущены подходящие корни. Проверь ограничения после замены переменной, затем подставь каждый корень в исходное уравнение."


def _interval_difference(raw, question):
    actual = solution_sets.parse_intervals(raw)
    expected = solution_sets.parse_intervals(str(question.get("answer")))
    if actual == expected:
        return None
    same_boundaries = len(actual) == len(expected) and all(a[:2] == b[:2] for a, b in zip(actual, expected))
    rational = question.get("family") in ("rational_linear", "rational_three_critical", "rational_interval")
    if same_boundaries:
        text = "Границы промежутков найдены верно. Проверь круглые и квадратные скобки: строгий знак исключает равенство."
    else:
        text = "Проверь знаки на каждом промежутке и включение граничных точек. В ответ должны войти все подходящие части числовой прямой."
    if rational:
        text += " Значения, обнуляющие знаменатель, всегда исключаются."
    return text


def _linear_difference(raw, question):
    family, seed = question.get("family"), question.get("seed")
    if family not in ("linear_isolate", "linear_brackets") or type(seed) is not int or seed < 0:
        return None
    from .curriculum import EXTRA_FIRST_SEED, EXTRA_LAST_SEED, EXTRA_PARAMETER_VALUES

    if seed >= EXTRA_FIRST_SEED:
        if family != "linear_isolate" or seed > EXTRA_LAST_SEED:
            return None
        i, j = divmod(seed - EXTRA_FIRST_SEED, EXTRA_PARAMETER_VALUES)
        i += PARAMETER_VALUES
    else:
        family_index, pair = divmod(seed, VARIANTS_PER_FAMILY)
        expected_index = 0 if family == "linear_isolate" else 1
        if family_index != expected_index:
            return None
        i, j = divmod(pair, PARAMETER_VALUES)
    value = grading.parse_number(raw)
    if value is None or grading.number_matches(value, question.get("answer")):
        return None
    if family == "linear_isolate":
        a, b, x = i + 2, i + 3, j - 5
        if not grading.number_matches(Fraction(x), question.get("answer")):
            return None
        c = a * x + b
        if value == a * x:
            return f"Это значение {_number(a)}x после вычитания постоянного слагаемого. Для нахождения x раздели обе части на {_number(a)}."
        if value == Fraction(c + b, a):
            return f"Такое значение получается при прибавлении {_number(b)} к правой части. Чтобы убрать +{_number(b)} слева, вычти его из обеих частей, затем выполни деление."
    else:
        a, b, x = i + 3, j + 2, j - 3
        if not grading.number_matches(Fraction(x), question.get("answer")):
            return None
        if value == x + b:
            return f"Это значение выражения x+{_number(b)} после деления на {_number(a)}. Чтобы найти x, осталось вычесть {_number(b)}."
    return None


def explain(question, outcome):
    """Give feedback only after a real incorrect submission, including old data."""
    if not isinstance(question, dict) or not isinstance(outcome, dict):
        return None
    raw = outcome.get("submitted")
    if outcome.get("correct") is not False or outcome.get("timedOut") or outcome.get("unanswered"):
        return None
    if not isinstance(raw, str) or not raw.strip():
        return None
    response = question.get("response") or {}
    if not isinstance(response, dict):
        return None
    try:
        kind = response.get("kind")
        if kind == "graph":
            return _graph_difference(raw, question, response)
        if kind == "roots":
            return _root_difference(raw, question.get("answer"))
        if kind in ("interval_set", "interval"):
            return _interval_difference(raw, question)
        if not response:
            return _linear_difference(raw, question)
    except (ValueError, TypeError, OverflowError):
        return None
    return None
