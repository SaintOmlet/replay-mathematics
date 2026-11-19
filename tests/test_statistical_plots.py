"""Prompt-derived oracles and exact input validation for the statistical editor."""

from collections import Counter
from fractions import Fraction as Q
import json
import re
import unittest

from backend import data_plots as parser
from backend import statistics_curriculum as curriculum
from backend.grading import AnswerError


def generated(family):
    for i in range(10):
        for j in range(10):
            yield family(i,j)


def answers(question):
    return tuple(map(Q,json.loads(question['answer'])))


def encode(values):
    return json.dumps([str(value) for value in values])


class StatisticalPlotsTests(unittest.TestCase):
    def test_all_400_questions_are_deterministic_distinct_and_exactly_gradable(self):
        count=0
        for topic in curriculum.TOPICS:
            body=topic['lesson']
            for field in ('theory','examples','mistakes','checks'):
                self.assertGreaterEqual(len(body[field]),2)
            self.assertTrue(all(len(example['steps'])>=2 for example in body['examples']))
            seen=set()
            for family in curriculum.FAMILIES[topic['id']]:
                for i in range(10):
                    for j in range(10):
                        with self.subTest(family=family.__name__,i=i,j=j):
                            question=family(i,j)
                            self.assertEqual(question,family(i,j))
                            json.dumps(question,allow_nan=False)
                            self.assertNotIn(question['ru'],seen)
                            seen.add(question['ru'])
                            response=question['response']
                            self.assertEqual(response['kind'],'data_plot')
                            self.assertEqual(len(response['labels']),len(set(response['labels'])))
                            self.assertEqual(len(response['labels']),len(answers(question)))
                            self.assertTrue(all(value>=0 for value in answers(question)))
                            self.assertTrue(parser.matches(question['answer'],response,question['answer']))
                            for position in range(len(response['labels'])):
                                wrong=list(answers(question))
                                wrong[position]+=1
                                self.assertFalse(parser.matches(encode(wrong),response,question['answer']))
                            self.assertEqual(len(question['hints']),2)
                            self.assertNotEqual(*question['hints'])
                            self.assertNotIn(question['hints'][1],question['solution'])
                            self.assertGreaterEqual(len(question['solution']),2)
                            count+=1
            self.assertEqual(len(seen),len(curriculum.FAMILIES[topic['id']])*100)
        self.assertEqual(count,400)

    def test_full_table_counts_every_observation_in_the_actual_prompt(self):
        for question in generated(curriculum.full_table):
            raw=re.search(r'выборки: (.+)\. Заполните',question['ru'])[1]
            observations=list(map(int,raw.split(', ')))
            frequencies=Counter(observations)
            labels=list(map(int,question['response']['labels']))
            self.assertEqual(labels,sorted(frequencies))
            self.assertEqual(answers(question),tuple(frequencies[value] for value in labels))
            self.assertEqual(sum(answers(question)),len(observations))
            self.assertEqual(question['response']['mode'],'frequency_table')
            # Entering the sample size in every cell cannot pass.
            self.assertFalse(parser.matches(encode([len(observations)]*len(labels)),question['response'],question['answer']))

    def test_polygon_reads_actual_table_and_retains_numeric_x_spacing(self):
        for question in generated(curriculum.polygon_absolute):
            raw=re.search(r'Таблица \(значение: частота\): (.+)\. Задайте',question['ru'])[1]
            pairs=[tuple(map(int,item.split(': '))) for item in raw.split('; ')]
            xs,frequencies=zip(*pairs)
            response=question['response']
            self.assertEqual(response['mode'],'frequency_polygon')
            self.assertEqual(response['x'],list(xs))
            self.assertEqual(list(map(int,response['labels'])),list(xs))
            self.assertEqual(answers(question),frequencies)
            self.assertTrue(all(a<b for a,b in zip(xs,xs[1:])))
            self.assertGreater(len(set(b-a for a,b in zip(xs,xs[1:]))),1)
            cumulative=[]
            for frequency in frequencies:
                cumulative.append(frequency+(cumulative[-1] if cumulative else 0))
            self.assertFalse(parser.matches(encode(cumulative),response,question['answer']))

    def test_polygon_from_sample_requires_all_frequencies(self):
        for question in generated(curriculum.polygon_from_sample):
            raw=re.search(r'По выборке (.+) постройте',question['ru'])[1]
            observations=list(map(int,raw.split(', ')))
            frequencies=Counter(observations)
            xs=question['response']['x']
            self.assertEqual(xs,sorted(frequencies))
            self.assertEqual(answers(question),tuple(frequencies[value] for value in xs))
            self.assertEqual(sum(answers(question)),len(observations))

    def test_histogram_areas_reconstruct_prompt_counts_and_unequal_widths(self):
        rational_cases=0
        for question in generated(curriculum.histogram):
            entries=re.findall(r'\[(-?\d+);(-?\d+)([)\]]): (\d+)',question['ru'])
            self.assertEqual(len(entries),3)
            intervals=[(int(left),int(right),bracket,int(count)) for left,right,bracket,count in entries]
            widths=[right-left for left,right,_,_ in intervals]
            self.assertTrue(all(width>0 for width in widths))
            # The promise "intervals of unequal width" must hold for every seed.
            self.assertGreater(len(set(widths)),1)
            self.assertEqual([item[2] for item in intervals],[')',')',']'])
            self.assertTrue(all(first[1]==second[0] for first,second in zip(intervals,intervals[1:])))
            counts=[item[3] for item in intervals]
            response=question['response']
            self.assertEqual(response['mode'],'histogram')
            self.assertEqual(response['bins'],[intervals[0][0]]+[right for _,right,_,_ in intervals])
            heights=answers(question)
            self.assertEqual(tuple(width*height for width,height in zip(widths,heights)),tuple(counts))
            self.assertEqual(sum(width*height for width,height in zip(widths,heights)),sum(counts))
            if any(value.denominator!=1 for value in heights): rational_cases+=1
            self.assertFalse(parser.matches(encode(counts),response,question['answer']))
        self.assertGreater(rational_cases,40)

    def test_histogram_regression_equal_width_seeds_are_no_longer_mislabeled(self):
        for i in (1,5,9):
            for j in (4,5):
                with self.subTest(i=i,j=j):
                    bounds=curriculum.histogram(i,j)['response']['bins']
                    self.assertGreater(len({b-a for a,b in zip(bounds,bounds[1:])}),1)

    def test_exact_fraction_grading_rejects_float_approximations(self):
        response={'kind':'data_plot','mode':'histogram','labels':['A','B','C']}
        target='["1/3","7/2","2"]'
        self.assertTrue(parser.matches('["2/6","3.5","2.0"]',response,target))
        self.assertTrue(parser.matches('["1 / 3","7/2","2"]',response,target))
        for raw in ('["0.3333333333","3.5","2"]','[".3333333333333333","7/2","2"]',
                    '["0.333333333333333333333333333333333333","7/2","2"]'):
            with self.subTest(raw=raw):
                self.assertFalse(parser.matches(raw,response,target))
        # Binary JSON numbers cannot silently change exact fraction semantics.
        for raw in ('[0.3333333333333333,"7/2","2"]','["1/3",3.5,"2"]','["1/3","7/2",2]'):
            with self.assertRaises(AnswerError): parser.matches(raw,response,target)

    def test_json_shape_and_every_empty_field_are_rejected(self):
        response={'kind':'data_plot','mode':'frequency_table','labels':['A','B','C']}
        invalid=(None,'',' ','null','{}','true','false','1','"1"','[]','["1"]',
                 '["1","2","3","4"]','["1","2",]','["1","2",null]',
                 '["","2","3"]','["1"," ","3"]','["1","2",""]',
                 '["1","2",{}]','["1","2",[]]','["1","2",true]',
                 '["1","2",NaN]','["1","2",Infinity]','["1","2","NaN"]',
                 '["1","2","Infinity"]','["1","2","1/0"]','["1","2","1e3"]')
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(AnswerError): parser.values(raw,response)

    def test_nonnegative_and_length_limits_with_exact_boundaries(self):
        response={'kind':'data_plot','mode':'frequency_table','labels':['A','B','C']}
        self.assertEqual(parser.values('["0","10000","2/3"]',response),(0,10000,Q(2,3)))
        self.assertEqual(parser.values('["-0","10 000",".5"]',response),(0,10000,Q(1,2)))
        for invalid in ('-1','-1/1000000000','10001','100000001/10000','1'*41,'2**3','2;3'):
            with self.subTest(value=invalid):
                with self.assertRaises(AnswerError): parser.values(encode(['1',invalid,'3']),response)

    def test_describe_preserves_labels_and_exact_fractions(self):
        response={'labels':['[0;2)','[2;5]']}
        self.assertEqual(parser.describe('["1/3","7/2"]',response),'[0;2): 1/3; [2;5]: 7/2')

    def test_full_coverage_claims_have_theory_examples_and_targeted_families(self):
        evidence={item['code']:item for item in curriculum.GOAL_EVIDENCE}
        for code in ('7.3.3.4','7.3.3.6','8.3.3.2'):
            self.assertEqual(evidence[code]['status'],'F')
            topic=next(topic for topic in curriculum.TOPICS if topic['id']==evidence[code]['topic'])
            self.assertGreaterEqual(len(topic['lesson']['examples']),2)
        g7=curriculum.FAMILIES[evidence['7.3.3.4']['topic']]
        self.assertIn(curriculum.full_table,g7)
        self.assertIn(curriculum.polygon_absolute,g7)
        self.assertIn(curriculum.polygon_from_sample,g7)
        g8=curriculum.FAMILIES[evidence['8.3.3.2']['topic']]
        self.assertIn(curriculum.histogram,g8)


if __name__=='__main__':
    unittest.main()
