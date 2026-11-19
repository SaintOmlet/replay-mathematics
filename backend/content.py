"""Original bilingual math exercises aligned with common school and SAT skills."""

from math import comb
from typing import Callable


def topic(key, grade, title, description, formula, sat, icon, *lesson):
    return dict(id=key, grade=grade, title=title, description=description,
                formula=formula, sat=sat, icon=icon, lesson=list(lesson))


TOPICS = [
    topic("linear", 7, "Линейные уравнения", "Изолируй неизвестную и проверяй ответ подстановкой.",
          "ax + b = c", "Linear equations in one variable", "x",
          "Уравнение сохраняет решения, если выполнить одну и ту же обратимую операцию с обеими частями.",
          "Собери слагаемые с x слева, числа справа. Раздели обе части на коэффициент при x.",
          "Пример: 3x + 4 = 19. Вычитаем 4: 3x = 15. Делим на 3: x = 5. Проверка: 15 + 4 = 19."),
    topic("percent", 7, "Проценты", "Находи долю, исходную величину и результат изменения.",
          "новое = исходное × (1 ± p/100)", "Percentages", "%",
          "Один процент — одна сотая. Чтобы найти p процентов от числа, умножь его на p/100.",
          "При увеличении на p% множитель равен 1 + p/100, при уменьшении — 1 − p/100.",
          "Пример: после скидки 20% цена 1200 ₸. Это 0,8 исходной цены, поэтому исходная цена 1200 ÷ 0,8 = 1500 ₸."),
    topic("lines", 7, "Прямые и линейные функции", "Связывай формулу прямой, её наклон и точки.",
          "y = mx + b", "Linear functions", "↗",
          "В формуле y = mx + b число m показывает изменение y при увеличении x на единицу.",
          "Число b задаёт значение y при x = 0. По двум точкам наклон равен (y₂ − y₁)/(x₂ − x₁).",
          "Пример: точки (1, 5) и (3, 9). Наклон (9 − 5)/(3 − 1) = 2. Тогда b = 5 − 2 × 1 = 3."),
    topic("systems", 8, "Системы уравнений", "Решай через подстановку, исключение или пересечение графиков.",
          "y₁ = y₂", "Systems of two linear equations", "∩",
          "Решение системы удовлетворяет обоим уравнениям. Для двух прямых это их общая точка.",
          "При подстановке выражаем одну переменную через другую. При исключении складываем или вычитаем уравнения, чтобы убрать переменную.",
          "Пример: x + y = 12 и x − y = 4. Складываем: 2x = 16, значит x = 8. Тогда y = 4."),
    topic("triangles", 8, "Треугольники", "Решай задачи на площадь, подобие и теорему Пифагора.",
          "S = bh/2  ·  c² = a² + b²", "Area, right triangles and similarity", "△",
          "Площадь треугольника равна половине произведения основания и перпендикулярной к нему высоты.",
          "Для прямоугольного треугольника сумма квадратов катетов равна квадрату гипотенузы.",
          "Пример: катеты 6 и 8. Площадь 6 × 8 ÷ 2 = 24, гипотенуза √(36 + 64) = 10."),
    topic("powers", 8, "Степени и корни", "Упрощай степени и находи точные квадратные корни.",
          "aᵐ × aⁿ = aᵐ⁺ⁿ", "Equivalent expressions", "aⁿ",
          "При умножении степеней с одинаковым основанием показатели складываются.",
          "При возведении степени в степень показатели умножаются. Для a ≠ 0 верно a⁻ⁿ = 1/aⁿ.",
          "Пример: 2³ × 2⁴ = 2⁷. Положительный квадратный корень √49 = 7."),
    topic("quadratics", 9, "Квадратичные функции", "Находи корни, вершину и касания параболы.",
          "y = a(x − h)² + k", "Nonlinear equations and functions", "∪",
          "У параболы y = a(x − h)² + k вершина (h, k). Если a > 0, минимальное значение функции — k.",
          "Корни функции — координаты x её пересечений с осью x. В произведении (x − r₁)(x − r₂) корни читаются сразу.",
          "Пример: y = (x − 3)² + 2. Вершина (3, 2); горизонтальная прямая y = 2 касается параболы в этой точке."),
    topic("exponential", 9, "Экспоненциальный рост", "Отличай постоянную прибавку от умножения на один и тот же коэффициент.",
          "A(t) = A₀ × rᵗ", "Exponential functions", "×",
          "Когда величина умножается на число r за каждый шаг, после t шагов она равна A₀ × rᵗ.",
          "Рост на 15% за шаг соответствует r = 1,15. Уменьшение на 15% соответствует r = 0,85.",
          "Пример: было 80, количество удваивается каждый час. Через 3 часа будет 80 × 2³ = 640."),
    topic("statistics", 9, "Среднее и медиана", "Сравнивай выборки и восстанавливай данные по их сводкам.",
          "среднее = сумма / количество", "One-variable data", "μ",
          "Среднее учитывает все значения. Чтобы восстановить сумму, умножь среднее на количество наблюдений.",
          "Медиана — центральное значение упорядоченного ряда. При чётном числе наблюдений усредняют два центральных значения.",
          "Пример: для 2, 3 и 10 среднее равно 5, а медиана — 3. Большое число меняет среднее сильнее."),
    topic("probability", 9, "Вероятность", "Считай доли исходов, условные и независимые события.",
          "P(A) = число подходящих / число возможных", "Probability and conditional probability", "P",
          "Для равновероятных исходов дели число подходящих на общее число возможных.",
          "Если известно условие, общий набор сужается до исходов, которые удовлетворяют этому условию.",
          "Пример: в коробке 3 синих и 2 белых шара. Синий первым: 3/5. Второй синий при первом синем без возврата: 2/4."),
]


