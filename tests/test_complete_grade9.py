"""Independent, prompt-derived oracles for all ninth-grade completion tasks."""
import ast
import json
import math
import re
import unittest
from fractions import Fraction as Q

from backend import complete_grade9 as c


def tasks(family):
    for i in range(10):
        for j in range(10):
            yield family(i, j)


def pair(task):
    return tuple(Q(item) for item in task['answer'].split(';'))


def selected(task):
    return next(option['label'] for option in task['response']['options']
                if option['value'] == task['answer'])


def ordered(task):
    options = {option['value']: option['label'] for option in task['response']['options']}
    return [options[key] for key in task['answer'].split(',')]


def expression(text, **variables):
    """Tiny numeric AST oracle; deliberately independent of the application grader."""
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Q(str(node.value))
        if isinstance(node, ast.Name):
            return Q(variables[node.id])
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
            if isinstance(node.op, ast.Pow) and b.denominator == 1: return a**int(b)
        raise AssertionError(ast.dump(node))
    return visit(ast.parse(text.replace('^', '**'), mode='eval').body)


def trig_expression(text, t):
    text = text.replace('−', '-')
    def replace(match):
        name, coefficient, half = match.groups()
        argument = int(coefficient)*t/(2 if half else 1)
        return '('+repr(getattr(math, name)(argument))+')'
    text = re.sub(r'(sin|cos)\(\((-?\d+)\)t(/2)?\)', replace, text)
    text = re.sub(r'(\d|\))\(', r'\1*(', text)
    return float(expression(text))


