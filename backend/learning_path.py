"""Small, deterministic study recommendations from recorded learning evidence.

Recommendations never lock topics. They point to the first unconfirmed foundation
of a selected topic, then to unfinished work in the learner's chosen grade.
"""

from .curriculum import TOPICS, TOPIC_BY_ID, VARIANTS_PER_FAMILY, difficulty


# These are teaching dependencies, not an estimate of the learner's ability.
# The graph topics are registered by the graph curriculum extension.
PREREQUISITES = {
    "linear": (),
    "percent": (),
    "lines": ("linear",),
    "g7-integer-powers": (),
    "g7-scientific-notation": ("g7-integer-powers",),
    "g7-monomials": ("g7-integer-powers",),
    "g7-polynomials": ("g7-monomials",),
    "g7-identities": ("g7-polynomials",),
    "g7-factorization": ("g7-identities",),
    "g7-algebraic-fractions": ("g7-factorization",),
    "g7-basic-curves": ("lines", "g7-integer-powers"),
    "g7-frequencies": ("percent",),
    "g7-linear-inequalities": ("linear",),
    "g7-adjacent-vertical": ("linear",),
    "g7-parallel-transversal": ("g7-adjacent-vertical",),
    "g7-triangle-angles": ("g7-parallel-transversal",),
    "g7-congruence": ("g7-proof-methods", "g7-triangle-angles"),
    "g7-isosceles": ("g7-congruence",),
    "g7-triangle-inequality": ("g7-triangle-angles",),
    "g7-circle-tangency": ("g7-congruence",),
    "g7-proof-methods": (),
    "g7-compass-methods": ("g7-congruence",),
    "g7-triangle-constructions": ("g7-compass-methods", "g7-triangle-inequality"),
    "g7-systems-full-pair": ("lines",),
    "g7-measurement-errors": ("percent", "g7-scientific-notation"),
    "powers": ("g7-integer-powers",),
    "systems": ("g7-systems-full-pair",),
    "g8-real-roots": ("powers",),
    "g8-radicals": ("g8-real-roots", "g7-identities"),
    "g8-root-graph": ("g8-real-roots", "lines"),
    "g8-discriminant": ("g7-polynomials", "g8-real-roots"),
    "g8-vieta": ("g8-discriminant", "g7-factorization"),
    "g8-complete-square": ("g7-identities", "g8-discriminant"),
    "g8-substitution": ("g8-discriminant",),
    "g8-rational-equations": ("g7-algebraic-fractions", "g8-discriminant"),
    "g8-quadratic-models": ("g8-discriminant", "linear"),
    "g8-inequalities": ("g7-linear-inequalities", "g8-vieta"),
    "g8-frequency-variance": ("g7-frequencies",),
    "g8-quadrilaterals": ("g7-triangle-angles", "g7-congruence"),
    "g8-midlines-trapezoid": ("g8-quadrilaterals",),
    "triangles": ("g7-triangle-angles", "g8-real-roots"),
    "g8-right-trig": ("triangles",),
    "g8-right-metric": ("triangles", "g8-radicals"),
    "g8-areas": ("g8-quadrilaterals", "triangles"),
    "g8-coordinate-geometry": ("lines", "triangles"),
    "g8-modulus-quadratics": ("g8-discriminant",),
    "g8-full-intervals": ("g8-inequalities",),
    "g8-thales": ("g7-parallel-transversal",),
    "g8-interval-frequencies": ("g7-frequencies",),
    "quadratics": ("g8-complete-square", "g8-vieta"),
    "exponential": ("powers", "percent"),
    "statistics": ("g8-frequency-variance",),
    "probability": ("percent", "g9-counting"),
    "g9-nonlinear-systems": ("systems", "g8-discriminant"),
    "g9-plane-inequalities": ("g8-full-intervals", "lines"),
    "g9-arithmetic-progression": ("linear",),
    "g9-geometric-progression": ("powers", "g9-arithmetic-progression"),
    "g9-infinite-series": ("g9-geometric-progression",),
    "g9-counting": (),
    "g9-binomial": ("g9-counting", "g7-identities"),
    "g9-unit-circle": ("g8-right-trig",),
    "g9-trig-identities": ("g9-unit-circle", "g7-identities"),
    "g9-angle-formulas": ("g9-trig-identities",),
    "g9-coordinates-vectors": ("g8-coordinate-geometry", "systems"),
    "g9-dot-product": ("g9-coordinates-vectors", "g8-right-trig"),
    "g9-plane-isometries": ("g8-coordinate-geometry",),
    "g9-similarity-homothety": ("g8-thales", "g8-areas"),
    "g9-triangle-laws": ("g8-right-trig", "g8-areas"),
    "g9-arcs-sectors": ("g9-unit-circle", "percent"),
    "g9-induction": ("g7-proof-methods", "g9-arithmetic-progression"),
    "g9-periodic-fractions": ("g9-infinite-series",),
    "g9-inscribed-chords": ("g7-circle-tangency", "g9-similarity-homothety"),
    "g7-line-graphs": ("lines",),
    "g8-parabola-graphs": ("g8-complete-square", "g8-discriminant"),
    "g8-graph-reading": ("g7-line-graphs", "g8-parabola-graphs", "systems"),
    "g8-modulus-solutions": ("g8-modulus-quadratics", "g8-discriminant"),
    "g8-quadratic-solution-sets": ("g8-inequalities", "g8-full-intervals"),
    "g8-rational-systems-sets": ("g8-quadratic-solution-sets", "g7-linear-inequalities"),
}


