"""Aggregate actual answers and completed lessons into learner progress."""

from .curriculum import LEVELS, TOPICS, TOPIC_BY_ID, difficulty, generate, public_topics
from .learning_path import plan


def counters():
    return {"answered": 0, "correct": 0, "timedAnswers": 0, "seconds": 0,
            "independent": 0, "assisted": 0, "unknown": 0}


def add_answer(target, outcome):
    target["answered"] += 1
    target["correct"] += int(outcome["correct"])
    target[outcome.get("assistance", "unknown")] += 1
    seconds = outcome.get("seconds")
    if seconds is not None:
        target["timedAnswers"] += 1
        target["seconds"] += seconds


def latest_answers(history):
    """History is newest session first; use the latest real outcome for each seed."""
    outcomes = {}
    for session in history:
        for index, result in session["outcomes"].items():
            question = tuple(session["questions"][int(index)])
            if question[0] not in TOPIC_BY_ID:
                continue
            previous = outcomes.get(question)
            if previous is None or (
                result.get("recordedAt") is not None
                and (previous.get("recordedAt") is None or result["recordedAt"] > previous["recordedAt"])
            ):
                outcomes[question] = result
    return outcomes


def summarize(history, completed):
    stats = {
        entry["id"]: {
            "id": entry["id"], **counters(), "lessonCompleted": entry["id"] in completed,
            "distinctAttempted": 0, "distinctCorrect": 0,
            "mediumCorrect": 0, "hardCorrect": 0, "mistakes": 0,
            "independentAttempted": 0, "independentCorrect": 0, "distinctFamilies": 0,
        }
        for entry in TOPICS
    }
    grades = {entry: {"grade": entry, "topics": 0, "mastered": 0, "lessons": 0, **counters()} for entry in (7, 8, 9)}
    levels = {level: {"level": level, **counters()} for level in LEVELS}
    recent = []
    active = None
    active_sessions = []
    for session in history:
        known = session["outcomes"]
        for index, outcome in known.items():
            topic_id, variant = session["questions"][int(index)]
            if topic_id not in stats:
                continue
            add_answer(stats[topic_id], outcome)
            add_answer(grades[TOPIC_BY_ID[topic_id]["grade"]], outcome)
            stored_levels = session.get("recordedDifficulties")
            level = stored_levels[int(index)] if stored_levels else difficulty(topic_id, variant)
            add_answer(levels[level], outcome)
        if session["finishedAt"]:
            timed = [outcome["seconds"] for outcome in known.values() if outcome.get("seconds") is not None]
            recent.append({
                "id": session["id"], "mode": session["mode"], "lang": session["lang"],
                "answered": len(known), "correct": sum(item["correct"] for item in known.values()),
                "total": len(session["questions"]), "finishedAt": session["finishedAt"],
                "elapsedSeconds": session.get("elapsedSeconds", sum(timed) if timed else None),
                "difficulty": session.get("difficulty", "mixed"),
                "topics": list(dict.fromkeys(q[0] for q in session["questions"])),
            })
        else:
            if active is None:
                active = {"id": session["id"], "mode": session["mode"]}
            topic_id = session["questions"][session["index"]][0]
            active_sessions.append({
                "id": session["id"], "mode": session["mode"], "lang": session["lang"],
                "topic": topic_id, "title": TOPIC_BY_ID[topic_id]["title"],
                "index": session["index"], "total": len(session["questions"]),
                "deadline": session.get("deadline"),
                "secondsPerQuestion": session.get("secondsPerQuestion"),
            })

    family_sets = {topic["id"]: set() for topic in TOPICS}
    for (topic_id, variant), outcome in latest_answers(history).items():
        entry = stats[topic_id]
        entry["distinctAttempted"] += 1
        entry["distinctCorrect"] += int(outcome["correct"])
        entry["mistakes"] += int(not outcome["correct"])
        level = difficulty(topic_id, variant)
        independent = outcome.get("assistance") == "independent"
        entry["independentAttempted"] += int(independent)
        entry["independentCorrect"] += int(independent and outcome["correct"])
        if independent and outcome["correct"]:
            family_sets[topic_id].add(generate(topic_id, variant)["family"])
        if independent and outcome["correct"] and level in ("medium", "hard"):
            entry[level + "Correct"] += 1

    level_counts = {topic["id"]: topic["difficultyCounts"] for topic in public_topics()}
    for topic in TOPICS:
        entry = stats[topic["id"]]
        entry["distinctFamilies"] = len(family_sets[topic["id"]])
        required_families = min(3, topic["families"])
        required_medium = 2 if level_counts[topic["id"]]["medium"] else 0
        required_hard = 1 if level_counts[topic["id"]]["hard"] else 0
        entry["mastered"] = (
            entry["lessonCompleted"]
            and entry["independentAttempted"] >= 6
            and 5 * entry["independentCorrect"] >= 4 * entry["independentAttempted"]
            and entry["distinctFamilies"] >= required_families
            and entry["mediumCorrect"] >= required_medium
            and entry["hardCorrect"] >= required_hard
        )
        needs = []
        if not entry["lessonCompleted"]:
            needs.append("завершить урок")
        if entry["independentAttempted"] < 6:
            needs.append(f"самостоятельно решить новые задачи (осталось {6-entry['independentAttempted']})")
        if entry["distinctFamilies"] < required_families:
            needs.append(f"верно решить задачи новых типов (осталось {required_families-entry['distinctFamilies']})")
        if entry["mediumCorrect"] < required_medium:
            needs.append(f"самостоятельно решить средние задачи (ещё {required_medium-entry['mediumCorrect']})")
        if entry["hardCorrect"] < required_hard:
            needs.append(f"самостоятельно решить сложные задачи (ещё {required_hard-entry['hardCorrect']})")
        if entry["independentAttempted"] and 5 * entry["independentCorrect"] < 4 * entry["independentAttempted"]:
            needs.append("поднять самостоятельную точность до 80%")
        entry["nextStep"] = "Освоена" if entry["mastered"] else ". ".join(needs)
        grade = grades[topic["grade"]]
        grade["topics"] += 1
        grade["mastered"] += int(entry["mastered"])
        grade["lessons"] += int(entry["lessonCompleted"])

    recent.sort(key=lambda item: item["finishedAt"], reverse=True)
    report = {
        "answered": sum(x["answered"] for x in stats.values()),
        "correct": sum(x["correct"] for x in stats.values()),
        "mastered": sum(x["mastered"] for x in stats.values()),
        "lessonsCompleted": sum(x["lessonCompleted"] for x in stats.values()),
        "mistakeCount": sum(x["mistakes"] for x in stats.values()),
        "sessions": len(recent), "topics": list(stats.values()), "grades": list(grades.values()),
        "activeSessions": active_sessions,
        "levels": list(levels.values()), "recent": recent[:15], "active": active,
        "testTrend": [item for item in recent if item["mode"] == "test"][:8][::-1],
    }
    report["recommendations"] = plan(report)
    return report