class CompleteGrade9Tests(unittest.TestCase):
    def test_entire_registry_determinism_uniqueness_and_contracts(self):
        self.assertEqual(len(c.TOPICS), 15)
        self.assertEqual(sum(map(len, c.FAMILIES.values())), 47)
        topic_ids = {topic['id'] for topic in c.TOPICS}
        all_prompts = set()
        for topic in c.TOPICS:
            self.assertEqual(topic['grade'], 9)
            self.assertTrue(topic['id'].startswith('g9-course-'))
            self.assertTrue(topic['prerequisites'])
            self.assertNotIn(topic['id'], topic['prerequisites'])
            for field in ('theory', 'examples', 'mistakes', 'checks'):
                self.assertGreaterEqual(len(topic['lesson'][field]), 2)
            self.assertTrue(all(len(item['steps']) >= 3 for item in topic['lesson']['examples']))
            self.assertEqual(len(c.FAMILIES[topic['id']]), len(c.LEVELS_BY_TOPIC[topic['id']]))
            self.assertLessEqual(set(topic['satSkills']),
                                 {'algebra', 'advanced-math', 'problem-solving-data', 'geometry-trigonometry'})
            for family in c.FAMILIES[topic['id']]:
                local = set()
                for i in range(10):
                    for j in range(10):
                        task = family(i, j)
                        self.assertEqual(task, family(i, j))
                        json.dumps(task, allow_nan=False)
                        self.assertNotIn(task['ru'], all_prompts, (family.__name__, i, j))
                        all_prompts.add(task['ru'])
                        local.add(task['ru'])
                        self.assertEqual(len(task['hints']), 2)
                        self.assertNotEqual(*task['hints'])
                        self.assertGreaterEqual(len(task['solution']), 2)
                        self.assertNotIn(task['hints'][1], task['solution'])
                        response = task.get('response', {})
                        if response.get('kind') in ('choice', 'sequence'):
                            labels = [option['label'] for option in response['options']]
                            self.assertEqual(len(labels), len(set(labels)))
                            keys = [option['value'] for option in response['options']]
                            self.assertEqual(len(keys), len(set(keys)))
                        if response.get('kind') == 'expression':
                            self.assertEqual(response['form'], 'expanded')
                            self.assertTrue(response['variables'])
                        if response.get('kind') == 'pair':
                            self.assertEqual(len(pair(task)), 2)
                self.assertEqual(len(local), 100)
        self.assertEqual(len(all_prompts), 4700)
        # Dependencies in the newly introduced subgraph must be acyclic.
        graph = {topic['id']: [item for item in topic['prerequisites'] if item in topic_ids]
                 for topic in c.TOPICS}
        def visit(node, trail):
            self.assertNotIn(node, trail)
            for dependency in graph[node]:
                visit(dependency, trail | {node})
        for node in graph:
            visit(node, set())

    def test_every_previously_absent_ninth_grade_goal_has_actual_material(self):
        absent = {
            ('algebra', '9.4.2.1'), ('algebra', '9.2.2.4'), ('algebra', '9.2.4.4'),
            ('algebra', '9.2.4.7'), ('algebra', '9.3.2.2'),
            *(('geometry', code) for code in ('9.1.2.1', '9.1.2.2', '9.1.2.3',
              '9.1.2.4', '9.1.2.5', '9.1.2.6', '9.1.3.8', '9.1.4.12', '9.1.4.16', '9.1.4.18')),
        }
        evidence = {(item['subject'], item['code']) for item in c.GOAL_EVIDENCE}
        self.assertLessEqual(absent, evidence)
        for item in c.GOAL_EVIDENCE:
            self.assertIn(item['topic'], c.FAMILIES)
            self.assertIn(item['status'], ('F', 'P', 'T'))
            if item['code'] in ('9.1.2.3', '9.1.4.12') and item['subject'] == 'geometry':
                self.assertNotEqual(item['status'], 'F')

    def test_nonlinear_models_require_all_values(self):
        for task in tasks(c.rectangle_model):
            perimeter, area = map(int, re.search(r'периметр (\d+) м и площадь (\d+)', task['ru']).groups())
            a, b = pair(task)
            self.assertGreater(a, b)
            self.assertGreater(b, 0)
            self.assertEqual(2*(a+b), perimeter)
            self.assertEqual(a*b, area)
        for task in tasks(c.positive_numbers):
            product, total = map(int, re.search(r'равно (\d+), сумма равна (\d+)', task['ru']).groups())
            a, b = pair(task)
            self.assertEqual(a+b, total)
            self.assertEqual(a*b, product)
            self.assertTrue(0 < a < b)
        for task in tasks(c.text_equation):
            gap, area = map(int, re.search(r'на (\d+) м.*?площадь (\d+)', task['ru']).groups())
            for x in (-3, 0, 2, 7):
                self.assertEqual(expression(task['answer'], x=x), x*(x+gap)-area)

    def test_entire_nonlinear_regions_and_degree_after_cancellation(self):
        for task in tasks(c.parabola_region):
            a, top = map(int, re.search(r'y≥x²−(\d+), y≤(\d+)', task['ru']).groups())
            bound, lower, upper = map(int, re.search(r'√(\d+).*?x²−(\d+)≤y≤(\d+)', selected(task)).groups())
            self.assertEqual(bound, a+top)
            self.assertEqual((lower, upper), (a, top))
            for x in (0, math.sqrt(bound), -math.sqrt(bound)):
                self.assertLessEqual(x*x-a, top+1e-10)
            self.assertGreater((math.sqrt(bound)+1)**2-a, top)
        for task in tasks(c.disk_halfplane):
            h, squared = map(int, re.search(r'\(x−\((-?\d+)\)\)²\+y²≤(\d+)', task['ru']).groups())
            self.assertEqual(selected(task), f'(x−({h}))²+y²≤{squared} и x≥{h}')
            self.assertGreater(squared, 0)
        for task in tasks(c.system_degree):
            nonlinear = 'xy' in task['ru']
            self.assertEqual(selected(task).startswith('Нелинейное'), nonlinear)

    def test_counting_and_full_binomial(self):
        for task in tasks(c.disjoint_count):
            a, b = map(int, re.search(r'из (\d+) математических.*?из (\d+) технических', task['ru']).groups())
            self.assertEqual(task['answer'], len(list(range(a))+list(range(b))))
        for task in tasks(c.factorial_ratio):
            n, m = map(int, re.search(r'0! \+ (\d+)!/(\d+)!', task['ru']).groups())
            self.assertGreaterEqual(m, 0)
            self.assertEqual(task['answer'], 1+math.prod(range(m+1, n+1)))
            self.assertIsInstance(task['answer'], int)
            self.assertLess(task['answer'], 2**53)
        for task in tasks(c.binomial_full):
            a, b = map(int, re.search(r'\((\d+)x\+(\d+)\)³', task['ru']).groups())
            for x in (-4, -1, 0, 2, 3):
                self.assertEqual(expression(task['answer'], x=x), (a*x+b)**3)

    def test_sequence_formula_classification_and_both_neighbor_properties(self):
        for task in tasks(c.sequence_formula):
            a, b = map(int, re.search(r'умножить на (\d+), затем прибавить (\d+)', task['ru']).groups())
            for n in (1, 2, 10, 50):
                self.assertEqual(expression(task['answer'], n=n), a*n*n+b)
            self.assertEqual(task['response']['variables'], ['n'])
        for task in tasks(c.progression_classify):
            values = list(map(Q, re.search(r'Первые четыре члена: ([\d, ]+)\.', task['ru']).group(1).split(',')))
            formula = re.search(r'a_n=(.*?) при n=', task['ru']).group(1)
            at = lambda n: expression(formula, n=n)
            self.assertEqual([at(n) for n in range(1,5)],values)
            differences = {b-a for a, b in zip(values, values[1:])}
            ratios = {b/a for a, b in zip(values, values[1:])}
            expected = ('Арифметическая прогрессия' if len(differences) == 1 else
                        'Геометрическая прогрессия' if len(ratios) == 1 else 'Ни одна из этих прогрессий')
            self.assertEqual(selected(task), expected)
            if expected == 'Арифметическая прогрессия':
                self.assertEqual(at(101)-at(100), values[1]-values[0])
            elif expected == 'Геометрическая прогрессия':
                self.assertEqual(at(21)/at(20), values[1]/values[0])
        for task in tasks(c.neighbor_properties):
            a4, a6, b4, b6 = map(int, re.search(r'a₄=(\d+) и a₆=(\d+).*?b₄=(\d+), b₆=(\d+)', task['ru']).groups())
            a5, b5 = pair(task)
            self.assertEqual(2*a5, a4+a6)
            self.assertEqual(b5*b5, b4*b6)
            self.assertGreater(b5, 0)

    def test_radians_coordinates_and_cotangent(self):
        for task in tasks(c.radians_back):
            n, d = map(int, re.search(r'\((\d+)/(\d+)\)π', task['ru']).groups())
            self.assertAlmostEqual(task['answer']*math.pi/180, n*math.pi/d)
        for task in tasks(c.unit_coordinates):
            u, v = map(int, re.search(r'cos α=\((\d+)²−(\d+)²\)', task['ru']).groups())
            x, y = pair(task)
            self.assertEqual(x*x+y*y, 1)
            self.assertEqual(x, Q(u*u-v*v, u*u+v*v))
            self.assertEqual(y, Q(2*u*v, u*u+v*v))
        for task in tasks(c.cotangent_value):
            n, d = map(int, re.search(r'tan α=(\d+)/(\d+)', task['ru']).groups())
            self.assertAlmostEqual(task['answer']*n, d)

    def test_reduction_and_half_angle_numerically(self):
        for family, name in ((c.reduction_sine, 'sin'), (c.reduction_cosine, 'cos')):
            for task in tasks(family):
                coefficient, angle = map(int, re.search(r'(\d+)·'+name+r'\(\((\d+)\)π', task['ru']).groups())
                sign, target_coefficient, target_name = re.fullmatch(r'(−?)(\d+)·(sin|cos) α', selected(task)).groups()
                for alpha in (-2.1, -0.4, 0, 0.8, 2.7):
                    argument = angle*math.pi-alpha if name == 'sin' else angle*math.pi/2+alpha
                    actual = (-1 if sign else 1)*int(target_coefficient)*getattr(math, target_name)(alpha)
                    self.assertAlmostEqual(coefficient*getattr(math, name)(argument), actual, places=10)
        for task in tasks(c.half_angle):
            n, d = map(int, re.search(r'cos α=(\d+)/(\d+)', task['ru']).groups())
            sine_squared, cosine_squared = pair(task)
            alpha = math.acos(n/d)
            self.assertAlmostEqual(float(sine_squared), math.sin(alpha/2)**2)
            self.assertAlmostEqual(float(cosine_squared), math.cos(alpha/2)**2)
            self.assertEqual(sine_squared+cosine_squared, 1)

    def test_sum_product_identities_on_multiple_arguments(self):
        for family in (c.sum_to_product, c.difference_to_product, c.product_to_sum):
            for task in tasks(family):
                a, b = map(int, re.findall(r'(?:sin|cos)\((\d+)t\)', task['ru']))
                for t in (-0.73, -0.11, 0.17, 0.44, 1.31):
                    actual = trig_expression(selected(task), t)
                    expected = (math.sin(a*t)+math.sin(b*t) if family is c.sum_to_product else
                                math.cos(a*t)-math.cos(b*t) if family is c.difference_to_product else
                                2*math.sin(a*t)*math.cos(b*t))
                    self.assertAlmostEqual(actual, expected, places=10)

    def test_probability_uses_fixed_elementary_outcomes_and_valid_areas(self):
        for task in tasks(c.event_types):
            n = int(re.search(r'от 1 до (\d+)', task['ru']).group(1))
            event = re.search(r'«(.*?)»', task['ru']).group(1)
            if 'диапазона' in event:
                count = n
            else:
                value = int(re.search(r'число (\d+)', event).group(1))
                count = int(1 <= value <= n)
            expected = 'Достоверное' if count == n else 'Невозможное' if not count else 'Случайное'
            self.assertEqual(selected(task), expected)
        for task in tasks(c.elementary_events):
            a, b = map(int, re.search(r'с (\d+) красными и (\d+) синими', task['ru']).groups())
            label = selected(task)
            self.assertRegex(label, r'^Выбран шар с номером \d+$')
            number = int(re.search(r'\d+', label).group())
            self.assertTrue(1 <= number <= a+b)
            self.assertTrue(a > 1 and b > 1)
        for task in tasks(c.empirical_geometric):
            n, success, side, a, b = map(int, re.search(r'В (\d+) .*?произошло (\d+) раз.*?стороной (\d+).*?стороны (\d+) и (\d+)', task['ru']).groups())
            frequency, probability = pair(task)
            self.assertEqual(frequency*n, success)
            self.assertEqual(probability*side*side, a*b)
            self.assertTrue(0 < a <= side and 0 < b <= side)
            self.assertTrue(0 < frequency < 1 and 0 < probability < 1)

    def test_cyclic_and_tangential_geometry_has_realizable_data(self):
        for task in tasks(c.cyclic_angles):
            a, b = map(int, re.search(r'∠A=(\d+)°, ∠B=(\d+)°', task['ru']).groups())
            x, y = pair(task)
            self.assertEqual(a+x, 180)
            self.assertEqual(b+y, 180)
            self.assertTrue(all(0 < angle < 180 for angle in (a, b, x, y)))
        for task in tasks(c.tangential_sides):
            a, b, d = map(int, re.search(r'AB=(\d+), BC=(\d+), CD=(\d+)', task['ru']).groups())
            e = task['answer']
            self.assertEqual(a+d, b+e)
            self.assertTrue(all(side > 0 and 2*side < a+b+d+e for side in (a, b, d, e)))
        for task in tasks(c.tangent_chord):
            a, b = map(int, re.search(r'AC=(\d+)° и CB=(\d+)°', task['ru']).groups())
            self.assertLess(a+b, 180)
            self.assertEqual(2*task['answer'], a+b)

    def test_regular_polygons_and_symmetry(self):
        for task in tasks(c.regular_angles):
            n, side = map(int, re.search(r'правильного (\d+)-угольника сторона равна (\d+)', task['ru']).groups())
            perimeter, angle = pair(task)
            self.assertEqual(perimeter/n, side)
            self.assertEqual(n*angle, 180*(n-2))
            self.assertTrue(0 < angle < 180)
        for task in tasks(c.square_radii):
            side, count = map(int, re.search(r'равна (\d+).*?площадь (\d+)', task['ru']).groups())
            radius_squared, area = pair(task)
            self.assertEqual(4*radius_squared, 2*side*side)
            self.assertEqual(area, count*side*side)
        for task in tasks(c.polygon_symmetry):
            n, count = map(int, re.search(r'правильного (\d+)-угольника.*?выполните (\d+) подряд', task['ru']).groups())
            axes, angle = pair(task)
            self.assertEqual(axes, n)
            self.assertEqual(angle*n, 360*count)

    def test_medians_triangle_radii_and_tangential_area(self):
        for task in tasks(c.median_center):
            am, bn = map(int, re.search(r'AM=(\d+), BN=(\d+)', task['ru']).groups())
            ag, gn = pair(task)
            self.assertEqual(3*ag, 2*am)
            self.assertEqual(3*gn, bn)
        for task in tasks(c.triangle_radii):
            count, a, b, d = map(int, re.search(r'из (\d+) .*?стороны (\d+),(\d+),(\d+)', task['ru']).groups())
            r_sum, radius_sum = pair(task)
            self.assertEqual(a*a+b*b, d*d)
            self.assertLess(d, a+b)
            area = Q(a*b, 2)
            semi = Q(a+b+d, 2)
            self.assertEqual(r_sum*semi, count*area)
            self.assertEqual(radius_sum*4*area, count*a*b*d)
        for task in tasks(c.tangential_area):
            r, p = map(int, re.search(r'радиуса (\d+).*?полупериметр (\d+)', task['ru']).groups())
            self.assertEqual(task['answer'], r*p)
            # These data admit a tangential rhombus: p >= 4r.
            self.assertGreaterEqual(p, 4*r)

    def test_vectors_include_zero_exception_and_respect_gram_matrix(self):
        for task in tasks(c.vector_angle):
            ax, ay, bx, by = map(int, re.search(r'u=\((-?\d+);(-?\d+)\), v=\((-?\d+);(-?\d+)\)', task['ru']).groups())
            norm_a, norm_b = math.hypot(ax, ay), math.hypot(bx, by)
            self.assertGreater(norm_a*norm_b, 0)
            cosine = max(-1, min(1, (ax*bx+ay*by)/(norm_a*norm_b)))
            self.assertAlmostEqual(task['answer'], math.degrees(math.acos(cosine)))
        for task in tasks(c.vector_length):
            x, y = map(int, re.search(r'вектора \((-?\d+);(-?\d+)\)', task['ru']).groups())
            self.assertEqual(task['answer']**2, x*x+y*y)
            self.assertGreaterEqual(task['answer'], 0)
        for task in tasks(c.vector_distributive):
            a, b = map(int, re.search(r'\((\d+)u\+v\)·\(u−(\d+)v\)', task['ru']).groups())
            for x in (Q(4, 3), 2, 5):
                # Construct actual Euclidean vectors having the required Gram matrix.
                u = (math.sqrt(x), 0)
                v = (2/math.sqrt(x), math.sqrt(max(0, 3-4/x)))
                left = (a*u[0]+v[0], a*u[1]+v[1])
                right = (u[0]-b*v[0], u[1]-b*v[1])
                self.assertAlmostEqual(float(expression(task['answer'], x=x)), sum(p*q for p, q in zip(left, right)))
        for task in tasks(c.vector_kinds):
            a, b = map(int, re.search(r'v=\((\d+);(\d+)\)', task['ru']).groups())
            representation = re.search(r'u=(.*?)\.', task['ru']).group(1)
            norm = 0 if representation == '0·v' else 1 if representation.startswith('v/√') else 2*math.hypot(a, b)
            expected = 'Нулевой' if norm == 0 else 'Единичный' if norm == 1 else 'Ненулевой, но не единичный'
            self.assertEqual(selected(task), expected)

    def test_similarity_bisector_and_entire_homothety_coordinates(self):
        for task in tasks(c.angle_bisector):
            a, b, bc = map(int, re.search(r'AB:AC=(\d+):(\d+), BC=(\d+)', task['ru']).groups())
            bd, dc = pair(task)
            self.assertEqual(bd+dc, bc)
            self.assertEqual(bd*b, dc*a)
            self.assertTrue(bd > 0 and dc > 0)
            # One realizable set of side lengths is AB=3a, AC=3b, BC=2(a+b).
            # Highly unequal ratios may require a different common scale, always available.
            lower, upper = Q(bc, a+b), Q(bc, abs(a-b)) if a != b else None
            self.assertTrue(upper is None or lower < upper)
        for task in tasks(c.homothety_coordinates):
            k, x, y = map(int, re.search(r'k=(-?\d+).*?A=\((\d+);(\d+)\)', task['ru']).groups())
            ax, ay = pair(task)
            self.assertEqual((ax, ay), (k*x, k*y))
            self.assertLess(k, 0)
        for task in tasks(c.similarity_choice):
            a, b, d, p, q, r = map(int, re.search(r'равны (\d+),(\d+),(\d+) и (\d+),(\d+),(\d+)', task['ru']).groups())
            self.assertLess(max(a, b, d)*2, a+b+d)
            self.assertEqual(Q(p, a), Q(q, b))
            self.assertEqual(Q(q, b), Q(r, d))
            self.assertIn('Три пары соответствующих сторон', selected(task))

    def test_construction_dependencies_full_images_and_rotation_composition(self):
        for task in tasks(c.square_construction):
            steps = ordered(task)
            self.assertTrue(steps[0].startswith('Строим перпендикуляры'))
            self.assertIn('из A', steps[1])
            self.assertIn('из B', steps[2])
            self.assertTrue(steps[3].startswith('Соединяем'))
            self.assertIn('AD перед BC', task['ru'])
        for task in tasks(c.pentagon_construction):
            steps = ordered(task)
            self.assertIn('середину M', steps[0])
            self.assertIn('центром M', steps[1])
            self.assertIn('пересечение', steps[2])
            self.assertIn('пять раз', steps[3])
            radius = int(re.search(r'радиуса (\d+)', task['ru']).group(1))
            op = radius*(math.sqrt(5)-1)/2
            chord = math.hypot(radius, op)
            self.assertAlmostEqual(chord, 2*radius*math.sin(math.pi/5))
        for task in tasks(c.transform_triangle):
            source = [tuple(map(int, point)) for point in re.findall(r'[ABC]\((\d+);(\d+)\)', task['ru'])]
            target = [tuple(map(int, point)) for point in re.findall(r'[ABC]′\((-?\d+);(-?\d+)\)', selected(task).replace('−', '-'))]
            self.assertEqual(target, [(x, -y) for x, y in source])
            self.assertEqual(len(source), 3)
            self.assertNotEqual(source[0], source[1])
        for task in tasks(c.polygon_rotate):
            n, count = map(int, re.search(r'Правильный (\d+)-угольник.*?центра (\d+) раз', task['ru']).groups())
            self.assertEqual(task['answer'], count % n)
            self.assertTrue(0 <= task['answer'] < n)

    def test_trig_domains_ranges_least_periods_parity_and_monotonicity(self):
        for task in tasks(c.trig_domain_range):
            amplitude, name, k = re.search(r'y=(\d+)·(sin|cos|tan|cot)\((\d+)x\)', task['ru']).groups()
            amplitude, k = int(amplitude), int(k)
            answer = selected(task)
            if name in ('sin', 'cos'):
                self.assertEqual(answer, f'Область R; значения [−{amplitude};{amplitude}]')
            else:
                excluded = f'π/(2·{k})+πn/{k}' if name == 'tan' else f'πn/{k}'
                self.assertEqual(answer, f'Все x, кроме {excluded}, n∈Z; значения R')
                for n in (-2, 0, 3):
                    x = (math.pi/2+n*math.pi)/k if name == 'tan' else n*math.pi/k
                    denominator = math.cos(k*x) if name == 'tan' else math.sin(k*x)
                    self.assertAlmostEqual(denominator, 0)
        for task in tasks(c.trig_period_parity):
            amplitude, name, k = re.search(r'y=(\d+)·(sin|cos|tan|cot)\((\d+)x\)', task['ru']).groups()
            n, d, parity = re.fullmatch(r'T=(\d+)π/(\d+); (чётная|нечётная)', selected(task)).groups()
            period = Q(int(n), int(d))
            self.assertEqual(period, Q(2 if name in ('sin', 'cos') else 1, int(k)))
            self.assertEqual(parity == 'чётная', name == 'cos')
        functions = {'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                     'cot': lambda x: 1/math.tan(x)}
        for task in tasks(c.trig_sign_monotonic):
            left, right, amplitude, name = re.search(r'\((\d+)π/2;(\d+)π/2\).*?y=(\d+)·(sin|cos|tan|cot)', task['ru']).groups()
            left, right, amplitude = int(left)*math.pi/2, int(right)*math.pi/2, int(amplitude)
            values = [amplitude*functions[name](left+(right-left)*t) for t in (0.2, 0.5, 0.8)]
            expected = ('положительна' if values[1] > 0 else 'отрицательна')
            expected += ' и '+('возрастает' if values[0] < values[2] else 'убывает')
            self.assertEqual(selected(task), expected)


if __name__ == '__main__':
    unittest.main()
