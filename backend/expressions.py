"""Bounded exact polynomial/rational-expression checker, without evaluation of code."""
import re
from collections import Counter
from fractions import Fraction

from .grading import AnswerError

MAX_TERMS = 256
MAX_DEGREE = 24
TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[.,]\d+|[A-Za-z]+|[()+*/^−+\-]")


def clean(polynomial):
    result = {power: coefficient for power, coefficient in polynomial.items() if coefficient}
    if len(result) > MAX_TERMS or any(sum(power) > MAX_DEGREE for power in result):
        raise AnswerError("Выражение слишком сложное. Запиши результат компактнее.")
    if any(max(coefficient.numerator.bit_length(), coefficient.denominator.bit_length()) > 2048 for coefficient in result.values()):
        raise AnswerError("Коэффициенты слишком велики.")
    return result


def add(left, right):
    result = dict(left)
    for power, coefficient in right.items():
        result[power] = result.get(power, Fraction(0)) + coefficient
    return clean(result)


def multiply(left, right):
    result = {}
    for first, a in left.items():
        for second, b in right.items():
            power = tuple(x+y for x, y in zip(first, second))
            if sum(power) > MAX_DEGREE:
                raise AnswerError("Степень выражения слишком велика.")
            result[power] = result.get(power, Fraction(0)) + a*b
            if len(result) > MAX_TERMS:
                raise AnswerError("Выражение слишком сложное. Запиши результат компактнее.")
    return clean(result)


def power(polynomial, exponent, one):
    result = one
    for _ in range(exponent):
        result = multiply(result, polynomial)
    return result