def number(value):
    return str(value).replace("-", "−")


def signed(value):
    return f"+ {value}" if value >= 0 else f"− {abs(value)}"


def line(m, b):
    return f"{m}x {signed(b)}"


def row(ru, en, answer, hint, *solution, followup, graph=None):
    problem = dict(ru=ru, en=en, answer=answer, hints=[hint, followup], solution=list(solution))
    if graph is not None:
        problem["graph"] = graph
    return problem


def quad(a, b, c):
    return dict(type="quadratic", a=a, b=b, c=c)


def lines(m1, b1, m2, b2):
    return dict(type="lines", m1=m1, b1=b1, m2=m2, b2=b2)


def triangle(base, height):
    return dict(type="triangle", base=base, height=height)


def linear_isolate(i, j):
    a, b, x = i + 2, i + 3, j - 5
    c = a * x + b
    return row(f"Найдите x: {a}x + {b} = {number(c)}.",
               f"What is the solution to {a}x + {b} = {number(c)}?", x,
               "Вычтите постоянное слагаемое из обеих частей.",
               f"{a}x = {number(c)} − {b} = {number(a*x)}.",
               f"x = {number(a*x)} ÷ {a} = {number(x)}.",
               followup="После вычитания постоянного слагаемого останется ax=d. Раздели обе части на a и проверь подстановкой.")


def linear_brackets(i, j):
    a, b, x = i + 3, j + 2, j - 3
    c = a * (x + b)
    return row(f"Найдите x: {a}(x + {b}) = {number(c)}.",
               f"If {a}(x + {b}) = {number(c)}, what is x?", x,
               "Сначала разделите обе части на множитель перед скобками.",
               f"x + {b} = {number(c)} ÷ {a} = {number(x+b)}.",
               f"x = {number(x+b)} − {b} = {number(x)}.",
               followup="После первого деления раскрой уравнение внутри скобок: перенеси постоянное слагаемое и раздели на коэффициент.")


def linear_both_sides(i, j):
    a, b, x = i + 2, 4, j + 1
    c = b + 3 * x
    return row(f"Решите уравнение: {a+3}x + {b} = {a}x + {c}.",
               f"What value of x satisfies {a+3}x + {b} = {a}x + {c}?", x,
               "Вычтите меньшее слагаемое с x из обеих частей.",
               f"3x + {b} = {c}, поэтому 3x = {c-b}.",
               f"x = {c-b} ÷ 3 = {x}.",
               followup="Получив (a−c)x=d−b, проверь, что коэффициент при x не равен нулю, и раздели на него.")


def linear_cost(i, j):
    fee, unit, count = 100 * (i + 2), 150, j + 3
    total = fee + unit * count
    return row(f"Мастерская берёт {fee} ₸ за подготовку заказа и {unit} ₸ за деталь. "
               f"За заказ заплатили {total} ₸. Сколько деталей заказали?",
               f"A workshop charges {fee} tenge per order plus {unit} tenge per part. "
               f"An order costs {total} tenge. How many parts are in the order?", count,
               "Сначала отделите фиксированную плату.",
               f"Детали стоят {total} − {fee} = {unit*count} ₸.",
               f"Количество равно {unit*count} ÷ {unit} = {count}.",
               followup="Оставшаяся после фиксированной платы сумма оплачивает одинаковые единицы. Раздели её на цену одной.")


