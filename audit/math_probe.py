"""Read-only audit of the shipped catalogue. Run from the project root:
python -B -m audit.math_probe
"""
from collections import Counter, defaultdict
from fractions import Fraction as Q
from math import asin, atan2, cos, factorial, hypot, isfinite, isqrt, pi, prod, radians, sin, sqrt
import re
from statistics import pvariance
import unicodedata

from backend.curriculum import TOPICS, VARIANTS_PER_FAMILY, generate


def roots(b, c):
    d = b * b - 4 * c
    return ((-b - sqrt(d)) / 2, (-b + sqrt(d)) / 2)


def exact_sqrt(value):
    value = Q(value)
    n, d = isqrt(value.numerator), isqrt(value.denominator)
    assert n * n == value.numerator and d * d == value.denominator, value
    return Q(n, d)


def sign_count(a, b):
    return sum((x + a) * (x + b) < 0 for x in range(-100, 101))


def fill_tank(values):
    total = Q(*values[:-1])
    return next(a for a in range(1,80) if 1/Q(a) + 1/Q(a+values[-1]) == 1/total)


# The numbers fed to these checks come from the student-facing prompt.
# The generator parameters, answer, graph payload and field "verify" are not used.
GRADE8 = {
    "root_bound": lambda v: isqrt(v[0]),
    "abs_root": lambda v: abs(sum(v)),
    "irrational_compare": lambda v: sum(v[0] < x*x < v[1] for x in range(isqrt(v[1])+1)),
    "extract_radical": lambda v: exact_sqrt(Q(v[0],v[1])),
    "combine_radical": lambda v: exact_sqrt(Q(v[0],v[3])) + v[1]*exact_sqrt(Q(v[2],v[3])),
    "rationalize_conjugate": lambda v: v[1]*v[1] - v[2],
    "root_domain": lambda v: Q(-v[1],v[0]),
    "root_inverse": lambda v: v[1]*v[1]-v[0],
    "root_scale": lambda v: Q(v[2]*v[2]-v[1]*v[1],v[0]*v[0]),
    "quadratic_incomplete": lambda v: exact_sqrt(Q(v[1],v[0])),
    "discriminant_root": lambda v: roots(v[0],v[1])[1],
    "quadratic_parameter": lambda v: Q(v[1]*v[1],4*v[0]),
    "vieta_sum": lambda v: -v[0],
    "vieta_missing": lambda v: -v[2]-Q(v[0],v[2]),
    "vieta_squares": lambda v: sum(x*x for x in roots(v[0],v[1])),
    "parabola_vertex": lambda v: v[2],
    "complete_square": lambda v: v[1]-Q(v[0]*v[0],4),
    "parabola_width": lambda v: 2*isqrt(v[0]),
    "biquadratic_root": lambda v: exact_sqrt(int(roots(v[0],v[1])[0])),
    "biquadratic_sign": lambda v: exact_sqrt(int(roots(v[0],v[1])[1])),
    "shifted_substitution": lambda v: -v[0]+exact_sqrt(int(roots(v[1],v[3])[1])),
    "rational_single": lambda v: Q(v[0],v[2])-v[1],
    "rational_two": lambda v: Q(v[2]*v[1]-v[0]*v[3],v[0]-v[2]),
    "rational_extraneous": lambda v: -v[0]+v[2],
    "rectangle_length": lambda v: roots(v[1],-v[0])[1],
    "trip_speed": lambda v: roots(v[1],-v[0]*v[1])[1],
    "fill_tank": fill_tank,
    "quadratic_integer_count": lambda v: sign_count(v[0],v[1]),
    "rational_integer_count": lambda v: sum(Q(x+v[0],x+v[1])<=0 for x in range(-100,101) if x+v[1]),
    "inequality_intersection": lambda v: sum(x*x+v[0]*x+v[1]<=0 and x*x>v[3] for x in range(-100,101)),
    "relative_frequency": lambda v: Q(v[0],v[0]+v[2]),
    "population_variance": lambda v: pvariance(v),
    "grouped_mean": lambda v: Q(v[0]*(v[1]+v[2])+v[3]*(v[4]+v[5])+v[6]*(v[7]+v[8]),2*(v[0]+v[3]+v[6])),
    "polygon_angles": lambda v: 180*(v[0]-v[1]),
    "parallelogram_angles": lambda v: Q(180-v[1],v[0]+1),
    "rhombus_diagonal": lambda v: exact_sqrt(Q(v[0]*v[0],4)-v[1]*v[1]),
    "trapezoid_average": lambda v: Q(v[0]+v[1],2),
    "triangle_midline_perimeter": lambda v: Q(sum(v),2),
    "trapezoid_height": lambda v: exact_sqrt(v[2]*v[2]-Q(v[1]-v[0],2)**2),
    "right_sine": lambda v: Q(v[0],v[1]),
    "right_trig_recover": lambda v: v[2]*exact_sqrt(1-Q(v[0],v[1])**2),
    "mast_height": lambda v: Q(v[4],Q(v[1],v[0])-Q(v[3],v[2])),
    "altitude_from_projections": lambda v: exact_sqrt(v[0]*v[1]),
    "leg_from_projection": lambda v: exact_sqrt(v[0]*v[1]),
    "altitude_projection_gap": lambda v: exact_sqrt(v[1]*v[1]+4*v[0]*v[0]),
    "parallelogram_area": lambda v: v[0]*v[1],
    "rhombus_unknown": lambda v: Q(2*v[0],v[1]),
    "remainder_area": lambda v: Q(11*v[0]*v[1],12),
    "midpoint_sum": lambda v: Q(sum(v),2),
    "coordinate_distance": lambda v: hypot(v[2]-v[0],v[3]-v[1]),
    "circle_chord": lambda v: 2*exact_sqrt(v[2]-(v[3]+v[1])**2),
}