class Expression:
    def __init__(self, raw, variables):
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 512:
            raise AnswerError("Введи выражение длиной до 512 знаков.")
        self.variables = tuple(variables)
        if not self.variables or len(self.variables) > 6 or len(set(self.variables)) != len(self.variables):
            raise AnswerError("Неизвестный набор переменных.")
        source = raw.replace("−", "-").replace("·", "*").replace("×", "*").replace("²", "^2").replace("³", "^3")
        tokens = []
        position = 0
        while position < len(source):
            if source[position].isspace():
                position += 1
                continue
            match = TOKEN.match(source, position)
            if match is None:
                raise AnswerError("Используй числа, переменные, скобки и знаки + − * / ^.")
            token = match[0]
            position = match.end()
            if token[0].isalpha() and token not in self.variables:
                if all(letter in self.variables for letter in token):
                    tokens.extend(token)
                    continue
                raise AnswerError("Допустимые переменные: " + ", ".join(self.variables) + ".")
            if len(token) > 32:
                raise AnswerError("Число или имя переменной слишком длинное.")
            tokens.append(token)
        if len(tokens) > 200:
            raise AnswerError("Выражение слишком длинное.")
        self.tokens = tokens
        self.position = 0
        self.depth = 0
        self.zero = (0,)*len(variables)
        self.one = {self.zero: Fraction(1)}
        try:
            self.tree = self.sum()
        except RecursionError:
            raise AnswerError("Слишком много вложенных скобок или степеней.") from None
        if self.position != len(tokens):
            raise AnswerError("Проверь скобки и знаки операций.")
        self.value = self.evaluate(self.tree)

    def peek(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def sum(self):
        node = self.product()
        while self.peek() in ("+", "-"):
            operation = self.peek()
            self.position += 1
            node = (operation, node, self.product())
        return node

    def product(self):
        node = self.unary()
        while self.peek() is not None and self.peek() not in ("+", "-", ")"):
            operation = self.peek() if self.peek() in ("*", "/") else "*"
            if self.peek() in ("*", "/"):
                self.position += 1
            node = (operation, node, self.unary())
        return node

    def unary(self):
        if self.peek() in ("+", "-"):
            sign = self.peek()
            self.position += 1
            return self.unary() if sign == "+" else ("neg", self.unary())
        node = self.atom()
        if self.peek() == "^":
            self.position += 1
            node = ("^", node, self.unary())
        return node

    def atom(self):
        token = self.peek()
        if token is None:
            raise AnswerError("После знака операции нужно выражение.")
        self.position += 1
        if token == "(":
            self.depth += 1
            if self.depth > 24:
                raise AnswerError("Слишком много вложенных скобок.")
            node = self.sum()
            if self.peek() != ")":
                raise AnswerError("Закрой скобку.")
            self.position += 1
            self.depth -= 1
            return node
        if token in self.variables:
            return ("variable", self.variables.index(token))
        try:
            return ("number", Fraction(token.replace(",", ".")))
        except ValueError:
            raise AnswerError("Проверь выражение рядом со знаком «" + token + "».") from None

    def constant(self, value):
        return {} if not value else {self.zero: Fraction(value)}

    def evaluate(self, node):
        operation = node[0]
        if operation == "number":
            return self.constant(node[1]), self.one
        if operation == "variable":
            degree = list(self.zero)
            degree[node[1]] = 1
            return {tuple(degree): Fraction(1)}, self.one
        if operation == "neg":
            numerator, denominator = self.evaluate(node[1])
            return {key: -value for key, value in numerator.items()}, denominator
        a, b = self.evaluate(node[1])
        c, d = self.evaluate(node[2])
        if operation in ("+", "-"):
            second = multiply(c, b)
            if operation == "-":
                second = {key: -value for key, value in second.items()}
            return add(multiply(a, d), second), multiply(b, d)
        if operation == "*":
            return multiply(a, c), multiply(b, d)
        if operation == "/":
            if not c:
                raise AnswerError("Деление на нулевое выражение запрещено.")
            return multiply(a, d), multiply(b, c)
        if set(c)-{self.zero} or set(d)-{self.zero}:
            raise AnswerError("Показатель степени должен быть целым числом.")
        exponent = c.get(self.zero, Fraction(0))/d[self.zero]
        if exponent.denominator != 1 or abs(exponent) > 12:
            raise AnswerError("Допустимы целые показатели степени от −12 до 12.")
        exponent = int(exponent)
        if exponent <= 0 and not a:
            raise AnswerError("Ноль в нулевой или отрицательной степени не определён.")
        if exponent < 0:
            a, b, exponent = b, a, -exponent
        return power(a, exponent, self.one), power(b, exponent, self.one)

    def simple_constant(self, node):
        if node[0] == "number":
            return True
        if node[0] == "neg":
            return self.simple_constant(node[1])
        return node[0] == "/" and self.simple_constant(node[1]) and self.simple_constant(node[2])

    def monomial_factors(self, node):
        if node[0] == "neg":
            return self.monomial_factors(node[1])
        if self.simple_constant(node):
            return ["constant"]
        if node[0] == "variable":
            return [node[1]]
        if node[0] == "^" and node[1][0] == "variable":
            return [node[1][1]]
        if node[0] in ("*", "/"):
            left, right = self.monomial_factors(node[1]), self.monomial_factors(node[2])
            return None if left is None or right is None else left+right
        return None

    def expanded(self, node=None):
        node = self.tree if node is None else node
        if node[0] in ("+", "-"):
            left, right = self.expanded(node[1]), self.expanded(node[2])
            if left is None or right is None or set(left) & set(right):
                return None
            return left+right
        if node[0] == "neg":
            return self.expanded(node[1])
        factors = self.monomial_factors(node)
        if factors is None or len(factors) != len(set(factors)):
            return None
        numerator, denominator = self.evaluate(node)
        if set(denominator)-{self.zero} or len(numerator) > 1:
            return None
        return list(numerator) if numerator else [self.zero]

    def factor_signature(self, node=None, multiplicity=1):
        node = self.tree if node is None else node
        if node[0] == "neg":
            scalar, factors = self.factor_signature(node[1], multiplicity)
            return scalar*(Fraction(-1)**multiplicity), factors
        if node[0] in ("*", "/"):
            left, first = self.factor_signature(node[1], multiplicity)
            right, second = self.factor_signature(node[2], multiplicity if node[0] == "*" else -multiplicity)
            first.update(second)
            return left*right, first
        if node[0] == "^":
            numerator, denominator = self.evaluate(node[2])
            if (set(numerator) | set(denominator))-{self.zero}:
                raise AnswerError("Показатель степени должен быть постоянным.")
            exponent = numerator.get(self.zero, Fraction(0))/denominator[self.zero]
            if exponent.denominator != 1:
                raise AnswerError("Показатель степени должен быть целым.")
            return self.factor_signature(node[1], multiplicity*int(exponent))
        numerator, denominator = self.evaluate(node)
        if set(denominator)-{self.zero}:
            raise AnswerError("В разложении записывай множители отдельно.")
        if not numerator:
            return Fraction(0), Counter()
        leading = max(numerator, key=lambda key: (sum(key), key))
        coefficient = numerator[leading]/denominator[self.zero]
        if leading == self.zero:
            return coefficient**multiplicity, Counter()
        factor = tuple(sorted((key, value/numerator[leading]) for key, value in numerator.items()))
        return coefficient**multiplicity, Counter({factor: multiplicity})


def matches(raw, response, target):
    if raw is None:
        return False
    variables = response.get("variables", ["x"])
    actual, expected = Expression(raw, variables), Expression(str(target), variables)
    if multiply(actual.value[0], expected.value[1]) != multiply(expected.value[0], actual.value[1]):
        return False
    form = response.get("form", "any")
    if form == "expanded":
        return actual.expanded() is not None
    if form == "monomial":
        factors = actual.monomial_factors(actual.tree)
        return factors is not None and len(factors) == len(set(factors))
    if form == "factored":
        scalar, factors = actual.factor_signature()
        wanted_scalar, wanted_factors = expected.factor_signature()
        return scalar == wanted_scalar and {key: value for key, value in factors.items() if value} == {key: value for key, value in wanted_factors.items() if value}
    return True