def percent_of(i, j):
    p, total = (i + 1) * 5, 200 * (j + 1)
    amount = total * p // 100
    return row(f"Из {total} страниц книги прочитали {p}%. Сколько страниц прочитали?",
               f"A reader finishes {p}% of a {total}-page book. How many pages did the reader finish?", amount,
               "Замените знак процента делением на 100.",
               f"Вычислите {total} × {p}/100.",
               f"Прочитано {amount} страниц.",
               followup="Сначала запиши долю как p/100. После умножения проверь, разумна ли полученная часть относительно целого.")


def percent_increase(i, j):
    p, total = (i + 2) * 4, 100 * (j + 5)
    increased = total * (100 + p) // 100
    return row(f"В прошлом месяце секцию посетили {total} человек. Число посетителей выросло на {p}%. "
               "Сколько посетителей было в новом месяце?",
               f"A club had {total} visitors last month. This month the number increased by {p}%. "
               "How many visitors came this month?", increased,
               "После роста осталось 100% старого значения и добавился процент роста.",
               f"Множитель роста равен 1 + {p}/100.",
               f"{total} × (1 + {p}/100) = {increased}.",
               followup="Используй множитель 1+p/100. Он больше единицы, поэтому новое положительное значение должно быть больше исходного.")


def percent_reverse(i, j):
    p, original = (i + 1) * 5, 500 * (j + 4)
    discounted = original * (100 - p) // 100
    return row(f"После скидки {p}% сумка стоит {discounted} ₸. Какой была цена до скидки?",
               f"A bag costs {discounted} tenge after a {p}% discount. What was its original price, in tenge?", original,
               "Текущая цена составляет 100% минус скидка от исходной цены.",
               f"{discounted} — это {100-p}% исходной цены.",
               f"Исходная цена {discounted} ÷ ({100-p}/100) = {original} ₸.",
               followup="Исходное значение умножается на 1−p/100. Для обратного хода раздели известную цену на этот множитель.")


def percent_change(i, j):
    old, growth = (i + 1) * 100, (j + 1) * 5
    new = old * (100 + growth) // 100
    return row(f"Стоимость услуги выросла с {old} до {new} ₸. На сколько процентов она выросла?",
               f"The cost of a service rises from {old} to {new} tenge. What is the percent increase?", growth,
               "Разницу надо делить на исходное значение.",
               f"Разница = {new} − {old} = {new-old}.",
               f"Рост = {new-old}/{old} × 100% = {growth}%.",
               followup="Разность нового и старого значений раздели на старое, затем умножь на 100.")


def lines_slope(i, j):
    m, y = i - 4, j + 2
    return row(f"Каков наклон прямой через точки (1; {y}) и (3; {number(y+2*m)})?",
               f"What is the slope of the line through (1, {y}) and (3, {number(y+2*m)})?", m,
               "Разделите изменение y на изменение x.",
               f"Изменение x равно 3 − 1 = 2, изменение y равно {number(2*m)}.",
               f"Наклон = {number(2*m)}/2 = {number(m)}.",
               followup="В числителе и знаменателе используй один порядок точек. Знак наклона должен согласоваться с ростом или убыванием.")


def lines_intercept(i, j):
    m, b = i + 2, j - 4
    y = 2 * m + b
    return row(f"Наклон прямой равен {m}, а точка (2; {y}) лежит на ней. "
               "Чему равно значение y при x = 0?",
               f"A line with slope {m} contains (2, {y}). What is its y-intercept?", b,
               "Подставьте известную точку в форму y = mx + b.",
               f"{y} = {m} × 2 + b.",
               f"b = {y} − {m*2} = {number(b)}.",
               followup="После подстановки координат точки вычти mx из y. Полученное b должно давать ту же точку на прямой.")