def coefficient(factors, exponent):
    coefficients = [1]
    for factor in factors:
        total = [0] * (len(coefficients) + len(factor) - 1)
        for i, a in enumerate(coefficients):
            for j, b in enumerate(factor):
                total[i+j] += a*b
        coefficients = total
    return coefficients[exponent]


def arithmetic_budget(v):
    step, days, total = v
    first = next(a for a in range(1,total+1) if sum(range(a,a+step*days,step))==total)
    return sum(range(first,first+4*step,step))


def geometric_rebuild(v):
    b2, b5 = v
    ratio = next(r for r in range(1,100) if b2*r**3==b5)
    return sum(Q(b2,ratio)*ratio**index for index in range(4))


def vector_basis(v):
    x1,y1,x2,y2,x3,y3=v
    determinant=x1*y2-x2*y1
    return Q(x3*y2-x2*y3,determinant)+Q(x1*y3-x3*y1,determinant)


def recover_rotation(v):
    _,px,py,qx,qy=v
    # Centre is the midpoint of the chord plus 90°-rotated half of P→Q.
    return Q(px+qx-qy+py,2)*Q(py+qy+qx-px,2)


def triangle_area_squared(v):
    half = Q(sum(v),2)
    assert all(half-a>0 for a in v)
    return half*prod(half-a for a in v)


def cut_similar(v):
    x,y,k=v
    points=[(Q(x,k),0),(x,0),(0,y),(0,Q(y,k))]
    return abs(sum(a*d-b*c for (a,b),(c,d) in zip(points,points[1:]+points[:1])))/2


# Includes all 16 hard families, with prompt-derived numerical inputs.
GRADE9 = {
    "intersect_horizontal": lambda v: exact_sqrt(v[1]-v[0]),
    "intersect_secant": lambda v: prod(roots(-v[0],-v[1])),
    "intersect_circle": lambda v: (2*sqrt(v[2]-(v[3]+v[0])**2))**2,
    "point_gap": lambda v: v[2]-(v[0]-v[1]),
    "count_under_line": lambda v: sum(x+y<=v[3] for x in range(v[1]+1) for y in range(v[3]+1)),
    "count_exclusion": lambda v: sum(Q(y,x)<Q(v[4],v[5]) for x in range(1,v[1]+1) for y in range(1,v[3]+1)),
    "arithmetic_term": lambda v: list(range(v[0],v[0]+8*v[1],v[1]))[-1],
    "arithmetic_recover": lambda v: sum(v[0]+Q(v[1]-v[0],3)*(index-2) for index in range(v[2])),
    "arithmetic_budget": arithmetic_budget,
    "geometric_term": lambda v: v[0]*prod([v[1]]*4),
    "geometric_sum": lambda v: sum(v[0]*Q(v[1],v[0])**k for k in range(v[2])),
    "geometric_rebuild": geometric_rebuild,
    "infinite_sum": lambda v: sum(v[0]*Q(v[1],v[2])**k for k in range(65)),
    "recover_geometric_ratio": lambda v: Q(v[0]-v[1],v[0]),
    "geometric_bounces": lambda v: v[0]+2*sum(v[0]*Q(v[1],v[2])**k for k in range(1,65)),
    "counting_product": lambda v: len([(a,b) for a in range(v[0]) for b in range(v[1])]),
    "counting_places": lambda v: prod(range(v[0]-v[1]+1,v[0]+1)),
    "counting_block": lambda v: (v[0]-v[1]+1)*factorial(v[0]-v[1])*factorial(v[1]),
    "choose_team": lambda v: Q(prod(range(v[0]-v[1]+1,v[0]+1)),factorial(v[1])),
    "binomial_term": lambda v: coefficient([(v[1],v[0])]*5,3),
    "binomial_product": lambda v: coefficient([(v[0],v[1])]*3+[(v[2],v[3])]*2,2),
    "radians_from_degrees": lambda v: radians(v[0])/pi,
    "degree_winding": lambda v: (v[1]-v[0])//360,
    "circle_rays": lambda v: sum(m*v[0]%(2*v[1])==m*v[2]%(2*v[3])==0 for m in range(v[4],v[5]+1)),
    "trig_sin_squared": lambda v: Q(v[1]*v[1]-v[0]*v[0],v[1]*v[1]),
    "trig_signed_sine": lambda v: sin(atan2(v[1],v[0])),
    "trig_symmetry_fraction": lambda v: Q(v[1]+v[0],v[1]-v[0])+Q(v[1]-v[0],v[1]+v[0]),
    "cos_double": lambda v: 1-2*(1-Q(v[0],v[1])**2),
    "sum_angles": lambda v: sin(asin(v[0]/v[1])+asin(v[2]/v[3])),
    "combined_angles": lambda v: sin(2*asin(v[0]/v[1])+pi-asin(v[2]/v[3])),
    "vector_difference": lambda v: v[2]-v[0],
    "vector_collinear": lambda v: v[1]+Q(v[4]*(v[2]-v[0]),v[3]),
    "vector_basis": vector_basis,
    "dot_evaluate": lambda v: sum(a*b for a,b in zip(v[:2],v[2:])),
    "dot_perpendicular": lambda v: -Q(v[0]*v[2],v[1]),
    "dot_projection": lambda v: (hypot(*v[:2])*cos(atan2(v[1],v[0])-atan2(v[3],v[2])))**2,
    "reflect_axis": lambda v: v[0]-v[1],
    "rotate_translate": lambda v: v[1]-v[0]+v[3]+v[4],
    "recover_rotation": recover_rotation,
    "homothety_length": lambda v: prod(v),
    "similarity_area": lambda v: Q(v[1],v[0])**2*v[2],
    "cut_similar": cut_similar,
    "cosine_law_square": lambda v: hypot(v[0]-v[1]*cos(radians(v[2])), v[1]*sin(radians(v[2])))**2,
    "sine_law_ratio": lambda v: v[2]*sin(radians(v[0]))/v[1],
    "triangle_area_squared": triangle_area_squared,
    "circle_arc": lambda v: Q(v[0]*v[1],180),
    "sector_difference": lambda v: Q(360-v[1],360)*v[0]**2,
    "sector_from_chord": lambda v: Q(v[2],360)*(Q(v[0],2)**2+v[1]**2),
}


