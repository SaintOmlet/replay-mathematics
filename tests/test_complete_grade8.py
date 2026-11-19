"""Prompt-derived mathematical oracles for the eighth-grade completion blocks."""
import ast
import json
from fractions import Fraction as Q
from math import isclose, isqrt, sqrt
import re
import unittest

from backend import complete_grade8 as c


def all_tasks(family):
    for i in range(10):
        for j in range(10):
            yield family(i,j)


def chosen(task):
    return next(option['label'] for option in task['response']['options'] if option['value']==task['answer'])


def pair(task):
    return tuple(Q(value) for value in task['answer'].split(';'))


def roots(task):
    return set(map(Q,task['answer'].split(';')))


def square_root(value):
    value=Q(value)
    a,b=isqrt(value.numerator),isqrt(value.denominator)
    assert a*a==value.numerator and b*b==value.denominator
    return Q(a,b)


def eval_expression(text,**variables):
    def visit(node):
        if isinstance(node,ast.Constant):
            return Q(str(node.value))
        if isinstance(node,ast.Name):
            return Q(variables[node.id])
        if isinstance(node,ast.UnaryOp):
            value=visit(node.operand)
            return -value if isinstance(node.op,ast.USub) else value
        if isinstance(node,ast.BinOp):
            left,right=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add): return left+right
            if isinstance(node.op,ast.Sub): return left-right
            if isinstance(node.op,ast.Mult): return left*right
            if isinstance(node.op,ast.Div): return left/right
            if isinstance(node.op,ast.Pow): return left**int(right)
        raise AssertionError(ast.dump(node))
    return visit(ast.parse(text.replace('^','**'),mode='eval').body)