def lines_table(i, j):
    m, b = i + 2, j + 1
    return row(f"Значения f(1) = {m+b} и f(2) = {2*m+b} принадлежат одной линейной функции. "
               "Найдите f(5).",
               f"For a linear function f, f(1) = {m+b} and f(2) = {2*m+b}. What is f(5)?", 5*m+b,
               "Изменение f при увеличении x на 1 постоянно.",
               f"Каждый шаг увеличивает f на {2*m+b} − {m+b} = {m}.",
               f"f(5) = f(2) + 3 × {m} = {5*m+b}.",
               followup="Вычти известные значения функции и раздели на разность аргументов.")


def lines_rate(i, j):
    start, rate = 12 + i, 3 + j
    return row(f"В баке было {start} литров. Каждую минуту поступает ещё {rate} литров. "
               "Сколько литров будет через 6 минут?",
               f"A tank starts with {start} liters and receives {rate} liters each minute. "
               "How many liters are in the tank after 6 minutes?", start+6*rate,
               "Начальный объём — значение функции при t = 0.",
               f"За 6 минут добавится 6 × {rate} = {6*rate} литров.",
               f"Всего будет {start} + {6*rate} = {start+6*rate} литров.",
               followup="В линейной модели значение в момент t равно начальному запасу плюс скорость, умноженная на t.")


def systems_sum(i, j):
    x, y = i + 5, j + 2
    s, d = x+y, x-y
    return row(f"В системе x + y = {s} и x − y = {number(d)} найдите x.",
               f"If x + y = {s} and x − y = {number(d)}, what is x?", x,
               "Сложите уравнения, чтобы исключить y.",
               f"2x = {s} + ({number(d)}) = {2*x}.",
               f"x = {x}. Подстановка даёт y = {y}.",
               graph=lines(-1, s, 1, -d),
               followup="При сложении левая часть станет 2x. Правые части тоже сложи, затем раздели полученное равенство на 2.")


def systems_prices(i, j):
    pen, notebook = 10 * (i + 5), 20 * (j + 3)
    a, b = 2*pen+notebook, pen+2*notebook
    return row(f"Две ручки и один блокнот стоят {a} ₸, а одна ручка и два блокнота стоят {b} ₸. "
               "Сколько стоит один блокнот?",
               f"Two pens and one notebook cost {a} tenge. One pen and two notebooks cost {b} tenge. "
               "What is the cost of one notebook, in tenge?", notebook,
               "Умножьте второе уравнение на 2 и вычтите первое.",
               f"Обозначим цены p и n: 2p + n = {a}, p + 2n = {b}.",
               f"3n = 2 × {b} − {a} = {3*notebook}, поэтому n = {notebook}.",
               followup="Составь линейную комбинацию так, чтобы коэффициенты второй цены сократились, затем найди первую цену.")


def systems_intersect(i, j):
    m, x, b = i + 2, j + 1, 2
    c = (m - 1)*x+b
    return row(f"Найдите координату x точки пересечения прямых y = {line(m,b)} и y = x + {c}.",
               f"What is the x-coordinate of the intersection of y = {line(m,b)} and y = x + {c}?", x,
               "В точке пересечения обе формулы дают одно значение y.",
               f"{line(m,b)} = x + {c}.",
               f"{m-1}x = {c-b}, поэтому x = {x}.",
               graph=lines(m, b, 1, c),
               followup="После приравнивания собери члены с x в одной части. Координату y можно использовать для обратной проверки.")


def systems_infinite(i, j):
    m, b, k = i + 2, j + 1, 3
    return row(f"При каком q система {m}x + y = {b}, {k*m}x + {k}y = q имеет бесконечно много решений?",
               f"For what value of q does the system {m}x + y = {b}, {k*m}x + {k}y = q "
               "have infinitely many solutions?", k*b,
               "Для совпадающих прямых одно уравнение получается умножением другого.",
               f"Вторая левая часть — это первая, умноженная на {k}.",
               f"Значит q = {k} × {b} = {k*b}.",
               followup="Один и тот же множитель должен одновременно переводить все коэффициенты и свободный член в другие.")


def triangles_area(i, j):
    base, height = 2 * (i + 3), j + 5
    area = base * height // 2
    return row(f"У треугольника основание {base} см и высота {height} см. Найдите площадь в см².",
               f"A triangle has base {base} cm and height {height} cm. What is its area, in square centimeters?", area,
               "Площадь треугольника — половина произведения основания и высоты.",
               f"S = {base} × {height} ÷ 2.",
               f"S = {area} см².", graph=triangle(base, height),
               followup="Основание и высота должны быть перпендикулярны. Их произведение даёт удвоенную площадь.")


