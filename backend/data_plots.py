"""Exact answers for authored frequency tables and statistical plots."""
import json

from .grading import AnswerError, parse_number


def values(raw, response):
    try:
        parts = json.loads(raw)
    except (ValueError, TypeError):
        raise AnswerError("Заполни все строки таблицы числами или точными дробями.") from None
    if not isinstance(parts, list) or len(parts) != len(response["labels"]):
        raise AnswerError("Заполни все строки таблицы.")
    result = []
    for part in parts:
        if not isinstance(part, str) or len(part) > 40:
            raise AnswerError("Введи число или дробь в каждой строке.")
        value = parse_number(part)
        if value is None or value < 0 or value > 10000:
            raise AnswerError("Каждая частота или плотность должна быть неотрицательным числом до 10 000.")
        result.append(value)
    return tuple(result)


def matches(raw, response, target):
    return values(raw,response) == values(target,response)


def describe(raw, response):
    return "; ".join(f"{label}: {value}" for label,value in zip(response["labels"], values(raw,response)))
