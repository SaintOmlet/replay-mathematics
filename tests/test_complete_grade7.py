"""Independent mathematical checks for original seventh-grade completion tasks."""

import ast
from collections import Counter
from fractions import Fraction as Q
import json
from math import cos, radians, sin
import re
import unittest

from backend import complete_grade7 as c
from backend.grading import structured_matches
from backend.solution_sets import contains, parse_intervals


def tasks(family):
    for i in range(10):
        for j in range(10):
            yield family(i,j)


def chosen(question):
    return next(option['label'] for option in question['response']['options']
                if option['value']==question['answer'])


def pair(question):
    return tuple(Q(value) for value in question['answer'].split(';'))


def evaluate(text, **variables):
    """Independent exact arithmetic at selected points, without Python eval."""
    def visit(node):
        if isinstance(node,ast.Constant):
            return Q(str(node.value))
        if isinstance(node,ast.Name):
            return Q(variables[node.id])
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            return -visit(node.operand) if isinstance(node.op,ast.USub) else visit(node.operand)
        if isinstance(node,ast.BinOp):
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add): return a+b
            if isinstance(node.op,ast.Sub): return a-b
            if isinstance(node.op,ast.Mult): return a*b
            if isinstance(node.op,ast.Div): return a/b
            if isinstance(node.op,ast.Pow) and b.denominator==1: return a**int(b)
        raise AssertionError(ast.dump(node))
    return visit(ast.parse(text.replace('^','**'),mode='eval').body)