class CompleteGrade8Tests(unittest.TestCase):
    def test_registry_content_grid_and_serialization(self):
        self.assertEqual(len(c.TOPICS),12)
        total=0
        for topic in c.TOPICS:
            body=topic['lesson']
            for field in ('theory','examples','mistakes','checks'):
                self.assertGreaterEqual(len(body[field]),2)
            self.assertTrue(all(len(example['steps'])>=3 for example in body['examples']))
            self.assertEqual(len(c.LEVELS_BY_TOPIC[topic['id']]),len(c.FAMILIES[topic['id']]))
            seen=set()
            for family in c.FAMILIES[topic['id']]:
                for i in range(10):
                    for j in range(10):
                        task=family(i,j)
                        self.assertEqual(task,family(i,j))
                        json.dumps(task,allow_nan=False)
                        self.assertNotIn(task['ru'],seen,(family.__name__,i,j))
                        seen.add(task['ru'])
                        self.assertEqual(len(task['hints']),2)
                        self.assertNotEqual(*task['hints'])
                        self.assertGreaterEqual(len(task['solution']),2)
                        self.assertNotIn(task['hints'][1],task['solution'])
                        if task.get('response',{}).get('kind')=='choice':
                            labels=[option['label'] for option in task['response']['options']]
                            self.assertEqual(len(labels),len(set(labels)))
                        total+=1
            self.assertEqual(len(seen),300)
        self.assertEqual(total,3600)

    def test_real_number_classification_and_root_signs(self):
        for task in all_tasks(c.classify_real):
            label=chosen(task)
            square,numerator=map(int,re.search(r'√(\d+); (\d+)/7',label).groups())
            self.assertEqual(isqrt(square)**2,square)
            self.assertGreater(numerator,0)
        for task in all_tasks(c.root_and_equation):
            radicand,shift=map(int,re.search(r'√(\d+).*?\(x−(\d+)\)',task['ru']).groups())
            root,total=pair(task)
            self.assertEqual(root,square_root(radicand))
            actual=(shift+root,shift-root)
            self.assertEqual(sum(actual),total)
            self.assertTrue(all((x-shift)**2==radicand for x in actual))
        for task in all_tasks(c.compare_signed_roots):
            inside,bound=map(int,re.search(r'чисел −√(\d+) и −(\d+)',task['ru']).groups())
            self.assertIn(' > ',chosen(task))
            self.assertLess(inside,bound*bound)

    def test_radical_transformations_have_exact_full_choices(self):
        for task in all_tasks(c.extract_root):
            original=int(re.search(r'из √(\d+)',task['ru'])[1])
            coefficient,inside=map(int,re.fullmatch(r'(\d+)√(\d+)',chosen(task)).groups())
            self.assertEqual(original,coefficient*coefficient*inside)
            self.assertFalse(any(inside%(square*square)==0 for square in range(2,isqrt(inside)+1)))
        for task in all_tasks(c.rationalize_full):
            b,d,a=map(int,re.search(r'в (\d+)/\(√(\d+)−(\d+)\)',task['ru']).groups())
            rb,rd,ra=map(int,re.fullmatch(r'(\d+)\(√(\d+)\+(\d+)\)',chosen(task)).groups())
            self.assertEqual((rb,rd,ra),(b,d,a))
            self.assertEqual(d-a*a,1)
            self.assertTrue(isclose(b/(sqrt(d)-a),rb*(sqrt(rd)+ra),rel_tol=1e-12))
        for task in all_tasks(c.combine_full_radicals):
            x,y=map(int,re.search(r'полностью √(\d+)\+√(\d+)',task['ru']).groups())
            coefficient=int(re.fullmatch(r'(\d+)√2',chosen(task))[1])
            self.assertEqual(coefficient,isqrt(x//2)+isqrt(y//2))

    def test_quadratic_classification_roots_and_full_factorization(self):
        for task in all_tasks(c.quadratic_classification):
            equation=task['ru'].split('уравнение ',1)[1].split(' после ')[0]
            left,right=equation.replace('²','^2').replace('−','-').split('=')
            def coefficients(value):
                # Independent finite differences recover a quadratic's
                # coefficients after moving both sides to the left.
                value=re.sub(r'(\d)x',r'\1*x',value)
                ys=[eval_expression(value,x=x) for x in (-1,0,1)]
                return ((ys[0]+ys[2]-2*ys[1])/2,(ys[2]-ys[0])/2,ys[1])
            a,b,d=(x-y for x,y in zip(coefficients(left),coefficients(right)))
            if a==0:
                self.assertIn('Линейное',chosen(task))
            elif b==0:
                self.assertIn('b=0',chosen(task))
            elif d==0:
                self.assertIn('c=0',chosen(task))
            else:
                self.assertEqual(chosen(task),'Полное квадратное')
        for task in all_tasks(c.quadratic_full_roots):
            b,d=map(int,re.search(r'x²\+\((-?\d+)\)x\+\((-?\d+)\)',task['ru']).groups())
            discriminant=b*b-4*d
            expected={Q(-b+isqrt(discriminant),2),Q(-b-isqrt(discriminant),2)}
            self.assertEqual(roots(task),expected)
            self.assertTrue(all(x*x+b*x+d==0 for x in roots(task)))
        for task in all_tasks(c.factor_full_quadratic):
            a,b,d=map(int,re.search(r'(\d+)x²−(\d+)x\+(\d+)',task['ru']).groups())
            self.assertEqual(task['response']['form'],'factored')
            for x in (Q(-2),Q(0),Q(1,3),Q(9)):
                self.assertEqual(eval_expression(task['answer'],x=x),a*x*x-b*x+d)

    def test_substitution_keeps_all_roots_and_original_domain(self):
        for family in (c.biquadratic_all,c.shifted_biquadratic):
            for task in all_tasks(family):
                if family is c.biquadratic_all:
                    b,d=map(int,re.search(r'x⁴−(\d+)x²\+(\d+)',task['ru']).groups())
                    shift=0
                else:
                    shift,b,d=map(int,re.search(r'\(x−\((-?\d+)\)\)⁴−(\d+)\(x−\(-?\d+\)\)²\+(\d+)',task['ru']).groups())
                disc=isqrt(b*b-4*d)
                t_values=(Q(b-disc,2),Q(b+disc,2))
                expected={shift+sign*square_root(t) for t in t_values for sign in (-1,1)}
                self.assertEqual(roots(task),expected)
                self.assertTrue(all((x-shift)**4-b*(x-shift)**2+d==0 for x in roots(task)))
        for task in all_tasks(c.reciprocal_substitution):
            shift=int(re.search(r'\(x−(\d+)\)',task['ru'])[1])
            right=Q(re.search(r'=([0-9/]+)\.',task['ru'])[1])
            disc=square_root(right*right-4)
            expected={shift+(right-disc)/2,shift+(right+disc)/2}
            self.assertEqual(roots(task),expected)
            self.assertTrue(all(x!=shift and x-shift+1/(x-shift)==right for x in roots(task)))

    def test_general_parabola_and_contextual_models(self):
        for task in all_tasks(c.general_parabola):
            a,b,d=map(int,re.search(r'y=(\d+)x²\+\((-?\d+)\)x\+\((-?\d+)\)',task['ru']).groups())
            parameters=json.loads(task['answer'])
            for x in (-3,0,2,7):
                self.assertEqual(parameters['a']*(x-parameters['h'])**2+parameters['k'],a*x*x+b*x+d)
        for task in all_tasks(c.area_model):
            perimeter=int(re.search(r'периметр (\d+)',task['ru'])[1])
            for x in (Q(1),Q(3),Q(perimeter,4)):
                self.assertEqual(eval_expression(task['answer'],x=x),x*(Q(perimeter,2)-x))
        for task in all_tasks(c.maximum_area):
            self.assertNotIn('квадрат',task['ru'].lower(),
                             'Условие не должно заранее сообщать ученику оптимальную форму прямоугольника')
            first,second=map(int,re.search(r'ограды (\d+) м и (\d+) м',task['ru']).groups())
            side,area=pair(task)
            self.assertEqual(4*side,first+second)
            self.assertEqual(area,side*side)
            self.assertGreater(area,(side-1)*(side+1))

    def test_statistics_uses_width_weight_and_population_denominator(self):
        for task in all_tasks(c.histogram_heights):
            a,b=map(int,re.search(r'частоты (\d+) и (\d+)',task['ru']).groups())
            heights=tuple(Q(value.strip()) for value in chosen(task).split(';'))
            self.assertEqual(heights,(Q(a,2),Q(b,4)))
        for task in all_tasks(c.cumulative_counts):
            frequencies=list(map(int,re.search(r'интервалов: (\d+); (\d+); (\d+)',task['ru']).groups()))
            self.assertEqual(pair(task),(sum(frequencies[:2]),sum(frequencies)))
        for task in all_tasks(c.variance_deviation):
            x,y,z=map(int,re.search(r'значения (\d+), (\d+), (\d+)',task['ru']).groups())
            observations=[x]*2+[y]*5+[z]*2
            mean=Q(sum(observations),len(observations))
            variance=sum((value-mean)**2 for value in observations)/len(observations)
            actual_variance,deviation=pair(task)
            self.assertEqual(actual_variance,variance)
            self.assertEqual(deviation*deviation,variance)

    def test_geometry_claims_and_construction_dependencies(self):
        for task in all_tasks(c.parallelogram_criterion):
            self.assertTrue(chosen(task).startswith('AB∥CD и AB=CD='))
            self.assertIn('SAS',task['solution'][0])
        for task in all_tasks(c.quadrilateral_hierarchy):
            actual=chosen(task)
            if 'все углы прямые' in task['ru']:
                self.assertEqual(actual,'Квадрат')
            elif 'Все углы прямые' in task['ru']:
                self.assertEqual(actual,'Прямоугольник, не ромб')
            else:
                self.assertEqual(actual,'Ромб, не прямоугольник')
        for task in all_tasks(c.polygon_external):
            count,angle=map(int,re.search(r'Выпуклый (\d+)-угольник.*?угол (\d+)°',task['ru']).groups())
            self.assertEqual(pair(task),(180*(count-2),360-angle))
        for family in (c.arbitrary_ratio_construction,c.trig_angle_construction):
            for task in all_tasks(family):
                labels={option['value']:option['label'] for option in task['response']['options']}
                ordered=[labels[key] for key in task['answer'].split(',')]
                self.assertTrue(ordered[0].startswith(('Из A','Проведи')))
                self.assertTrue(ordered[1].startswith('Отложи'))
                self.assertIn('AX:XB' if family is c.arbitrary_ratio_construction else 'тангенс',ordered[-1])
        for task in all_tasks(c.fourth_proportional):
            a,b,d=map(int,re.search(r'OA=(\d+), OB=(\d+).*?OC=(\d+)',task['ru']).groups())
            self.assertAlmostEqual(task['answer'],float(Q(b*d,a)))

    def test_centres_and_triangle_conditions(self):
        for task in all_tasks(c.centroid_coordinates):
            coordinates=[tuple(map(int,value)) for value in re.findall(r'[ABC]\((-?\d+);(-?\d+)\)',task['ru'])]
            actual=pair(task)
            self.assertEqual(3*actual[0],sum(v[0] for v in coordinates))
            self.assertEqual(3*actual[1],sum(v[1] for v in coordinates))
        for task in all_tasks(c.bisector_ratio):
            ab,ac,bc=map(Q,re.search(r'AB=(\d+), AC=(\d+), BC=([0-9/]+)',task['ru']).groups())
            self.assertLess(abs(ab-ac),bc)
            self.assertLess(bc,ab+ac)
            bd=Q(str(task['answer'])).limit_denominator(10000)
            self.assertEqual(bd/(bc-bd),ab/ac)
        for task in all_tasks(c.circumcentre_right):
            coordinates=[tuple(map(int,value)) for value in re.findall(r'[ABC]\((-?\d+);(-?\d+)\)',task['ru'])]
            x,y=pair(task)
            distances={(x-a)**2+(y-b)**2 for a,b in coordinates}
            self.assertEqual(len(distances),1)

    def test_trig_and_complementary_angles_use_complete_ratios(self):
        for task in all_tasks(c.trig_all_functions):
            numerator,denominator=map(int,re.search(r'sin α=(\d+)/(\d+)',task['ru']).groups())
            sine=Q(numerator,denominator)
            cosine,tangent,cotangent=map(Q,re.findall(r'=([0-9/]+)',chosen(task)))
            self.assertEqual(sine*sine+cosine*cosine,1)
            self.assertEqual(tangent,sine/cosine)
            self.assertEqual(cotangent,cosine/sine)
        for task in all_tasks(c.complementary_functions):
            a,b,h=map(int,re.search(r'катет (\d+), прилежащий (\d+), гипотенуза (\d+)',task['ru']).groups())
            values=tuple(map(Q,re.findall(r'=([0-9/]+)',chosen(task))))
            self.assertEqual(values,(Q(b,h),Q(a,h),Q(b,a),Q(a,b)))
        for task in all_tasks(c.special_triangle_sides):
            hyp,angle=map(int,re.search(r'треугольника (\d+), острый угол α=(\d+)',task['ru']).groups())
            def squared(text):
                if '√' in text:
                    coefficient,radicand,denominator=map(int,re.fullmatch(r'(\d+)√(\d+)/(\d+)',text.strip()).groups())
                    return Q(coefficient*coefficient*radicand,denominator*denominator)
                return Q(text.strip())**2
            actual=tuple(squared(text) for text in chosen(task).split(';'))
            fractions={30:(Q(1,4),Q(3,4)),45:(Q(1,2),Q(1,2)),60:(Q(3,4),Q(1,4))}[angle]
            self.assertEqual(actual,tuple(hyp*hyp*f for f in fractions))
            self.assertEqual(sum(actual),hyp*hyp)

    def test_areas_coordinates_and_complete_line_expressions(self):
        for task in all_tasks(c.trapezoid_area):
            a,b,h=map(int,re.search(r'трапеции (\d+) и (\d+), высота (\d+)',task['ru']).groups())
            self.assertEqual(Q(str(task['answer'])),Q((a+b)*h,2))
        for task in all_tasks(c.equal_area_height):
            a,b,base=map(int,re.search(r'основанием (\d+) и высотой (\d+).*?основанием (\d+)',task['ru']).groups())
            self.assertAlmostEqual(task['answer']*base,a*b)
        for task in all_tasks(c.area_rearrangement):
            self.assertIn('без наложения и промежутков',chosen(task))
        for task in all_tasks(c.section_point):
            ax,ay,bx,by,m,p=map(int,re.search(r'A\((-?\d+);(-?\d+)\), B\((-?\d+);(-?\d+)\).*?AX:XB=(\d+):(\d+)',task['ru']).groups())
            x,y=pair(task)
            self.assertEqual((m+p)*x,p*ax+m*bx)
            self.assertEqual((m+p)*y,p*ay+m*by)
        for task in all_tasks(c.general_line):
            points=[tuple(map(int,value)) for value in re.findall(r'[AB]\((-?\d+);(-?\d+)\)',task['ru'])]
            self.assertNotEqual(points[0][0],points[1][0])
            self.assertTrue(all(eval_expression(task['answer'],x=x)==y for x,y in points))
        for task in all_tasks(c.vertical_line):
            points=[tuple(map(int,value)) for value in re.findall(r'[AB]\((-?\d+);(-?\d+)\)',task['ru'])]
            self.assertEqual(points[0][0],points[1][0])
            self.assertEqual(chosen(task),'x='+str(points[0][0]))


if __name__=='__main__':
    unittest.main()
