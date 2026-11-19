"""Original English SAT transfer practice aligned to College Board's four domains."""
from fractions import Fraction

from .curriculum_extensions import material

TOPICS, FAMILIES, LEVELS_BY_TOPIC, GOAL_EVIDENCE = [], {}, {}, []
LEGACY_LESSONS = {}
SOURCE = "https://satsuite.collegeboard.org/sat/whats-on-the-test/math/types"


def task(prompt, answer, hints, *steps, response=None):
    if isinstance(answer, Fraction):
        answer = float(answer)
    result = {"ru":prompt,"en":prompt,"answer":answer,"hints":list(hints),"solution":list(steps)}
    if response:
        result["response"] = response
    return result


def equation(i,j):
    a,b,x = i+2,j+3,j-i
    return task(f"What value of x satisfies {a}x + {b} = {a*x+b}?",x,
                ("Убери постоянное слагаемое одинаковой операцией с обеих сторон.","После переноса раздели обе части на коэффициент при x."),
                f"{a}x={a*x+b}−{b}={a*x}.",f"x={a*x}/{a}={x}. Проверка возвращает правую часть.")


def system(i,j):
    x,y=i+1,j+2
    return task(f"The system x + y = {x+y} and 2x - y = {2*x-y} has solution (x, y). What is y?",y,
                ("Сложи уравнения, чтобы исключить y.","Найди x, затем подставь его в первое уравнение."),
                f"Сумма уравнений даёт 3x={3*x}, x={x}.",f"y={x+y}−{x}={y}.")


def linear_model(i,j):
    fee,rate,hours=20+5*i,j+2,i+j+3
    return task(f"A repair company charges a fixed fee of {fee} dollars plus {rate} dollars per hour. A customer pays {fee+rate*hours} dollars. How many hours were billed?",hours,
                ("Отдели фиксированную плату от почасовой части.","Раздели оставшуюся стоимость на цену одного часа."),
                f"Модель C={fee}+{rate}h.",f"{rate}h={rate*hours}, поэтому h={hours}.")


def equivalent(i,j):
    a,b=i+2,j+1
    options=[f"{a}x+{a*b}",f"{a}x+{b}",f"{a+b}x",f"{a}x-{a*b}"]
    order=[(n+i+j)%4 for n in range(4)]
    response={"kind":"choice","options":[{"value":chr(97+k),"label":options[n]} for k,n in enumerate(order)]}
    return task(f"Which expression is equivalent to {a}(x + {b})?",chr(97+order.index(0)),
                ("Используй распределительный закон.","Множитель перед скобками умножается на каждое слагаемое."),
                f"{a}(x+{b})={a}x+{a}·{b}.",f"Получаем {a}x+{a*b}; равенство верно при любом x.",response=response)


def coefficient(i,j):
    a,b=i+1,j+2
    return task(f"The expression (x + {a})(x + {b}) is equivalent to x² + bx + c. What is the value of b?",a+b,
                ("Коэффициент при x образуется из двух перекрёстных произведений.","Собери слагаемые ax и bx после раскрытия скобок."),
                f"(x+{a})(x+{b})=x²+({a}+{b})x+{a*b}.",f"Коэффициент b={a+b}. Буква b здесь обозначает искомый коэффициент.")


def rational_value(i,j):
    a,x=i+2,j+12
    return task(f"For x ≠ {a}, f(x) = (x² - {a*a})/(x - {a}). What is f({x})?",x+a,
                ("Разложи разность квадратов на множители.","Сократи общий множитель при указанном ограничении, затем подставь число."),
                f"x²−{a*a}=(x−{a})(x+{a}).",f"f(x)=x+{a} при x≠{a}, поэтому f({x})={x+a}.")


def positive_root(i,j):
    a,b=i+1,j+2
    return task(f"If x > 0 and x² + ({b-a})x - {a*b} = 0, what is x?",a,
                ("Найди два числа с нужным произведением и суммой.","После разложения проверь требование x>0."),
                f"Уравнение равносильно (x−{a})(x+{b})=0.",f"Корни {a} и −{b}. Условию x>0 удовлетворяет {a}.")


def quadratic_vertex(i,j):
    h,k=i-4,j+1
    return task(f"The function f is defined by f(x) = (x - ({h}))² + {k}. What is the minimum value of f(x)?",k,
                ("Квадрат действительного числа неотрицателен.","Найди значение выражения, когда квадрат равен нулю."),
                f"(x−({h}))²≥0 при любом x.",f"При x={h} достигается минимум f(x)={k}.")


