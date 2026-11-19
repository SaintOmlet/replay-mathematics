"""Stable curriculum registry over the original bank and grade modules."""

from .content import TOPICS as LEGACY_TOPICS
from .content import VARIANTS_PER_FAMILY, PARAMETER_VALUES, generate as legacy_generate
from .content import linear_isolate, systems_sum, quadratic_tangent
from . import grade7, grade8, grade9, curriculum_extensions, graph_curriculum, set_curriculum, sat_curriculum, complete_grade7, complete_grade8, complete_grade9, statistics_curriculum

LEVELS = ("easy", "medium", "hard")
LEGACY_LEVELS = {
    "linear": (0, 1, 1, 1), "percent": (0, 0, 1, 1), "lines": (0, 1, 0, 0),
    "systems": (0, 2, 1, 2), "triangles": (0, 1, 1, 1), "powers": (0, 1, 0, 0),
    "quadratics": (0, 1, 1, 2), "exponential": (0, 1, 2, 1),
    "statistics": (0, 1, 0, 2), "probability": (0, 2, 1, 2),
}
LEVEL_OVERRIDES = {
    "g8-complete-square": (0, 1, 1), "g7-congruence": (0, 1, 1),
    "g7-factorization": (0, 1, 1), "g7-algebraic-fractions": (0, 1, 1),
    "g7-circle-tangency": (0, 1, 1), "g7-adjacent-vertical": (0, 1, 1),
    "g8-radicals": (0, 1, 1), "g8-discriminant": (0, 1, 1),
    "g9-triangle-laws": (0, 1, 1),
}
EXTRA_FAMILIES = {"linear": linear_isolate, "systems": systems_sum, "quadratics": quadratic_tangent}
EXTRA_FIRST_SEED = 1000
EXTRA_PARAMETER_VALUES = 1000
EXTRA_LAST_SEED = EXTRA_FIRST_SEED + EXTRA_PARAMETER_VALUES ** 2 - 1
GRADE_MODULES = (grade7, grade8, grade9, curriculum_extensions, graph_curriculum, set_curriculum, complete_grade7, complete_grade8, complete_grade9, statistics_curriculum, sat_curriculum)
FAMILY_LEVELS = {key: levels for module in GRADE_MODULES for key, levels in getattr(module,"LEVELS_BY_TOPIC",{}).items()}
FAMILIES = {key: families for module in GRADE_MODULES for key, families in module.FAMILIES.items()}
LEGACY_LESSONS = {key: extra for module in GRADE_MODULES for key, extra in module.LEGACY_LESSONS.items()}

TOPICS = [
    {**entry, "section": "Школьная математика", **LEGACY_LESSONS.get(entry["id"], {}), "satReady": True}
    for entry in LEGACY_TOPICS
]
for module in GRADE_MODULES:
    for entry in module.TOPICS:
        family_count = len(FAMILIES[entry["id"]])
        TOPICS.append({
            **entry, "satReady": bool(entry.get("satReady",False)), "variants": family_count * VARIANTS_PER_FAMILY,
            "families": family_count,
        })

TOPICS.sort(key=lambda entry: (entry["grade"], entry.get("order", 100)))
TOPIC_BY_ID = {entry["id"]: entry for entry in TOPICS}
if len(TOPIC_BY_ID) != len(TOPICS):
    raise ValueError("Duplicate curriculum topic ID")
for entry in TOPICS:
    applications = ([entry["id"]] if entry["satReady"] else [])
    applications.extend(sat_curriculum.SCHOOL_APPLICATIONS.get(entry["id"], ()))
    if applications:
        entry["satApplications"] = list(dict.fromkeys(applications))


def difficulty(topic_id, variant):
    if variant >= EXTRA_FIRST_SEED and topic_id in EXTRA_FAMILIES:
        return "easy" if topic_id != "quadratics" else "medium"
    family, _ = divmod(variant, VARIANTS_PER_FAMILY)
    levels = LEGACY_LEVELS.get(topic_id, LEVEL_OVERRIDES.get(topic_id))
    if topic_id in FAMILY_LEVELS:
        return FAMILY_LEVELS[topic_id][family]
    return LEVELS[levels[family] if levels is not None else family]


def public_topics():
    return [
        {**{key: value for key, value in topic.items() if key not in ("lesson", "formula")},
         "difficultyCounts": {
             level: sum(difficulty(topic["id"], variant) == level for variant in range(0, topic["variants"], VARIANTS_PER_FAMILY))
             * VARIANTS_PER_FAMILY for level in LEVELS
         }}
        for topic in TOPICS
    ]


def lesson(topic_id):
    topic = TOPIC_BY_ID[topic_id]
    body = topic["lesson"]
    if isinstance(body, list):
        body = {"theory": body}
    return {"id": topic_id, "formula": topic["formula"], **body}


def supports_seed(topic_id, seed):
    topic = TOPIC_BY_ID.get(topic_id)
    return topic is not None and type(seed) is int and (
        0 <= seed < topic["variants"]
        or topic_id in EXTRA_FAMILIES and EXTRA_FIRST_SEED <= seed <= EXTRA_LAST_SEED
    )


def generate(topic_id, variant, lang="ru"):
    if lang not in ("ru", "en"):
        raise ValueError("Unknown language")
    if not supports_seed(topic_id, variant):
        raise ValueError("Unknown problem ID")
    family = None
    if variant >= EXTRA_FIRST_SEED and topic_id in EXTRA_FAMILIES:
        family = EXTRA_FAMILIES[topic_id]
        i, j = divmod(variant - EXTRA_FIRST_SEED, EXTRA_PARAMETER_VALUES)
        raw = family(i + PARAMETER_VALUES, j)
    elif topic_id in LEGACY_LEVELS:
        exercise = legacy_generate(topic_id, variant, lang)
    else:
        family_index, pair = divmod(variant, VARIANTS_PER_FAMILY)
        i, j = divmod(pair, PARAMETER_VALUES)
        family = FAMILIES[topic_id][family_index]
        raw = family(i, j)
    if family is not None:
        exercise = {
            **{key: raw[key] for key in ("answer", "hints", "solution", "graph", "verify", "response", "diagnostics") if key in raw},
            "prompt": raw[lang],
            "family": family.__name__,
        }
    return {**exercise, "difficulty": difficulty(topic_id, variant), "seed": variant}