def triangles_height(i, j):
    base, height = 2 * (i + 5), j + 7
    area = base * height // 2
    return row(f"Площадь треугольника {area} см², основание {base} см. Найдите высоту к этому основанию в см.",
               f"A triangle has area {area} square centimeters and base {base} centimeters. "
               "What is the height to that base, in centimeters?", height,
               "Выразите высоту из S = bh/2.",
               f"При удвоении площади получаем bh = {2*area}.",
               f"h = {2*area} ÷ {base} = {height} см.",
               followup="Умножь площадь на 2 и раздели на основание. Сверь единицы измерения.")


TRIPLES = [(3,4,5), (5,12,13), (8,15,17), (7,24,25), (20,21,29),
           (12,35,37), (9,40,41), (28,45,53), (11,60,61), (33,56,65)]


def triangles_pythagoras(i, j):
    a, b, c = (side * (j + 1) for side in TRIPLES[i])
    return row(f"Катеты прямоугольного треугольника равны {a} и {b}. Найдите гипотенузу.",
               f"A right triangle has legs of lengths {a} and {b}. What is the length of its hypotenuse?", c,
               "Сложите квадраты катетов, затем извлеките квадратный корень.",
               f"c² = {a}² + {b}² = {c*c}.",
               f"Длина положительна, поэтому c = √{c*c} = {c}.", graph=triangle(a, b),
               followup="Гипотенуза больше каждого катета. Это позволяет проверить выбранный положительный корень.")


def triangles_similarity(i, j):
    a, b, scale = i + 4, j + 4, 3
    return row(f"У первого треугольника отмечены стороны длиной {a} и {b}. У подобного ему треугольника "
               f"сторона, соответствующая первой отмеченной стороне, равна {scale*a}. "
               "Найдите длину стороны, соответствующей второй.",
               f"One triangle has two marked sides of lengths {a} and {b}. The side corresponding to "
               f"the first marked side in a similar triangle is {scale*a}. What is the length corresponding to the second?", scale*b,
               "Отношение соответствующих сторон одинаково.",
               f"Масштаб от первого ко второму равен {scale*a} ÷ {a} = {scale}.",
               f"Вторая сторона равна {b} × {scale} = {scale*b}.",
               followup="Сначала определи масштаб по известной паре сторон, затем примени тот же масштаб к искомой стороне.")


def powers_product(i, j):
    a, b = i + 2, j + 2
    return row(f"При каком n равенство x^{a} × x^{b} = x^n верно для всех x > 0?",
               f"For x > 0, what value of n makes x^{a} × x^{b} = x^n an identity?", a+b,
               "У степеней с одинаковыми основаниями сложите показатели.",
               f"x^{a} × x^{b} = x^({a}+{b}).",
               f"n = {a} + {b} = {a+b}.",
               followup="При записи ответа укажи показатель, а не значение всей степени.")


def powers_nested(i, j):
    a, b = i + 2, j + 2
    return row(f"Упростите (x^{a})^{b} при x > 0. Введите показатель результирующей степени x.",
               f"For x > 0, what is the exponent of x in the simplified form of (x^{a})^{b}?", a*b,
               "Степень степени означает повторное умножение целой скобки.",
               f"(x^{a})^{b} = x^({a}×{b}).",
               f"Показатель равен {a*b}.",
               followup="В (aᵐ)ⁿ показатель m повторяется n раз, поэтому надо перемножить показатели.")


def powers_negative(i, j):
    base, exponent = i + 2, j + 1
    return row(f"В равенстве {base}^(−{exponent}) = 1/n найдите n.",
               f"If {base}^(−{exponent}) = 1/n, what is n?", base**exponent,
               "Отрицательная степень даёт обратное число.",
               f"{base}^(−{exponent}) = 1/({base}^{exponent}).",
               f"n = {base}^{exponent} = {base**exponent}.",
               followup="Представь a⁻ⁿ как 1/aⁿ. Если требуется знаменатель, вычисли положительную степень основания.")


def powers_square_roots(i, j):
    a, b = i + 12, j + 2
    return row(f"Найдите точное значение √{a*a} − √{b*b}.",
               f"What is the exact value of √{a*a} − √{b*b}?", a-b,
               "Извлеките каждый квадратный корень отдельно.",
               f"√{a*a} = {a}, а √{b*b} = {b}.",
               f"Разность равна {a} − {b} = {a-b}.",
               followup="После извлечения корней выполни указанное действие. Арифметические корни неотрицательны.")