def growth(i,j):
    initial,factor=i+2,j+2
    return task(f"A population starts at {initial} hundred and is multiplied by {factor} each year. How many hundreds are there after 3 years?",initial*factor**3,
                ("Множитель применяется один раз за каждый год.","Запиши начальное значение, умноженное на третью степень коэффициента."),
                f"Модель P(t)={initial}·{factor}^t.",f"P(3)={initial}·{factor}³={initial*factor**3} сотен.")


def percent(i,j):
    price,discount=100*(i+2),5*(j+1)
    answer=price*(100-discount)//100
    return task(f"An item costs {price} dollars before a {discount}% discount. What is its price, in dollars, after the discount?",answer,
                ("После скидки остаётся 100% минус процент скидки.","Умножь начальную цену на долю, которая остаётся."),
                f"Остаётся {100-discount}% цены.",f"{price}·{100-discount}/100={answer} долларов.")


def unit_rate(i,j):
    distance,time=i+10,j+2
    return task(f"A vehicle travels {distance*time} kilometers in {time} hours at a constant speed. How many kilometers does it travel in {i+j+1} hours?",distance*(i+j+1),
                ("Найди расстояние за один час.","Постоянная скорость позволяет умножить единичную скорость на новое время."),
                f"v={distance*time}/{time}={distance} км/ч.",f"d={distance}·{i+j+1}={distance*(i+j+1)} км.")


def scale_units(i,j):
    a,b=i+2,j+3
    return task(f"A rectangle is {a} meters long and {b} meters wide. What is its area in square centimeters?",a*b*10000,
                ("Найди площадь в квадратных метрах.","В одном квадратном метре 100² квадратных сантиметров."),
                f"S={a}·{b}={a*b} м².",f"{a*b}·10000={a*b*10000} см².")


def weighted_mean(i,j):
    a,b,n,m=i+2,j+7,i+1,j+2
    answer=Fraction(a*n+b*m,n+m)
    return task(f"A data set contains {n} values equal to {a} and {m} values equal to {b}. What is its mean?",answer,
                ("Сначала найди сумму всех значений с учётом количества повторов.","Раздели полную сумму на полное число значений."),
                f"Сумма {a}·{n}+{b}·{m}={a*n+b*m}.",f"Среднее равно {a*n+b*m}/{n+m}={answer}.")


def missing_mean(i,j):
    a,b,mean=i+1,j+2,i+j+4
    x=3*mean-a-b
    return task(f"The mean of the three numbers {a}, {b}, and x is {mean}. What is x?",x,
                ("Восстанови сумму из среднего и количества значений.","Вычти из полной суммы оба известных числа."),
                f"Сумма равна 3·{mean}={3*mean}.",f"x={3*mean}−{a}−{b}={x}.")


def linear_prediction(i,j):
    m,b,x=i+1,j+3,i+j+2
    return task(f"A model predicts a value y using y = {m}x + {b}. What value does the model predict when x = {x}?",m*x+b,
                ("Вопрос просит предсказание модели при данном входе.","Подставь x в правую часть уравнения и соблюдай порядок действий."),
                f"y={m}·{x}+{b}.",f"Получаем y={m*x+b}; это значение модели, а не утверждение о точном наблюдении.")


def probability_bag(i,j):
    red,blue=i+1,j+2
    return task(f"A bag contains {red} red balls and {blue} blue balls. One ball is selected at random. What is the probability that it is red?",Fraction(red,red+blue),
                ("Все отдельные шары равновероятны.","Раздели число подходящих шаров на число всех шаров."),
                f"Всего {red+blue} шаров, подходящих {red}.",f"P={red}/{red+blue}.")


def conditional(i,j):
    total,favorable=i+j+5,i+1
    return task(f"Among {total} students who play chess, {favorable} also play tennis. A student is selected at random from the chess players. What is the probability that this student also plays tennis?",Fraction(favorable,total),
                ("Выбор уже ограничен шахматистами.","В знаменателе должно стоять число учеников внутри заданного условия."),
                f"Пространство выбора состоит из {total} шахматистов.",f"Из них {favorable} играют в теннис, поэтому P={favorable}/{total}.")


def independent(i,j):
    a,b=i+2,j+2
    return task(f"Two independent events have probabilities 1/{a} and 1/{b}. What is the probability that both occur?",Fraction(1,a*b),
                ("В условии явно сказано, что события независимы.","Вероятность совместного наступления независимых событий равна произведению вероятностей."),
                f"P(A∩B)=P(A)P(B).",f"(1/{a})·(1/{b})=1/{a*b}.")


