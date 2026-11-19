"""Independent condition-derived checks of all 2,700 original SAT variants.

Domain mapping verified against College Board's four Types of Math Tested
pages (Algebra, Advanced Math, Problem-Solving and Data Analysis, Geometry
and Trigonometry). These are original transfer exercises, not official items.
"""
import json
import math
import re
import tempfile
import unittest
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as Q

from backend import grading, sat_curriculum as sat
from backend.curriculum import generate
from backend.storage import StudyStore


DOMAINS={
    'algebra':{'sat-linear'},
    'advanced-math':{'sat-expressions','sat-nonlinear'},
    'problem-solving-data':{'sat-ratios','sat-data','sat-probability'},
    'geometry-trigonometry':{'sat-geometry','sat-circles','sat-right-triangles'},
}


def variants(family):
    for i in range(10):
        for j in range(10):
            yield family(i,j)


def numbers(pattern,prompt):
    match=re.search(pattern,prompt)
    if not match:
        raise AssertionError((pattern,prompt))
    return tuple(Q(value) for value in match.groups())


def numeric_oracle(family,prompt):
    """Derive a unique requested quantity using only the visible condition."""
    name=family.__name__
    if name=='equation':
        a,b,c=numbers(r'satisfies (\d+)x \+ (\d+) = (-?\d+)',prompt)
        assert a!=0
        return (c-b)/a
    if name=='system':
        total,difference=numbers(r'x \+ y = (\d+) and 2x - y = (-?\d+)',prompt)
        # Determinant -3 is nonzero, so no other pair can satisfy the system.
        x=(total+difference)/3
        y=total-x
        assert 2*x-y==difference
        return y
    if name=='linear_model':
        fee,rate,total=numbers(r'fee of (\d+) dollars plus (\d+) dollars per hour.*?pays (\d+) dollars',prompt)
        assert rate>0 and total>=fee
        return (total-fee)/rate
    if name=='coefficient':
        a,b=numbers(r'\(x \+ (\d+)\)\(x \+ (\d+)\)',prompt)
        return a+b
    if name=='rational_value':
        excluded,square,denominator,x=numbers(r'x ≠ (\d+).*?x² - (\d+)\)/\(x - (\d+)\).*?f\((\d+)\)',prompt)
        assert excluded==denominator and x!=excluded
        return (x*x-square)/(x-denominator)
    if name=='positive_root':
        b,minus_c=numbers(r'x² \+ \((-?\d+)\)x - (\d+) = 0',prompt)
        disc=b*b+4*minus_c
        root=math.isqrt(int(disc))
        assert root*root==disc and minus_c>0
        roots={(-b+root)/2,(-b-root)/2}
        positive=[x for x in roots if x>0]
        assert len(positive)==1
        return positive[0]
    if name=='quadratic_vertex':
        h,k=numbers(r'\(x - \((-?\d+)\)\)² \+ (\d+)',prompt)
        # The coefficient of the square is positive; h is in the real domain.
        assert isinstance(h,Q)
        return k
    if name=='growth':
        initial,factor,years=numbers(r'starts at (\d+) hundred.*?by (\d+) each year.*?after (\d+) years',prompt)
        assert years.denominator==1
        return initial*factor**int(years)
    if name=='percent':
        price,discount=numbers(r'costs (\d+) dollars before a (\d+)% discount',prompt)
        assert 0<=discount<=100
        return price*(100-discount)/100
    if name=='unit_rate':
        distance,time,new_time=numbers(r'travels (\d+) kilometers in (\d+) hours.*?travel in (\d+) hours',prompt)
        assert time>0
        return distance*new_time/time
    if name=='scale_units':
        length,width=numbers(r'is (\d+) meters long and (\d+) meters wide',prompt)
        return (length*100)*(width*100)
    if name=='weighted_mean':
        count_a,a,count_b,b=numbers(r'contains (\d+) values equal to (\d+) and (\d+) values equal to (\d+)',prompt)
        assert count_a>0 and count_b>0
        data=[a]*int(count_a)+[b]*int(count_b)
        return sum(data,Q(0))/len(data)
    if name=='missing_mean':
        a,b,mean=numbers(r'numbers (\d+), (\d+), and x is (\d+)',prompt)
        return 3*mean-a-b
    if name=='linear_prediction':
        m,b,x=numbers(r'y = (\d+)x \+ (\d+).*?x = (\d+)',prompt)
        return m*x+b
    if name=='probability_bag':
        red,blue=numbers(r'contains (\d+) red balls and (\d+) blue balls',prompt)
        assert red>0 and blue>0
        return red/(red+blue)
    if name=='conditional':
        total,favorable=numbers(r'Among (\d+) students.*?, (\d+) also play tennis',prompt)
        assert 0<=favorable<=total and total>0
        return favorable/total
    if name=='independent':
        a,b=numbers(r'probabilities 1/(\d+) and 1/(\d+)',prompt)
        assert a>=1 and b>=1 and 'independent' in prompt
        return 1/(a*b)
    if name=='triangle_area':
        base,height=numbers(r'base of (\d+) and a perpendicular height of (\d+)',prompt)
        assert base>0 and height>0
        return base*height/2
    if name=='similar_length':
        p,q,length=numbers(r'first is (\d+)/(\d+).*?first triangle has length (\d+)',prompt)
        assert p>0 and q>0
        return length*p/q
    if name=='box_volume':
        a,b,c=numbers(r'side lengths (\d+), (\d+), and (\d+)',prompt)
        assert min(a,b,c)>0
        return a*b*c
    if name=='radius_squared':
        square,=numbers(r'= (\d+) represents a circle',prompt)
        root=math.isqrt(int(square))
        assert root*root==square and root>0
        return Q(root)
    if name=='circle_area':
        radius,numerator,denominator=numbers(r'radius (\d+).*?occupies (\d+)/(\d+) of the circle',prompt)
        assert radius>0 and 0<numerator<=denominator
        return radius*radius*numerator/denominator
    if name=='circle_arc':
        radius,angle=numbers(r'radius (\d+).*?measures (\d+) degrees',prompt)
        assert radius>0 and 0<angle<=360
        return 2*radius*angle/360
    if name=='right_ratio':
        a,b=numbers(r'legs have lengths (\d+) and (\d+)',prompt)
        square=a*a+b*b
        hypotenuse=math.isqrt(int(square))
        assert hypotenuse*hypotenuse==square and min(a,b)>0
        return min(a,b)/hypotenuse
    if name=='right_length':
        numerator,denominator,hypotenuse=numbers(r'sin A = (\d+)/(\d+), and AB = (\d+)',prompt)
        assert 0<numerator<denominator and hypotenuse>0
        return hypotenuse*numerator/denominator
    if name=='complementary':
        numerator,denominator=numbers(r'sin A = (\d+)/(\d+)',prompt)
        assert 0<numerator<denominator and 'acute angles of a right triangle' in prompt
        return numerator/denominator
    raise AssertionError('Missing condition-derived oracle for '+name)