def quadratic_roots(i, j):
    left, right = i + 2, j + 13
    return row(f"Найдите больший корень уравнения (x − {left})(x − {right}) = 0.",
               f"What is the greater solution of (x − {left})(x − {right}) = 0?", right,
               "Произведение равно нулю, если хотя бы один множитель равен нулю.",
               f"Из первого множителя получаем x = {left}, из второго — x = {right}.",
               f"Наибольший корень — {right}.", graph=quad(1, -left-right, left*right),
               followup="Приравняй каждый множитель к нулю отдельно, затем выбери больший из полученных корней.")


def quadratic_vertex(i, j):
    h, c = i + 2, j + 3
    return row(f"При каком x функция y = x² − {2*h}x + {c} принимает наименьшее значение?",
               f"At what value of x does y = x² − {2*h}x + {c} reach its minimum?", h,
               "Выделите полный квадрат или используйте x вершины = −b/(2a).",
               f"x² − {2*h}x + {c} = (x − {h})² {signed(c-h*h)}.",
               f"Квадрат равен нулю при x = {h}.", graph=quad(1, -2*h, c),
               followup="Знак b в формуле −b/(2a) меняется. Проверь найденную абсциссу через ось симметрии.")


def quadratic_tangent(i, j):
    h, k = i + 2, j - 5
    return row(f"При каком c прямая y = c имеет ровно одну общую точку с y = (x − {h})² {signed(k)}?",
               f"For what value of c does the line y = c meet y = (x − {h})² {signed(k)} at exactly one point?", k,
               "Горизонтальная прямая касается параболы на высоте вершины.",
               f"Наименьшее значение функции достигается при x = {h}.",
               f"В этой точке y = {number(k)}, поэтому c = {number(k)}.", graph=quad(1, -2*h, h*h+k),
               followup="В записи y=(x−h)²+k квадрат обращается в ноль при x=h. Найди соответствующую ординату.")


def quadratic_rectangle(i, j):
    a, b = i + 2, j + 13
    side_sum, area = a + b, a * b
    return row(f"Периметр прямоугольника равен {2*side_sum}, а площадь равна {area}. "
               "Найдите длину большей стороны.",
               f"A rectangle has perimeter {2*side_sum} and area {area}. What is the length of its longer side?", b,
               "Если одна сторона равна x, то вторая равна половине периметра минус x.",
               f"Уравнение площади: x({side_sum} − x) = {area}.",
               f"Переносим всё влево: x² − {side_sum}x + {area} = 0.",
               f"(x − {a})(x − {b}) = 0. Большая сторона равна {b}.",
               followup="Для сторон u и v известны u+v=P/2 и uv=S. Найди обе положительные стороны и выбери большую.")


def exponential_value(i, j):
    initial, base = 5*(i+3), j+2
    return row(f"Число клеток задано моделью N(t) = {initial} × {base}^t. Сколько клеток при t = 3?",
               f"The number of cells is modeled by N(t) = {initial} × {base}^t. What is N(3)?", initial*base**3,
               "В формуле сначала найдите степень, затем умножьте.",
               f"{base}³ = {base**3}.",
               f"N(3) = {initial} × {base**3} = {initial*base**3}.",
               followup="Количество шагов — показатель степени множителя. Начальное значение соответствует нулю шагов.")


def exponential_rate(i, j):
    base, initial = i+2, 10*(j+2)
    next_amount = initial * base
    return row(f"Экспоненциальная последовательность начинается числами {initial}, {next_amount}. "
               "На какой множитель умножают число, чтобы получить следующее?",
               f"An exponential sequence starts with {initial}, {next_amount}. "
               "By what factor is each term multiplied to obtain the next?", base,
               "Найдите отношение второго значения к первому.",
               f"Коэффициент роста равен {next_amount}/{initial}.",
               f"Следующий член получают умножением на {base}.",
               followup="Если новое равно старому, умноженному на r, то r равно их отношению. Процент роста равен (r−1)·100.")