def triangle_area(i,j):
    base,height=2*(i+2),j+3
    return task(f"A triangle has a base of {base} and a perpendicular height of {height}. What is its area?",base*height//2,
                ("Высота уже дана перпендикулярно основанию.","Возьми половину произведения основания и высоты."),
                f"S=bh/2.",f"S={base}·{height}/2={base*height//2}.")


def similar_length(i,j):
    length,p,q=i+2,j+2,j+1
    return task(f"Two triangles are similar. The ratio of a side in the second triangle to its corresponding side in the first is {p}/{q}. A side in the first triangle has length {length*q}. What is the corresponding length in the second?",length*p,
                ("Следи за направлением отношения: второй треугольник к первому.","Умножь исходную длину на указанный линейный коэффициент."),
                f"Коэффициент подобия k={p}/{q}.",f"Искомая длина {length*q}·{p}/{q}={length*p}.")


def box_volume(i,j):
    a,b,c=i+2,j+3,i+j+1
    return task(f"A rectangular prism has side lengths {a}, {b}, and {c}. What is its volume?",a*b*c,
                ("Для прямоугольного параллелепипеда основание — прямоугольник.","Умножь площадь основания на высоту."),
                f"Sосн={a}·{b}={a*b}.",f"V={a*b}·{c}={a*b*c} кубических единиц.")


def radius_squared(i,j):
    h,r=i-4,j+2
    return task(f"The equation (x - ({h}))² + (y - {i+j+1})² = {r*r} represents a circle. What is its radius?",r,
                ("Справа в стандартном уравнении окружности стоит квадрат радиуса.","Возьми положительный квадратный корень из правой части."),
                f"Стандартная запись (x−h)²+(y−k)²=r².",f"r²={r*r}, поэтому r={r}.")


def circle_area(i,j):
    r,ratio=i+2,j+1
    return task(f"A circle has radius {r}. A sector occupies {ratio}/12 of the circle. Its area is kπ. What is k?",Fraction(r*r*ratio,12),
                ("Полная площадь круга равна πr².","Возьми указанную долю; ответом является коэффициент при π."),
                f"Sсектора=({ratio}/12)π·{r*r}.",f"Коэффициент k={r*r*ratio}/12={Fraction(r*r*ratio,12)}.")


def circle_arc(i,j):
    r,a=i+2,j+1
    return task(f"A circle has radius {r}. A central angle measures {15*a} degrees. The corresponding arc length is kπ. What is k?",Fraction(r*a,12),
                ("Угол составляет данную долю полного оборота 360°.","Умножь эту долю на длину окружности 2πr."),
                f"l=({15*a}/360)·2π·{r}.",f"Коэффициент k={Fraction(r*a,12)}.")


def right_ratio(i,j):
    p,q,c=((3,4,5),(5,12,13),(8,15,17),(7,24,25),(20,21,29),(12,35,37),(9,40,41),(28,45,53),(11,60,61),(16,63,65))[i]
    scale=j+1
    return task(f"In a right triangle, the legs have lengths {p*scale} and {q*scale}. Angle A is opposite the shorter leg. What is sin A?",Fraction(p,c),
                ("Найди гипотенузу по теореме Пифагора.","Синус равен отношению противолежащего катета к гипотенузе."),
                f"Гипотенуза равна √({p*scale}²+{q*scale}²)={c*scale}.",f"sin A={p*scale}/{c*scale}={Fraction(p,c)}.")


def right_length(i,j):
    scale=10*i+j+2
    return task(f"In right triangle ABC, angle C is 90 degrees, sin A = 3/5, and AB = {5*scale}. What is BC?",3*scale,
                ("AB лежит напротив прямого угла, это гипотенуза.","BC — противолежащий катет для угла A, поэтому BC=AB·sin A."),
                f"sin A=BC/AB.",f"BC={5*scale}·3/5={3*scale}.")


def complementary(i,j):
    numerator,denominator=i+1,i+j+3
    return task(f"Angles A and B are the acute angles of a right triangle. If sin A = {numerator}/{denominator}, what is cos B?",Fraction(numerator,denominator),
                ("Острые углы прямоугольного треугольника дополняют друг друга до 90°.","Используй равенство синуса угла и косинуса дополнительного угла."),
                f"B=90°−A, поэтому cos B=sin A.",f"cos B={numerator}/{denominator}.")


