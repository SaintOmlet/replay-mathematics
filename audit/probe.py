"""Read-only audit probes against a disposable Replay database; run from the project root."""

from collections import Counter
from fractions import Fraction
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
import json

from backend.curriculum import TOPICS, difficulty, generate
from backend.storage import StudyStore, parse_answer
from backend.grading import sat_matches, sat_input_available


def state_probes():
    clock = [1_000.0]
    with TemporaryDirectory() as tmp:
        store = StudyStore(tmp, clock=lambda: clock[0])
        store.complete_lesson("linear")
        used_with_help = []
        for seed in (0, 1, 2, 100, 101, 300):
            clock[0] += 1
            state = store.start({"mode": "practice", "count": 1, "problemId": f"linear:{seed}"})
            for _ in range(2):
                store.access(state["id"], "hint", {"index": 0})
            state = store.access(state["id"], "answer", {
                "index": 0, "answer": str(generate("linear", seed)["answer"]),
            })
            used_with_help.append(difficulty("linear", seed))
            store.access(state["id"], "next", {"index": 0})
        linear = next(t for t in store.progress()["topics"] if t["id"] == "linear")

        test = store.start({"mode": "test", "topics": ["linear"], "count": 3, "secondsPerQuestion": 60})
        clock[0] += 3_600
        progress_before = store.progress()
        read = store.access(test["id"])
        assert read["answered"] == 0 and read["index"] == 0 and read["expired"]
        updated = store.access(test["id"], "expire", {"index":0})
        assert updated["answered"] == 1 and updated["index"] == 1
        assert updated["remainingSeconds"] == 60

        practice = store.start({"mode": "practice", "topics": ["linear"], "count": 1})
        assert store.progress()["active"]["id"] == practice["id"]
        assert not store.access(test["id"])["finished"]
        clock[0] += 1
        current_prompt = practice["question"]["prompt"]
        store.access(practice["id"], "answer", {"index": 0, "answer": None})
        store.access(practice["id"], "next", {"index": 0})
        revived = StudyStore(tmp, clock=lambda: clock[0])
        assert revived.access(practice["id"])["results"][0]["prompt"] == current_prompt

        return {
            "mastered_after_two_hints_on_each_attempt": linear["mastered"],
            "hinted_levels": used_with_help,
            "background_test_after_return": {
                "active_before_open": progress_before["active"]["mode"],
                "questions_counted_as_answered": updated["answered"],
                "new_time_allowed_seconds": updated["remainingSeconds"],
                "read_only_get_preserves_unanswered_question": read["answered"] == 0,
                "all_unfinished_sessions_listed": {entry["id"] for entry in store.progress()["activeSessions"]} == {test["id"]},
                "older_session_still_accessible_by_its_url": True,
            }
        }


def bank_probes():
    sat = [t for t in TOPICS if t["satReady"]]
    unique_format = None
    impossible_probabilities = 0
    impossible_example = None
    mixed_formats = 0
    oversized_spr_keys = 0
    for topic in sat:
        for seed in range(topic["variants"]):
            question = generate(topic["id"], seed, "en")
            target = question["answer"]
            if question.get("response", {}).get("kind") == "choice":
                choices = question["response"]["options"]
                assert len(choices) == len({option["label"] for option in choices}) == 4
                assert sum(option["value"] == target for option in choices) == 1
                continue
            choices = StudyStore.options(topic["id"], seed, target)
            values = [parse_answer(choice) for choice in choices]
            assert len(set(values)) == 4
            assert sum(StudyStore.matches(value, target) for value in values) == 1
            if len({"/" in choice for choice in choices}) != 1:
                mixed_formats += 1
                if unique_format is None:
                    unique_format = (topic["id"], seed, target, choices)
            if not sat_input_available(target):
                oversized_spr_keys += 1
            if (topic["id"] == "probability" or topic.get("answerRange") == [0,1]) and any(not 0 <= option <= 1 for option in values):
                impossible_probabilities += 1
                impossible_example = impossible_example or (topic["id"], seed, target, choices)

    families = Counter((t["grade"], t["id"], generate(t["id"], i)["family"])
                       for t in TOPICS for i in range(t["variants"]))
    return {
        "catalog_topics": len(TOPICS), "indexed_variants": sum(families.values()), "registered_families": len(families),
        "sets_with_mixed_fraction_formats": mixed_formats,
        "mixed_format_example": unique_format,
        "oversized_keys_rendered_as_multiple_choice": oversized_spr_keys,
        "probability_sets_with_an_impossible_option_out_of_400": impossible_probabilities,
        "impossible_probability_example": impossible_example,
        "fraction_and_decimal_are_equivalent_when_exact": StudyStore.matches(Fraction(1, 3), 1/3),
        "sat_accepts_official_two_thirds_forms": all(sat_matches(v,2/3) for v in ("2/3", ".6666", ".6667", "0.666", "0.667")),
    }


def profile_summary():
    reports = {}
    with TemporaryDirectory() as tmp:
        store = StudyStore(tmp)
        previous = 0
        for count in (100, 1_000, 5_000):
            with store.transaction() as conn:
                for i in range(previous, count):
                    store.save(conn, {
                        "id": f"{i:032x}", "mode": "test", "lang": "ru",
                        "questions": [["linear", seed] for seed in range(10)],
                        "outcomes": {str(k): {"correct": k % 2 == 0, "seconds": 7, "submitted": "1", "timedOut": False}
                                     for k in range(10)},
                        "finishedAt": "2026-11-16T12:00:00+00:00",
                        "elapsedSeconds": 70,
                    })
            previous = count
            timings, cold = [], []
            expected = store.progress()
            for _ in range(5):
                store._progress_cache = None
                start = perf_counter()
                uncached = store.progress()
                cold.append((perf_counter() - start) * 1000)
                start = perf_counter()
                cached = store.progress()
                timings.append((perf_counter() - start) * 1000)
                assert expected == uncached == cached, "Cached summary differs"
            reports[str(count)] = {"uncached_median_ms":round(median(cold),1),
                                   "cached_median_ms":round(median(timings),1), "results_identical":True}
    return reports


if __name__ == "__main__":
    print(json.dumps({"flows": state_probes(), "bank": bank_probes(), "synthetic_summary_median_ms": profile_summary()}, indent=2))