def exponential_time(i, j):
    initial, steps = 5*(2*i+1), j+2
    last = initial * 2**steps
    return row(f"Было {initial} бактерий. Популяция удваивается каждый час. "
               f"Через сколько часов в модели будет {last} бактерий?",
               f"A population starts at {initial} bacteria and doubles each hour. "
               f"After how many hours does the model predict {last} bacteria?", steps,
               "Разделите конечное количество на начальное и найдите показатель степени двойки.",
               f"{last}/{initial} = {2**steps} = 2^{steps}.",
               f"Количество удваивалось {steps} раз — по разу за час.",
               followup="Проверь последовательные степени двойки, пока отношение конечного количества к начальному не совпадёт.")


def exponential_decay(i, j):
    initial, percent = 10000*(i+1), 5*(j+1)
    factor_num = 100-percent
    last = initial*factor_num**2//10000
    return row(f"Цена оборудования {initial} ₸ и ежегодно падает на {percent}% от текущей цены. "
               "Какой она станет через два года?",
               f"Equipment worth {initial} tenge loses {percent}% of its current value each year. "
               "What is its value after two years, in tenge?", last,
               "Примените множитель уменьшения два раза.",
               f"Каждый год остаётся {factor_num}% текущей стоимости.",
               f"{initial} × ({factor_num}/100)² = {last} ₸.",
               followup="Если убрали p%, остаётся 1−p/100 исходного. Для двух шагов возведи множитель остатка в квадрат.")


def stats_mean(i, j):
    a, b = i + 2, 3*j + 20
    values = a, b, 2*a + 2
    return row(f"Найдите среднее арифметическое чисел {values[0]}, {values[1]} и {values[2]}.",
               f"What is the arithmetic mean of {values[0]}, {values[1]}, and {values[2]}?", sum(values)/3,
               "Сложите все значения и разделите сумму на их число.",
               f"Сумма равна {sum(values)}.",
               f"Среднее равно {sum(values)}/3.",
               followup="Количество наблюдений включает все повторы. Раздели сумму на это количество.")


def stats_missing(i, j):
    target, x = i + 12, j + 2
    y = target - 4
    missing = 3*target - x - y
    return row(f"Среднее арифметическое трёх чисел равно {target}. Два числа — {x} и {y}. Найдите третье.",
               f"The mean of three numbers is {target}. Two of the numbers are {x} and {y}. What is the third?", missing,
               "Из среднего и количества наблюдений найдите общую сумму.",
               f"Сумма равна 3 × {target} = {3*target}.",
               f"Третье число равно {3*target} − {x} − {y} = {missing}.",
               followup="Из полной суммы вычти сумму известных значений. Проверь среднее восстановленного набора.")


def stats_median(i, j):
    a, b = i + 4, j + 16
    values = b+2, a, b, 2, a+1
    return row(f"Найдите медиану набора: {', '.join(map(str, values))}.",
               f"What is the median of {', '.join(map(str, values))}?", a+1,
               "Отсортируйте значения и возьмите центральное.",
               f"По возрастанию: 2, {a}, {a+1}, {b}, {b+2}.",
               f"Третье из пяти значений равно {a+1}.",
               followup="Для нечётного количества нужен один центральный элемент. Одинаковые значения остаются отдельными наблюдениями.")


def stats_weighted(i, j):
    a, b = 10+i, 16+j
    return row(f"Два участника набрали по {a} баллов, ещё три — по {b}. Каков средний результат всех пяти?",
               f"Two participants each score {a}, and three each score {b}. What is the mean score of all five?", (2*a+3*b)/5,
               "Сначала найдите сумму всех пяти результатов с учётом повторений.",
               f"Сумма = 2 × {a} + 3 × {b} = {2*a+3*b}.",
               f"Среднее равно {2*a+3*b}/5.",
               followup="Сложи произведения каждого результата на его частоту, затем раздели на общее количество результатов.")


def probability_single(i, j):
    blue, white = i + 2, j + 2
    return row(f"В коробке {blue} синих и {white} белых шаров. "
               "Какова вероятность достать синий шар за один случайный выбор?",
               f"A box has {blue} blue marbles and {white} white marbles. "
               "What is the probability that one marble selected at random is blue?", blue/(blue+white),
               "Все шары равновероятны. Посчитайте число исходов каждого вида.",
               f"Подходящих исходов {blue}, всего {blue+white}.",
               f"Вероятность равна {blue}/{blue+white}.",
               followup="В знаменателе стоят все шары, в числителе — только подходящего цвета. Ответ должен лежать от 0 до 1.")