PREREQUISITES.update({topic["id"]: tuple(topic["prerequisites"])
                      for topic in TOPICS if "prerequisites" in topic})


def validate_prerequisites(prerequisites=None):
    """Reject broken authoring data before recommendations reach learners."""
    graph = PREREQUISITES if prerequisites is None else prerequisites
    visiting, visited = set(), set()

    def visit(topic):
        if topic not in graph:
            raise ValueError(f"Unknown prerequisite topic: {topic}")
        if topic in visiting:
            raise ValueError(f"Prerequisite cycle at {topic}")
        if topic in visited:
            return
        visiting.add(topic)
        for prerequisite in graph[topic]:
            visit(prerequisite)
        visiting.remove(topic)
        visited.add(topic)

    for topic in graph:
        visit(topic)


def _count(row, key):
    value = row.get(key, 0)
    return value if type(value) is int and value >= 0 else 0


def _practice_reason(row, topic):
    attempts, correct = _count(row, "independentAttempted"), _count(row, "independentCorrect")
    if _count(row, "answered") and not attempts:
        return "В истории пока нет подтверждённых самостоятельных ответов. Реши новые варианты без помощи."
    if attempts and correct * 5 < attempts * 4:
        return f"Самостоятельно верно {correct} из {attempts}. Потренируй применение правила на новых задачах."
    if attempts < 6:
        return f"Самостоятельно проверено разных задач — {attempts}. Для подтверждения темы нужно минимум 6."
    if _count(row, "distinctFamilies") < min(3, topic["families"]):
        return "Проверь другие типы задач этой темы самостоятельными решениями."
    levels = {difficulty(topic["id"], seed) for seed in range(0, topic["variants"], VARIANTS_PER_FAMILY)}
    if "medium" in levels and _count(row, "mediumCorrect") < 2:
        return "Для подтверждения темы нужны ещё самостоятельные верные решения среднего уровня."
    if "hard" in levels and not _count(row, "hardCorrect"):
        return "Для подтверждения темы нужно самостоятельное верное решение сложного уровня."
    return "Продолжи практику новыми вариантами этой темы."


def plan(report):
    """Return up to three optional next actions; never mutate progress or mastery."""
    validate_prerequisites()
    report = report if isinstance(report, dict) else {}
    rows = report.get("topics", [])
    rows = rows if isinstance(rows, list) else []
    stats = {row["id"]: row for row in rows if isinstance(row, dict)
             and isinstance(row.get("id"), str) and row["id"] in TOPIC_BY_ID}
    active = report.get("activeSessions", [])
    active = active if isinstance(active, list) else []
    active_topics = [row["topic"] for row in active if isinstance(row, dict)
                     and isinstance(row.get("topic"), str) and row["topic"] in TOPIC_BY_ID]
    recent = report.get("recent", [])
    recent = recent if isinstance(recent, list) else []
    recent_topics = [topic for row in recent if isinstance(row, dict) and isinstance(row.get("topics"), list)
                     for topic in row["topics"] if isinstance(topic, str) and topic in TOPIC_BY_ID]
    started = [topic["id"] for topic in TOPICS if stats.get(topic["id"], {}).get("lessonCompleted")
               or _count(stats.get(topic["id"], {}), "answered")
               or _count(stats.get(topic["id"], {}), "independentAttempted")]
    interest = active_topics + recent_topics + started
    grade = TOPIC_BY_ID[interest[0]]["grade"] if interest else 7
    weak = [topic for topic in started if _count(stats[topic], "independentAttempted")
            and _count(stats[topic], "independentCorrect") * 5 < _count(stats[topic], "independentAttempted") * 4]
    weak.sort(key=lambda topic: (
        _count(stats[topic], "independentCorrect") / _count(stats[topic], "independentAttempted"),
        -_count(stats[topic], "independentAttempted"),
    ))
    fresh = sorted(TOPICS, key=lambda topic: (topic["grade"] != grade, topic["grade"]))
    goals = active_topics + weak + recent_topics + started + [topic["id"] for topic in fresh]

    def first_unconfirmed(topic):
        for prerequisite in PREREQUISITES.get(topic, ()):
            if not stats.get(prerequisite, {}).get("mastered"):
                return first_unconfirmed(prerequisite)
        return topic

    recommendations, selected = [], set()
    for goal in goals:
        if stats.get(goal, {}).get("mastered"):
            continue
        target = first_unconfirmed(goal)
        if target in selected or target not in TOPIC_BY_ID:
            continue
        row, topic = stats.get(target, {}), TOPIC_BY_ID[target]
        action = "practice" if row.get("lessonCompleted") else "lesson"
        # The existing resume list already points to the active question. Avoid
        # suggesting another fresh session instead of that unfinished practice.
        if target in active_topics and action == "practice":
            continue
        if action == "lesson":
            reason = "Разбери теорию и примеры, затем выполни самопроверку."
            if _count(row, "answered"):
                reason = "Практика уже начата. Заверши теорию и самопроверку этой темы."
        else:
            reason = _practice_reason(row, topic)
        recommendation = {"topic": target, "title": topic["title"], "reason": reason, "action": action}
        if target != goal:
            recommendation["prerequisite"] = goal
            recommendation["reason"] = f"Основа для темы «{TOPIC_BY_ID[goal]['title']}». " + reason
        recommendations.append(recommendation)
        selected.add(target)
        if len(recommendations) == 3:
            break
    return recommendations