class SatCurriculumTests(unittest.TestCase):
    def test_registry_domains_and_all_2700_english_unique_variants(self):
        self.assertEqual(len(sat.TOPICS),9)
        self.assertEqual({d:set(v) for d,v in sat.DOMAIN_PRACTICE.items()},DOMAINS)
        total=0
        for topic in sat.TOPICS:
            self.assertTrue(topic['satReady'] and topic['satOnly'])
            self.assertIn(topic['id'],DOMAINS[topic['satDomain']])
            self.assertEqual(topic['source'],sat.SOURCE)
            self.assertEqual(len(sat.FAMILIES[topic['id']]),3)
            prompts=set()
            for family in sat.FAMILIES[topic['id']]:
                for i in range(10):
                    for j in range(10):
                        task=family(i,j)
                        self.assertEqual(task,family(i,j))
                        self.assertEqual(task['ru'],task['en'])
                        self.assertNotRegex(task['en'],r'[А-Яа-яЁё]')
                        self.assertNotIn(task['en'],prompts)
                        prompts.add(task['en'])
                        self.assertGreaterEqual(len(task['hints']),2)
                        self.assertGreaterEqual(len(task['solution']),2)
                        json.dumps(task,allow_nan=False)
                        total+=1
            self.assertEqual(len(prompts),300)
        self.assertEqual(total,2700)

    def test_all_2600_numeric_keys_against_visible_conditions(self):
        count=0
        for families in sat.FAMILIES.values():
            for family in families:
                if family is sat.equivalent:
                    continue
                for task in variants(family):
                    with self.subTest(family=family.__name__,prompt=task['en']):
                        expected=numeric_oracle(family,task['en'])
                        self.assertIsInstance(expected,Q)
                        self.assertTrue(math.isfinite(task['answer']))
                        self.assertTrue(math.isclose(float(expected),task['answer'],rel_tol=1e-12,abs_tol=1e-12))
                        count+=1
        self.assertEqual(count,2600)

    def test_all_four_authored_expression_choices_have_exactly_one_identity(self):
        positions=Counter()
        for task in variants(sat.equivalent):
            a,b=numbers(r'equivalent to (\d+)\(x \+ (\d+)\)',task['en'])
            correct=[]
            labels=[]
            for option in task['response']['options']:
                label=option['label']
                labels.append(label)
                match=re.fullmatch(r'(\d+)x(?:([+-])(\d+))?',label)
                self.assertIsNotNone(match)
                coefficient=Q(match[1])
                constant=Q(match[3] or 0)*(-1 if match[2]=='-' else 1)
                # Exact coefficient equality proves the polynomial identity
                # for every x, rather than testing one convenient input.
                equivalent=(coefficient,constant)==(a,a*b)
                self.assertEqual(grading.structured_matches(option['value'],task['response'],task['answer']),equivalent)
                if equivalent:
                    correct.append(option['value'])
            self.assertEqual(len(set(labels)),4)
            self.assertEqual(correct,[task['answer']])
            positions[correct[0]]+=1
        self.assertEqual(set(positions),{'a','b','c','d'})

    def test_english_state_preserves_authored_choices_and_structured_grading(self):
        with tempfile.TemporaryDirectory() as folder:
            store=StudyStore(folder,clock=lambda:1000)
            state=store.start({'mode':'practice','lang':'en','topics':['sat-expressions'],'count':1,'problemId':'sat-expressions:0'})
            with store.transaction(write=False) as conn:
                session=next(value for value in store.load_all(conn) if value['id']==state['id'])
            # Check both the automatic-MC and automatic-SPR index positions.
            for index in (0,1):
                for seed in range(100):
                    session['questions']=[['sat-expressions',seed]]*2
                    session['recordedDifficulties']=['easy','easy']
                    session['priorExposure']=[False,False]
                    session['index']=index
                    question=store.state(session,1000)['question']
                    authored=generate('sat-expressions',seed,'en')
                    self.assertEqual(question['response'],authored['response'])
                    self.assertNotIn('options',question)
                    self.assertNotIn('answer',question)
            for correct in (False,True):
                state=store.start({'mode':'practice','lang':'en','topics':['sat-expressions'],'count':1,'problemId':'sat-expressions:23'})
                task=generate('sat-expressions',23,'en')
                answer=task['answer'] if correct else next(option['value'] for option in task['response']['options'] if option['value']!=task['answer'])
                result=store.access(state['id'],'answer',{'index':0,'answer':answer})
                self.assertEqual(result['feedback']['correct'],correct)

    def test_all_numeric_choices_are_unique_homogeneous_and_bound_probabilities(self):
        count=0
        for topic in sat.TOPICS:
            for seed in range(300):
                task=generate(topic['id'],seed,'en')
                if task.get('response'):
                    continue
                choices=StudyStore.options(topic['id'],seed,task['answer'])
                self.assertEqual(len(choices),4)
                self.assertEqual(len(set(choices)),4)
                values=list(map(Q,choices))
                self.assertEqual(sum(math.isclose(float(value),task['answer'],rel_tol=1e-12,abs_tol=1e-12) for value in values),1)
                self.assertEqual(len({'fraction' if '/' in text else 'integer' for text in choices}),1)
                self.assertEqual(choices,StudyStore.options(topic['id'],seed,task['answer']))
                if topic['id']=='sat-probability':
                    self.assertTrue(all(0<=value<=1 for value in values))
                count+=1
        self.assertEqual(count,2600)

    def test_numeric_keys_have_a_usable_spr_or_choice_representation(self):
        for families in sat.FAMILIES.values():
            for family in families:
                if family is sat.equivalent:
                    continue
                for task in variants(family):
                    expected=numeric_oracle(family,task['en'])
                    if not grading.sat_input_available(task['answer']):
                        # The store switches an oversized key to choices.
                        self.assertTrue(StudyStore.multiple_choice({'index':1},task))
                        continue
                    exact=str(expected)
                    limit=6 if expected<0 else 5
                    if len(exact)<=limit:
                        self.assertTrue(grading.sat_matches(exact,task['answer']))
                    else:
                        whole=len(str(abs(int(expected))))
                        places=4-whole
                        self.assertGreaterEqual(places,0)
                        decimal=Decimal(expected.numerator)/Decimal(expected.denominator)
                        value=decimal.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
                        self.assertTrue(grading.sat_matches(format(value,f'.{places}f'),task['answer']))


if __name__=='__main__':
    unittest.main()