class CompleteGrade7Tests(unittest.TestCase):
    def test_material_and_all_4900_generated_questions(self):
        self.assertEqual(len(c.TOPICS),14)
        total=0
        for topic in c.TOPICS:
            self.assertEqual(topic['grade'],7)
            self.assertTrue(topic['id'].startswith('g7-course-'))
            self.assertFalse(topic.get('satReady',False))
            lesson=topic['lesson']
            self.assertTrue(lesson['intro'])
            for field in ('theory','examples','mistakes','checks'):
                self.assertGreaterEqual(len(lesson[field]),2)
            self.assertTrue(all(len(example['steps'])>=2 for example in lesson['examples']))
            families=c.FAMILIES[topic['id']]
            self.assertGreaterEqual(len(families),3)
            self.assertEqual(len(c.LEVELS_BY_TOPIC[topic['id']]),len(families))
            seen=set()
            for family in families:
                for i in range(10):
                    for j in range(10):
                        with self.subTest(family=family.__name__,i=i,j=j):
                            question=family(i,j)
                            self.assertEqual(question,family(i,j))
                            json.dumps(question,allow_nan=False)
                            self.assertNotIn(question['ru'],seen)
                            seen.add(question['ru'])
                            self.assertEqual(len(question['hints']),2)
                            self.assertNotEqual(*question['hints'])
                            self.assertNotIn(question['hints'][1],question['solution'])
                            self.assertGreaterEqual(len(question['solution']),2)
                            if question.get('response'):
                                self.assertTrue(structured_matches(str(question['answer']),question['response'],question['answer']))
                            if question.get('response',{}).get('kind')=='choice':
                                labels=[option['label'] for option in question['response']['options']]
                                self.assertEqual(len(labels),len(set(labels)))
                            total+=1
            self.assertEqual(len(seen),100*len(families))
        self.assertEqual(total,4900)

    def test_prerequisites_are_existing_grade7_and_acyclic(self):
        topics={topic['id']:topic for topic in c.TOPICS}
        def walk(topic_id,path):
            self.assertNotIn(topic_id,path)
            for prerequisite in topics[topic_id]['prerequisites']:
                self.assertIn(prerequisite,topics)
                self.assertLessEqual(topics[prerequisite]['grade'],7)
                walk(prerequisite,path+(topic_id,))
        for topic in topics:
            walk(topic,())

    def test_all_originally_absent_grade7_goals_have_honest_evidence(self):
        absent={
            'algebra': '7.1.2.2 7.4.2.3 7.2.3.1 7.1.2.9 7.3.3.3',
            'geometry': '7.1.1.1 7.1.1.2 7.1.1.6 7.1.1.8 7.1.1.11 7.1.1.13 7.1.1.15 7.1.1.20 7.1.1.24 7.1.1.25 7.1.1.27 7.1.1.30 7.1.1.31 7.1.2.1 7.1.2.2 7.1.2.8 7.1.2.9 7.1.2.10',
        }
        evidence={(item['subject'],item['code']):item for item in c.GOAL_EVIDENCE}
        for subject,codes in absent.items():
            for code in codes.split():
                item=evidence[(subject,code)]
                self.assertIn(item['status'],('F','P'))
                self.assertTrue(item['evidence'])
                self.assertIn(item['topic'],c.FAMILIES)
        self.assertTrue(all(item['status']=='P' for item in c.GOAL_EVIDENCE if item['subject']=='geometry'))
        self.assertEqual(evidence[('algebra','7.3.3.3')]['status'],'P')

    def test_remainders_scaling_and_multiplicative_sequence(self):
        for question in tasks(c.last_digit):
            base,exponent=map(int,re.search(r'числа (\d+)\^(\d+)',question['ru']).groups())
            # Successive multiplication is independent of the generator's pow call.
            remainder=1
            for _ in range(exponent): remainder=remainder*base%10
            self.assertEqual(question['answer'],remainder)
        for question in tasks(c.scaling_pair):
            side,factor=map(int,re.search(r'равны (\d+) см.*?в (\d+) раз',question['ru']).groups())
            area,volume=pair(question)
            self.assertEqual(area/side**2,factor**2)
            self.assertEqual(volume/side**3,factor**3)
        for question in tasks(c.power_sequence):
            a,b,d=map(int,re.search(r': (\d+), (\d+), (\d+),',question['ru']).groups())
            self.assertEqual(Q(b,a),Q(d,b))
            self.assertEqual(question['answer'],d*Q(b,a))

    def test_zero_power_domain_excludes_exactly_the_zero_base(self):
        for question in tasks(c.zero_power_domain):
            a,b=map(int,re.search(r'\((\d+)x\+\((-?\d+)\)\)\^0',question['ru']).groups())
            domain=parse_intervals(question['answer'])
            hole=Q(-b,a)
            self.assertFalse(contains(domain,hole))
            self.assertTrue(contains(domain,hole-Q(1,1000)))
            self.assertTrue(contains(domain,hole+Q(1,1000)))
            self.assertFalse(structured_matches('(-inf;+inf)',question['response'],question['answer']))

    def test_scientific_notation_and_cubic_unit_conversion(self):
        for question in tasks(c.scientific_sum):
            a,e,b,f=re.search(r'\(([-\d/]+)·10\^(-?\d+)\)\+\(([-\d/]+)·10\^(-?\d+)\)',question['ru']).groups()
            coefficient,exponent=pair(question)
            self.assertEqual(exponent.denominator,1)
            self.assertTrue(1<=coefficient<10)
            self.assertEqual(coefficient*Q(10)**int(exponent),Q(a)*Q(10)**int(e)+Q(b)*Q(10)**int(f))
        relations=set()
        for question in tasks(c.scientific_compare):
            a,e,b,f=re.search(r'A=\(([-\d/]+)\)·10\^(-?\d+) и B=\(([-\d/]+)\)·10\^(-?\d+)',question['ru']).groups()
            first,second=Q(a)*Q(10)**int(e),Q(b)*Q(10)**int(f)
            expected='A<B' if first<second else 'A=B' if first==second else 'A>B'
            self.assertEqual(chosen(question),expected)
            relations.add(expected)
        self.assertEqual(relations,{'A<B','A=B','A>B'})
        for question in tasks(c.volume_units):
            a,b=map(int,re.search(r'(\d+) мм, (\d+) мм и 10 мм',question['ru']).groups())
            coefficient,exponent=pair(question)
            self.assertTrue(1<=coefficient<10)
            # Convert each length first, then multiply all three metres.
            actual=Q(a,1000)*Q(b,1000)*Q(10,1000)
            self.assertEqual(coefficient*Q(10)**int(exponent),actual)

    def test_complete_monomials_and_degree_after_cancellation(self):
        for question in tasks(c.monomial_product):
            a,p,b,q=map(int,re.search(r'\((\d+)x\^(\d+)y\)·\((\d+)x²y\^(\d+)\)',question['ru']).groups())
            for x,y in ((Q(-2),Q(3)),(Q(2,3),Q(-1,2)),(Q(0),Q(7))):
                self.assertEqual(evaluate(question['answer'],x=x,y=y),(a*x**p*y)*(b*x*x*y**q))
        for question in tasks(c.monomial_quotient):
            p,q,r=map(int,re.search(r'\(6x\^(\d+)y\^(\d+)\)/\(3x²y\^(\d+)\)',question['ru']).groups())
            for x,y in ((Q(-3),Q(2)),(Q(1,3),Q(-2))):
                self.assertEqual(evaluate(question['answer'],x=x,y=y),Q(6)*x**p*y**q/(3*x*x*y**r))
        for question in tasks(c.polynomial_degree):
            p,q,r,degree=map(int,re.search(r'\(x\^(\d+)\+(\d+)x\)−x\^\d+\+(\d+)x\^(\d+)',question['ru']).groups())
            coefficients=Counter({p:1})
            coefficients[1]+=q
            coefficients[p]-=1
            coefficients[degree]+=r
            coefficients[0]+=1
            expected=max(power for power,coefficient in coefficients.items() if coefficient)
            self.assertEqual(question['answer'],expected)
        self.assertEqual({question['answer'] for question in tasks(c.polynomial_degree)},set(range(1,7)))

    def test_polynomial_recognition_distinguishes_poles_constants_and_zero(self):
        cases=set()
        for question in tasks(c.polynomial_classification):
            source=re.search(r'выражение (.+) многочленом по x после',question['ru'])[1].replace('−','-')
            label=chosen(question)
            if 'x^-' in source:
                negative=re.search(r'(\d+)x\^-(\d+)',source)
                self.assertGreater(int(negative[1]),0)
                self.assertGreater(int(negative[2]),0)
                self.assertIn('Не является многочленом',label)
                cases.add('negative-power')
            elif '/(x+' in source:
                a,b,c0=map(int,re.fullmatch(r'\((\d+)x\+(\d+)\)/\(x\+(\d+)\)',source).groups())
                # A genuine uncancelled pole proves this rational function is not polynomial.
                self.assertNotEqual(a*(-c0)+b,0)
                self.assertIn('Не является многочленом',label)
                cases.add('variable-denominator')
            else:
                coefficients=Counter()
                tokens=list(re.finditer(r'([+-]?)(?:(\d*)x\^(\d+)|(\d+))',source))
                self.assertEqual(''.join(token[0] for token in tokens),source)
                for token in tokens:
                    sign=-1 if token[1]=='-' else 1
                    if token[3] is not None:
                        coefficients[int(token[3])]+=sign*int(token[2] or '1')
                    else:
                        coefficients[0]+=sign*int(token[4])
                remaining={power:value for power,value in coefficients.items() if value}
                if not remaining:
                    self.assertEqual(label,'Нулевой многочлен; обычная конечная степень не определена.')
                    cases.add('zero')
                else:
                    degree=max(remaining)
                    self.assertEqual(label,f'Многочлен степени {degree}.')
                    cases.add('constant' if degree==0 else 'polynomial')
        self.assertEqual(cases,{'negative-power','variable-denominator','zero','constant','polynomial'})

    def test_full_polynomial_results_match_the_original_expression(self):
        for family in (c.polynomial_add,c.polynomial_subtract,c.polynomial_multiply):
            for question in tasks(family):
                a,b=map(int,re.search(r'\((\d+)x[²+]+(\d+)x?',question['ru']).groups()) if family is not c.polynomial_multiply else map(int,re.search(r'\((\d+)x\+(\d+)\)',question['ru']).groups())
                for x in (Q(-3),Q(0),Q(1,7),Q(2)):
                    if family is c.polynomial_add: expected=(a*x*x+b*x-1)+(3*x*x-a*x+b)
                    elif family is c.polynomial_subtract: expected=(a*x*x+b*x+4)-(2*x*x-a*x+b)
                    else: expected=(a*x+b)*(x-a)
                    self.assertEqual(evaluate(question['answer'],x=x),expected)
                self.assertEqual(question['response']['form'],'expanded')
                # A coefficient alone cannot pass as a full polynomial.
                self.assertFalse(structured_matches(str(a),question['response'],question['answer']))
        question=c.polynomial_add(1,0)
        self.assertEqual(question['answer'],'6*x^2+2')
        self.assertTrue(structured_matches('2+6x²',question['response'],question['answer']))
        question=c.polynomial_subtract(0,1)
        self.assertEqual(question['answer'],'6*x^1')
        self.assertTrue(structured_matches('6x',question['response'],question['answer']))

    def test_full_factorization_and_binomial_cubes(self):
        for family in (c.factor_common,c.factor_group,c.factor_cube,c.binomial_cube):
            for question in tasks(family):
                if family is c.factor_common:
                    a,constant=map(int,re.search(r'Разложите (\d+)x²\+(\d+)x',question['ru']).groups())
                    original=lambda x:a*x*x+constant*x
                elif family is c.factor_group:
                    a,b,constant=map(int,re.search(r'x³\+(\d+)x²\+(\d+)x\+(\d+)',question['ru']).groups())
                    original=lambda x:x**3+a*x*x+b*x+constant
                elif family is c.factor_cube:
                    a,b=map(int,re.search(r'кубов (\d+)x³−(\d+)',question['ru']).groups())
                    original=lambda x:a*x**3-b
                else:
                    a,b=map(int,re.search(r'куб \((\d+)x−(\d+)\)',question['ru']).groups())
                    original=lambda x:(a*x-b)**3
                for x in (Q(-2),Q(0),Q(1,5),Q(4)):
                    self.assertEqual(evaluate(question['answer'],x=x),original(x))
        question=c.factor_common(0,0)
        self.assertFalse(structured_matches('2x²+6x',question['response'],question['answer']))
        self.assertTrue(structured_matches('2(x+3)x',question['response'],question['answer']))
        question=c.binomial_cube(0,0)
        self.assertFalse(structured_matches('(x-2)^3',question['response'],question['answer']))

    def test_rational_operations_respect_original_equivalence_and_exclusions(self):
        for family in (c.rational_add,c.rational_multiply,c.rational_divide):
            for i in range(10):
                for j in range(10):
                    question=family(i,j)
                    a,b=i+2,j+3
                    for x in (Q(-20),Q(-1,2),Q(1,3),Q(20)):
                        if family is c.rational_add: expected=Q(a)/x+Q(b)/(x+1)
                        elif family is c.rational_multiply: expected=(a*x/(x+b))*((x+b)**2/(b*x*x))
                        else: expected=(Q(a)/(x-b))/(Q(b)/(x+a))
                        self.assertEqual(evaluate(question['answer'],x=x),expected)
                    self.assertIn('x≠',question['ru'])
        question=c.rational_add(0,0)
        self.assertFalse(structured_matches('5',question['response'],question['answer']))

    def test_functions_graph_parameters_intercepts_and_domain(self):
        for question in tasks(c.direct_proportion):
            x,y=map(Q,re.search(r'точку \(([-\d/]+);([-\d/]+)\)',question['ru']).groups())
            answer=json.loads(question['answer'])
            self.assertEqual(answer['b'],0)
            self.assertEqual(Q(str(answer['m']))*x,y)
            for parameter in question['response']['parameters']:
                self.assertLessEqual(parameter['min'],answer[parameter['key']])
                self.assertGreaterEqual(parameter['max'],answer[parameter['key']])
        for question in tasks(c.axes_pair):
            m,b=map(int,re.search(r'y=(\d+)x\+(\d+)',question['ru']).groups())
            x0,y0=pair(question)
            self.assertEqual(m*x0+b,0)
            self.assertEqual(y0,b)
        for question in tasks(c.function_domain):
            hole,left,right=map(int,re.search(r'x−\((-?\d+)\).*?\[(-?\d+);(-?\d+)\]',question['ru']).groups())
            domain=parse_intervals(question['answer'])
            for point in (left-1,left,Q(left+hole,2),hole,Q(hole+right,2),right,right+1):
                self.assertEqual(contains(domain,point),left<=point<=right and point!=hole)
        for question in tasks(c.function_relation):
            for option in question['response']['options']:
                observations=[tuple(map(int,point)) for point in re.findall(r'\((\d+);(\d+)\)',option['label'])]
                outputs={}
                valid=True
                for x,y in observations:
                    if x in outputs and outputs[x]!=y: valid=False
                    outputs[x]=y
                self.assertEqual(valid,option['value']==question['answer'])

    def test_data_frequency_table_and_polygon(self):
        for question in tasks(c.sample_design):
            self.assertIn('общего списка всех классов',chosen(question))
        for question in tasks(c.frequency_pair):
            observations=list(map(int,question['ru'].split(': ',1)[1].split('. Составьте',1)[0].split(', ')))
            self.assertEqual(pair(question),(observations.count(1),observations.count(2)))
            self.assertEqual(sum(pair(question)),len(observations))
        for question in tasks(c.frequency_polygon):
            frequencies=tuple(map(int,re.search(r'равны (\d+),(\d+),(\d+)',question['ru']).groups()))
            vertices=tuple(tuple(map(int,point)) for point in re.findall(r'\((\d+);(\d+)\)',chosen(question)))
            self.assertEqual(vertices,tuple(zip((2,4,6),frequencies)))

    def test_axioms_order_layoff_and_parallel_uniqueness(self):
        for question in tasks(c.incidence_axiom):
            ab,bc=map(int,re.search(r'AB=(\d+), BC=(\d+)',question['ru']).groups())
            self.assertIn('единственная прямая',chosen(question))
            self.assertIn(f'AC={ab+bc}.',chosen(question))
        for question in tasks(c.point_order):
            ob,oc=map(int,re.search(r'OB=(\d+), OC=(\d+)',question['ru']).groups())
            self.assertEqual(pair(question),(oc-ob,1))
        for question in tasks(c.angle_layoff):
            a,total=map(int,re.search(r'∠AOB=(\d+)°, ∠AOC=(\d+)°',question['ru']).groups())
            self.assertTrue(0<a<total<180)
            self.assertEqual(question['answer'],total-a)
        for question in tasks(c.triangle_copy):
            self.assertEqual(chosen(question),'Один.')
        for question in tasks(c.parallel_axiom):
            slope,intercept,px,py=map(int,re.search(r'y=(-?\d+)x\+(\d+).*?P=\((-?\d+);(-?\d+)\)',question['ru']).groups())
            self.assertNotEqual(slope*px+intercept,py)
            self.assertEqual(evaluate(question['answer'],x=px),py)
            self.assertEqual(evaluate(question['answer'],x=px+1)-evaluate(question['answer'],x=px),slope)

    def test_triangle_classification_side_order_and_external_height(self):
        kinds=set()
        for question in tasks(c.triangle_type):
            angles=list(map(int,re.search(r'углы (\d+)°, (\d+)° и (\d+)°',question['ru']).groups()))
            self.assertEqual(sum(angles),180)
            self.assertTrue(all(angle>0 for angle in angles))
            largest=max(angles)
            expected='Остроугольный.' if largest<90 else 'Прямоугольный.' if largest==90 else 'Тупоугольный.'
            self.assertEqual(chosen(question),expected)
            kinds.add(expected)
        self.assertEqual(len(kinds),3)
        for question in tasks(c.side_angle_order):
            a,b,d=map(int,re.search(r'∠A=(\d+)°, ∠B=(\d+)°, ∠C=(\d+)°',question['ru']).groups())
            lengths={'BC':sin(radians(a)),'AC':sin(radians(b)),'AB':sin(radians(d))}
            sides=chosen(question).split(' < ')
            self.assertTrue(lengths[sides[0]]<lengths[sides[1]]<lengths[sides[2]])
        for question in tasks(c.height_location):
            a,b,d=map(int,re.search(r'∠A=(\d+)°, ∠B=(\d+)°, ∠C=(\d+)°',question['ru']).groups())
            # Set AB=1; law of sines gives AC, its x-projection locates the foot.
            foot=sin(radians(b))/sin(radians(d))*cos(radians(a))
            expected='В точке B.' if abs(foot-1)<1e-12 else 'Внутри отрезка AB.' if 0<foot<1 else 'На продолжении AB за точку B.'
            self.assertEqual(chosen(question),expected)

    def test_right_triangle_special_lengths_and_valid_congruence(self):
        for question in tasks(c.right_thirty):
            hyp,side=map(int,re.search(r'гипотенуза (\d+) см.*?сторона (\d+) см',question['ru']).groups())
            leg,perimeter=pair(question)
            self.assertAlmostEqual(float(leg),hyp*sin(radians(30)))
            self.assertEqual(perimeter/side,3)
        for question in tasks(c.right_median):
            a,b=map(int,re.search(r'равны (\d+) и (\d+) см',question['ru']).groups())
            first,second=pair(question)
            self.assertEqual((2*first,2*second),(a,b))
        for question in tasks(c.right_congruence):
            hyp,leg=map(int,re.search(r'гипотенузы равны (\d+) см.*?катеты равны (\d+) см',question['ru']).groups())
            self.assertTrue(0<leg<hyp)
            self.assertIn('по гипотенузе и катету',chosen(question))

    def test_projections_perpendicular_angles_and_parallel_correspondence(self):
        for question in tasks(c.projection_compare):
            a,b=map(int,re.search(r'HA=(\d+), HB=(\d+)',question['ru']).groups())
            # Any common altitude, e.g. PH=7, gives the same order of squared lengths.
            first,second=49+a*a,49+b*b
            expected='PA<PB' if first<second else 'PA=PB' if first==second else 'PA>PB'
            self.assertEqual(chosen(question),expected)
        for question in tasks(c.perpendicular_angles):
            a,b=map(int,re.search(r'на (\d+)°.*?на (\d+)°',question['ru']).groups())
            self.assertEqual(question['answer']+a+b,90)
            self.assertGreater(question['answer'],0)
        for question in tasks(c.common_perpendicular):
            a,b=map(int,re.search(r'угол (\d+)°.*?угол (\d+)°',question['ru']).groups())
            angle,half=map(Q,chosen(question).split(';'))
            self.assertEqual(angle,a)
            self.assertEqual(2*half,b)

    def test_circle_position_and_chord_theorems_all_cases(self):
        counts=set()
        for question in tasks(c.line_circle):
            radius,distance=map(int,re.search(r'окружности (\d+) см.*?прямой (\d+) см',question['ru']).groups())
            # Intersections satisfy t²=R²-d² along the line.
            square=radius*radius-distance*distance
            expected=2 if square>0 else 1 if square==0 else 0
            self.assertEqual(question['answer'],expected)
            counts.add(expected)
        self.assertEqual(counts,{0,1,2})
        cases=set()
        for question in tasks(c.two_circles):
            radius,small,distance=map(Q,re.search(r'R=(\d+), r=(\d+).*?d=([\d/]+)',question['ru']).groups())
            self.assertTrue(radius>small>0)
            if distance==0: expected='Концентрические, не совпадают.'
            elif distance<radius-small: expected='Одна внутри другой, общих точек нет.'
            elif distance==radius-small: expected='Внутреннее касание.'
            elif distance<radius+small: expected='Две общие точки.'
            elif distance==radius+small: expected='Внешнее касание.'
            else: expected='Расположены вне друг друга, общих точек нет.'
            self.assertEqual(chosen(question),expected)
            cases.add(expected)
        self.assertEqual(len(cases),6)
        for question in tasks(c.chord_midpoints):
            a,b=map(int,re.search(r'AM=(\d+), CN=(\d+)',question['ru']).groups())
            self.assertEqual(question['answer'],a+a+b+b)
        for question in tasks(c.locus):
            ax,bx,py=map(int,re.search(r'A=\((-?\d+);0\), B=\((\d+);0\), P=\(0;(\d+)\)',question['ru']).groups())
            self.assertEqual(ax*ax+py*py,bx*bx+py*py)
            self.assertNotEqual(py,0)
            self.assertNotEqual(ax*ax+py*py,(bx-ax)**2)
            self.assertIn('Серединный перпендикуляр',chosen(question))

    def test_incircle_circumcircle_and_obtuse_center(self):
        cases=set()
        for question in tasks(c.circumcenter_location):
            a,b,d=map(int,re.search(r'углы (\d+)°, (\d+)°, (\d+)°',question['ru']).groups())
            largest=max(a,b,d)
            expected='Внутри треугольника.' if largest<90 else 'На середине гипотенузы.' if largest==90 else 'Вне треугольника.'
            self.assertEqual(chosen(question),expected)
            cases.add(expected)
        self.assertEqual(len(cases),3)
        for question in tasks(c.incenter_angles):
            a,b=map(int,re.search(r'∠A=(\d+)°, ∠B=(\d+)°',question['ru']).groups())
            d=180-a-b
            bic,cia=pair(question)
            self.assertEqual(bic+Q(b,2)+Q(d,2),180)
            self.assertEqual(cia+Q(d,2)+Q(a,2),180)
        for question in tasks(c.circumradius_pair):
            a,b=map(int,re.search(r'гипотенузы (\d+) и (\d+) см',question['ru']).groups())
            first,second=pair(question)
            self.assertEqual((2*first,2*second),(a,b))


if __name__=='__main__':
    unittest.main()