def probability_without_replacement(i, j):
    blue, white = i + 3, j + 3
    total = blue+white
    return row(f"В коробке {blue} синих и {white} белых шаров. Достаём два шара подряд без возврата. "
               "Какова вероятность, что оба синие?",
               f"A box has {blue} blue marbles and {white} white marbles. Two marbles are drawn without replacement. "
               "What is the probability that both are blue?", comb(blue,2)/comb(total,2),
               "После первого синего шара уменьшаются и число синих, и общее число шаров.",
               f"Первый синий с вероятностью {blue}/{total}, второй после него — {blue-1}/{total-1}.",
               f"Перемножаем: {blue*(blue-1)}/{total*(total-1)}.",
               followup="Вероятность двух последовательных синих равна вероятности первого, умноженной на условную вероятность второго.")


def probability_conditional(i, j):
    attended, submitted = i + j + 13, i + 2
    return row(f"Из {attended} учеников, посетивших кружок, {submitted} сдали задачу. "
               "Какова вероятность, что случайно выбранный из посетивших кружок ученик сдал задачу?",
               f"Of {attended} students who attended a club, {submitted} handed in a problem. "
               "What is the probability that a randomly selected attendee handed it in?", submitted/attended,
               "Условие уже ограничивает выбор учениками, которые посетили кружок.",
               f"Всего возможных вариантов {attended}, из них {submitted} удовлетворяют вопросу.",
               f"Искомая вероятность равна {submitted}/{attended}.",
               followup="В знаменателе используй размер группы, указанной после слова «если», а не всех участников.")


def probability_complement(i, j):
    blue, white = i + 3, j + 3
    total = blue+white
    return row(f"В коробке {blue} синих и {white} белых шаров. Выбираем шар, возвращаем его и выбираем ещё раз. "
               "Какова вероятность, что хотя бы один шар синий?",
               f"A box contains {blue} blue marbles and {white} white marbles. Two marbles are drawn with replacement. "
               "What is the probability that at least one is blue?", (total**2-white**2)/total**2,
               "Противоположное событие — оба раза достали белый шар.",
               f"Вероятность двух белых равна ({white}/{total})².",
               f"Вычитаем из 1: {total**2-white**2}/{total**2}.",
               followup="При возвращении состав коробки восстанавливается. Вероятность двух белых — квадрат доли белых.")


FAMILIES: dict[str, tuple[Callable, ...]] = {
    "linear": (linear_isolate, linear_brackets, linear_both_sides, linear_cost),
    "percent": (percent_of, percent_increase, percent_reverse, percent_change),
    "lines": (lines_slope, lines_intercept, lines_table, lines_rate),
    "systems": (systems_sum, systems_prices, systems_intersect, systems_infinite),
    "triangles": (triangles_area, triangles_height, triangles_pythagoras, triangles_similarity),
    "powers": (powers_product, powers_nested, powers_negative, powers_square_roots),
    "quadratics": (quadratic_roots, quadratic_vertex, quadratic_tangent, quadratic_rectangle),
    "exponential": (exponential_value, exponential_rate, exponential_time, exponential_decay),
    "statistics": (stats_mean, stats_missing, stats_median, stats_weighted),
    "probability": (probability_single, probability_without_replacement, probability_conditional, probability_complement),
}

PARAMETER_VALUES = 10
VARIANTS_PER_FAMILY = PARAMETER_VALUES ** 2
for entry in TOPICS:
    entry["variants"] = len(FAMILIES[entry["id"]]) * VARIANTS_PER_FAMILY
    entry["families"] = len(FAMILIES[entry["id"]])


def generate(topic_id: str, variant: int, lang: str = "ru") -> dict:
    """Return a reproducible exercise by topic and zero-based variant."""
    if lang not in {"ru", "en"}:
        raise ValueError("Unknown exercise language")
    families = FAMILIES.get(topic_id)
    if families is None:
        raise ValueError("Unknown topic")
    if type(variant) is not int or not 0 <= variant < len(families) * VARIANTS_PER_FAMILY:
        raise ValueError("Variant is outside the catalog")
    family_index, pair = divmod(variant, VARIANTS_PER_FAMILY)
    i, j = divmod(pair, PARAMETER_VALUES)
    family = families[family_index]
    exercise = family(i, j)
    prompt = exercise.pop(lang)
    exercise.pop("en" if lang == "ru" else "ru")
    return dict(exercise, prompt=prompt, family=family.__name__)