def add(identifier,grade,title,domain,intro,theory,families,prerequisites,checks):
    examples=[]
    for family,i,j in ((families[0],1,2),(families[1],2,3)):
        example=family(i,j)
        examples.append((example["en"],*example["solution"]))
    body=material(intro,theory,examples,
                  (("Перевожу условие, теряя нужную величину.","Выдели, что именно спрашивается и в каких единицах."),
                   ("Округляю до завершения вычислений.","Сначала получи точный результат, затем используй правила поля SAT.")),checks)
    TOPICS.append({"id":identifier,"grade":grade,"title":title,"section":"Применение в SAT",
                   "description":intro,"formula":"","lesson":body,"order":390+len(TOPICS),
                   "satReady":True,"satOnly":True,"satDomain":domain,"sat":domain,"source":SOURCE,
                   "prerequisites":list(prerequisites)})
    FAMILIES[identifier]=families
    LEVELS_BY_TOPIC[identifier]=("easy","medium","medium")


add("sat-linear",7,"SAT — линейные модели","algebra",
    "Перенеси линейные уравнения, системы и функции в англоязычные условия экзамена.",
    ("Equation означает уравнение, solution — решение, fixed fee — фиксированную плату, per hour — за час.",
     "Переведи условие в равенство и проверь единицы. У системы ответ должен удовлетворять обоим уравнениям.",
     "Вопрос может требовать только одну координату или параметр модели; сначала прочитай последнюю строку."),
    (equation,system,linear_model),("linear","g7-systems-full-pair"),
    (("Что означает fixed fee?","Плата, которая не зависит от количества часов или единиц."),("Как проверить пару решения системы?","Подставить обе координаты в оба уравнения.")))
add("sat-expressions",7,"SAT — равносильные выражения","advanced-math",
    "Используй преобразования выражений, чтобы узнавать равносильную запись и определять параметры.",
    ("Equivalent expressions равны при всех допустимых значениях переменной. Проверка одного числа не доказывает тождество.",
     "Раскрывая скобки, умножай каждый член. Собирай коэффициенты при одинаковых степенях.",
     "При сокращении дроби сохраняй исключённые значения исходного знаменателя."),
    (equivalent,coefficient,rational_value),("g7-polynomials","g7-algebraic-fractions"),
    (("Равносильны ли 2(x+3) и 2x+3?","Нет: распределение даёт 2x+6."),("Можно ли подставить запрещённое значение после сокращения?","Нет, исходное ограничение остаётся.")))
add("sat-nonlinear",9,"SAT — нелинейные функции","advanced-math",
    "Применяй квадратные модели, вершину параболы и мультипликативный рост в формате SAT.",
    ("Minimum value означает наименьшее значение функции, а не координату x, где оно достигается.",
     "Условие positive solution выбирает положительный корень из найденного множества.",
     "Рост в одинаковое число раз моделируется степенью: начальное значение умножается на коэффициент за каждый шаг."),
    (positive_root,quadratic_vertex,growth),("g8-discriminant","g8-complete-square","exponential"),
    (("Чему равен минимум (x−2)²+5?","5."),("Рост в 3 раза за шаг: каков множитель за два шага?","3²=9.")))
add("sat-ratios",7,"SAT — проценты и единицы","problem-solving-data",
    "Отработай проценты, единичные скорости и преобразование единиц в англоязычных задачах.",
    ("Discount означает скидку, constant speed — постоянную скорость, square centimeters — квадратные сантиметры.",
     "Доля процента равна p/100. После скидки p% остаётся множитель 1−p/100.",
     "При преобразовании площадей коэффициент длины возводят в квадрат, объёмов — в куб."),
    (percent,unit_rate,scale_units),("percent","g7-measurement-errors"),
    (("Какой множитель отвечает скидке 20%?","0,8."),("Сколько см² в 1 м²?","10 000.")))
add("sat-data",8,"SAT — анализ данных","problem-solving-data",
    "Находи средние, восстанавливай неизвестные данные и интерпретируй предсказание модели.",
    ("Mean — среднее арифметическое, data set — набор данных, predicts — предсказывает.",
     "При разном количестве повторений используй взвешенную сумму и общее количество значений.",
     "Предсказание модели вычисляется по её формуле и может отличаться от фактического наблюдения."),
    (weighted_mean,missing_mean,linear_prediction),("g7-frequencies","g8-frequency-variance"),
    (("Как восстановить сумму из среднего?","Умножить среднее на количество значений."),("Обязательно ли предсказание равно наблюдению?","Нет, модель может иметь погрешность.")))
add("sat-probability",9,"SAT — вероятность","problem-solving-data",
    "Решай задачи о случайном выборе, условном пространстве и независимых событиях.",
    ("At random означает случайный выбор, independent — независимые события, given — заданное условие.",
     "Условие меняет знаменатель вероятности: считай только объекты внутри выбранной группы.",
     "Произведение вероятностей совместного наступления применимо при независимости. Любая вероятность находится между 0 и 1."),
    (probability_bag,conditional,independent),("probability",),
    (("Что происходит с пространством исходов при условии?","Оно ограничивается исходами, удовлетворяющими условию."),("Какова вероятность обоих независимых событий?","Произведение их вероятностей.")))