def numbers(text):
    return [int(re.sub(r"\s+", "", s.replace("−","-"))) for s in re.findall(r"(?:[+−-]\s*)?[0-9]+",text)]


def normalized(text):
    return " ".join(unicodedata.normalize("NFC",text).casefold().replace("−","-").split()).rstrip(" .?!;:")


def main():
    metrics = Counter()
    normalized_ids = defaultdict(list)
    failures = []
    single_step = set()
    samples = []
    for topic in TOPICS:
        key = topic["id"]
        metrics["topics"] += 1
        for v in range(topic["variants"]):
            q = generate(key,v)
            f = q["family"]
            ref = f"{key}:{v}"
            metrics["variants"] += 1
            metrics[f"grade {topic['grade']}"] += 1
            metrics[f"difficulty {q['difficulty']}"] += 1
            normalized_ids[normalized(q["prompt"])].append(ref)
            assert q == generate(key,v), ref
            if isinstance(q["answer"], (int, float)):
                assert isfinite(q["answer"])
            else:
                assert q.get("response", {}).get("kind") in ("pair", "interval", "choice", "sequence", "graph", "roots", "interval_set", "expression", "data_plot"), ref
                metrics["structured answers"] += 1
            metrics[f"hints {len(q['hints'])}"] += 1
            metrics[f"solution steps {len(q['solution'])}"] += 1
            if len(q["solution"]) == 1:
                single_step.add((key, f))
                if q["solution"][0] in q["hints"]:
                    metrics["complete solution in hint"] += 1
            assert q["hints"] and q["solution"], ref
            if v % VARIANTS_PER_FAMILY in (0,56,99):
                samples.append(ref)
            oracles = GRADE8 if key.startswith("g8-") else GRADE9 if key.startswith("g9-") else None
            if oracles and f in oracles and isinstance(q["answer"], (int, float)):
                try:
                    digits = numbers(q["prompt"])
                    expected = oracles[f](digits)
                    metrics["prompt oracles grade "+str(topic["grade"])] += 1
                    if abs(expected - q["answer"]) > max(1e-10,abs(expected)*1e-12):
                        failures.append((ref,f,digits,q["answer"],str(expected)))
                except (ValueError,KeyError,IndexError,StopIteration,ZeroDivisionError,AssertionError) as ex:
                    failures.append((ref,f,q["prompt"],str(ex)))
    duplicates = [group for group in normalized_ids.values() if len(group)>1]
    print(dict(metrics))
    print("Fixed sample records:",len(samples))
    print("Normalized duplicate groups:",len(duplicates),duplicates[:20])
    print("One-step families:", sorted(single_step))
    print("Grade 8/9 prompt-oracle checker discrepancies:",len(failures),
          {name: next(row for row in failures if row[1] == name) for name in sorted({row[1] for row in failures})})
    assert not failures, "Audit oracles disagree (check the harness and task separately)"


if __name__ == "__main__":
    main()