TOPICS[-1]["answerRange"]=[0,1]
add("sat-geometry",8,"SAT — площади, объёмы и подобие","geometry-trigonometry",
    "Перенеси метрические формулы и подобие в задачи SAT с единицами измерения.",
    ("Perpendicular height — перпендикулярная высота, corresponding sides — соответствующие стороны, rectangular prism — прямоугольный параллелепипед.",
     "Линейные размеры подобных фигур меняются в k раз, площади — в k², объёмы — в k³.",
     "Для площади треугольника используй половину произведения основания и перпендикулярной высоты."),
    (triangle_area,similar_length,box_volume),("triangles","g8-areas"),
    (("При k=2 как меняется площадь?","В 4 раза."),("Что должно быть перпендикулярно основанию?","Используемая в формуле высота.")))
add("sat-circles",8,"SAT — окружность и её уравнение","geometry-trigonometry",
    "Работай с радиусом, уравнением окружности, площадями секторов и длинами дуг.",
    ("Radius — радиус, central angle — центральный угол, arc length — длина дуги, sector — сектор.",
     "В уравнении (x−h)²+(y−k)²=r² справа стоит квадрат радиуса.",
     "Площадь сектора и длина дуги составляют долю θ/360° от площади круга и длины окружности соответственно."),
    (radius_squared,circle_area,circle_arc),("g8-coordinate-geometry",),
    (("Если r²=49, каков радиус?","7."),("Какова доля круга при угле 90°?","1/4.")))
add("sat-right-triangles",8,"SAT — прямоугольный треугольник","geometry-trigonometry",
    "Используй теорему Пифагора, тригонометрические отношения и дополнительные острые углы.",
    ("Hypotenuse — гипотенуза, opposite — противолежащий, adjacent — прилежащий.",
     "Синус острого угла равен отношению противолежащего катета к гипотенузе, косинус — прилежащего к гипотенузе.",
     "Для дополнительных острых углов sin A=cos B. Сначала определи, где находится выбранный угол."),
    (right_ratio,right_length,complementary),("g8-right-trig",),
    (("Чему равен sin 30°?","1/2."),("Что находится напротив прямого угла?","Гипотенуза.")))

DOMAIN_PRACTICE={
    "algebra":("sat-linear",),
    "advanced-math":("sat-expressions","sat-nonlinear"),
    "problem-solving-data":("sat-ratios","sat-data","sat-probability"),
    "geometry-trigonometry":("sat-geometry","sat-circles","sat-right-triangles"),
}

# Lesson-to-practice links refer to a skill actually exercised by this bank.
# A domain label alone is too broad (e.g. a histogram should not lead to discounts).
SCHOOL_APPLICATIONS={
    "g7-statistical-plots":("sat-data",),
    "g8-histogram-construction":("sat-data",),
    "g7-course-powers":("sat-nonlinear","sat-geometry"),
    "g7-course-scientific":("sat-ratios",),
    **{f"g7-course-{slug}":("sat-expressions",) for slug in
       ("monomials","polynomials","factorization","rational-operations")},
    "g7-course-functions":("sat-linear",),
    "g7-course-statistics":("sat-data",),
    "g7-course-triangle-types":("sat-right-triangles",),
    "g7-course-right-triangles":("sat-right-triangles",),
    "g7-course-perpendiculars":("sat-geometry",),
    "g7-course-circle-loci":("sat-circles",),
    "g7-course-triangle-circles":("sat-circles",),
    **{f"g8-course-{slug}":("sat-nonlinear",) for slug in
       ("real-numbers","quadratic-forms","substituted-equations","quadratic-models")},
    "g8-course-statistics":("sat-data",),
    "g8-course-quadrilaterals":("sat-geometry",),
    "g8-course-proportional-constructions":("sat-geometry","sat-right-triangles"),
    "g8-course-triangle-centres":("sat-circles",),
    "g8-course-right-triangle":("sat-right-triangles",),
    "g8-course-areas":("sat-geometry",),
    "g8-course-coordinates":("sat-linear","sat-circles"),
    "g9-course-models":("sat-nonlinear",),
    "g9-course-probability":("sat-probability",),
    "g9-course-cyclic-quadrilaterals":("sat-circles",),
    "g9-course-regular-polygons":("sat-geometry","sat-circles"),
    "g9-course-centers":("sat-circles","sat-geometry"),
}
