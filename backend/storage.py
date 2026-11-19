"""Generate and grade practice sessions using a local SQLite database."""

import json
import math
import random
import re
import sqlite3
import time
import uuid
import threading
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .curriculum import LEVELS, TOPICS, TOPIC_BY_ID, VARIANTS_PER_FAMILY, difficulty, generate, lesson, public_topics, supports_seed
from .progress import latest_answers, summarize
from . import grading
from .diagnostics import explain, graph_description


TEST_SECONDS = 240
SCHEMA_VERSION = 1
TEST_DURATIONS = {60, 120, TEST_SECONDS, 360}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def parse_answer(raw):
    try:
        return grading.parse_number(raw)
    except grading.AnswerError as error:
        raise ApiError(400, str(error)) from None


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StudyStore:
    def __init__(self, data_dir, clock=time.time):
        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "study.sqlite3"
        self.clock = clock
        self._progress_cache = None
        self._cache_lock = threading.RLock()
        with self.transaction() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("Эта база создана более новой версией Replay.")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL
                )
                """
            )
            if version == 0:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS completed_lessons (
                        topic_id TEXT PRIMARY KEY NOT NULL,
                        completed_at TEXT NOT NULL
                    )
                """)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextmanager
    def transaction(self, write=True):
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def load_all(conn):
        rows = conn.execute("SELECT body FROM sessions ORDER BY ordinal DESC")
        return [json.loads(row[0]) for row in rows]

    def save(self, conn, session):
        conn.execute(
            """INSERT INTO sessions (id, body) VALUES (?, ?)
               ON CONFLICT(id) DO UPDATE SET body = excluded.body""",
            (session["id"], json.dumps(session, ensure_ascii=False)),
        )
        with self._cache_lock:
            self._progress_cache = None

    @staticmethod
    def catalog():
        return {"topics": public_topics(), "questionCount": sum(t["variants"] for t in TOPICS)}

    def get_lesson(self, topic_id):
        if topic_id not in TOPIC_BY_ID:
            raise ApiError(404, "Тема не найдена.")
        with self.transaction(write=False) as conn:
            row = conn.execute("SELECT completed_at FROM completed_lessons WHERE topic_id = ?", (topic_id,)).fetchone()
        return {**lesson(topic_id), "completed": row is not None}

    def complete_lesson(self, topic_id):
        if topic_id not in TOPIC_BY_ID:
            raise ApiError(404, "Тема не найдена.")
        with self.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO completed_lessons VALUES (?, ?)", (topic_id, timestamp()))
            with self._cache_lock:
                self._progress_cache = None
        return {"completed": True}

    def start(self, payload):
        mode = payload.get("mode")
        lang = payload.get("lang", "ru")
        topics = payload.get("topics", [])
        count = payload.get("count")
        level = payload.get("difficulty", "mixed")
        time_limit = payload.get("secondsPerQuestion", TEST_SECONDS) if mode == "test" else None
        replay = payload.get("reviewStrategy", "fresh")
        source = payload.get("sourceSessionId")
        problem_id = payload.get("problemId")
        if mode not in ("practice", "test", "review") or lang not in ("ru", "en"):
            raise ApiError(400, "Выбери режим и язык заданий.")
        if type(count) is not int or not 1 <= count <= 40:
            raise ApiError(400, "В тренировке может быть от 1 до 40 задач.")
        if level not in ("mixed", *LEVELS):
            raise ApiError(400, "Выбери допустимый уровень сложности.")
        if time_limit is not None and (type(time_limit) is not int or time_limit not in TEST_DURATIONS):
            raise ApiError(400, "Выбери допустимый лимит времени.")
        if replay not in ("fresh", "exact") or (mode != "review" and replay == "exact"):
            raise ApiError(400, "Выбери допустимый режим повторения.")
        if source is not None and (not isinstance(source, str) or mode != "review"):
            raise ApiError(400, "Не удалось определить исходную сессию.")
        fixed_question = None
        if problem_id is not None:
            match = re.fullmatch(r"([a-z0-9-]+):([0-9]{1,10})", problem_id) if isinstance(problem_id, str) else None
            if mode != "practice" or not match:
                raise ApiError(400, "Введи код задачи в формате тема:номер, например linear:130.")
            fixed_topic, variant = match[1], int(match[2])
            topic = TOPIC_BY_ID.get(fixed_topic)
            if not supports_seed(fixed_topic, variant) or (lang == "en" and not topic["satReady"]):
                raise ApiError(404, "Задача с таким кодом не найдена.")
            fixed_question = [fixed_topic, variant]
        if not isinstance(topics, list) or any(
            not isinstance(topic, str) or topic not in TOPIC_BY_ID for topic in topics
        ):
            raise ApiError(400, "Выбрана неизвестная тема.")
        topics = list(dict.fromkeys(topics))
        if lang == "en" and any(not TOPIC_BY_ID[topic]["satReady"] for topic in topics):
            raise ApiError(400, "В SAT Math доступны только англоязычные темы.")
        with self.transaction() as conn:
            history = self.load_all(conn)
            attempted, missed = self.performance(history)
            selected_history = history
            if source:
                selected_history = [item for item in history if item["id"] == source and item["finishedAt"]]
                if not selected_history:
                    raise ApiError(404, "Завершённая сессия не найдена.")
                _, missed = self.performance(selected_history)
            if fixed_question:
                questions = [fixed_question]
            elif replay == "exact":
                outcomes = latest_answers(selected_history)
                questions = [
                    list(question) for question, outcome in outcomes.items()
                    if not outcome["correct"]
                    and (not topics or question[0] in topics)
                    and (lang == "ru" or TOPIC_BY_ID[question[0]]["satReady"])
                    and (level == "mixed" or difficulty(*question) == level)
                ][:count]
                if not questions:
                    raise ApiError(400, "Ошибок для повторения пока нет.")
            elif mode == "review":
                missed_order = sorted(missed, key=lambda key: missed[key], reverse=True)
                topics = [key for key in missed_order if (not topics or key in topics)
                          and (lang == "ru" or TOPIC_BY_ID[key]["satReady"])]
                if not topics:
                    raise ApiError(400, "В выбранных темах пока нет ошибок для повторения.")
            elif not topics:
                raise ApiError(400, "Выбери хотя бы одну тему.")
            if replay != "exact" and not fixed_question:
                reserved = {tuple(question) for item in history[:3] for question in item["questions"]}
                questions = self.select_questions(topics, attempted | reserved, count, level)
            now = self.clock()
            session = {
                "id": uuid.uuid4().hex,
                "mode": mode,
                "lang": lang,
                "index": 0,
                "questions": questions,
                "outcomes": {},
                "hintCount": 0,
                "assistanceVersion": 1,
                "coachUsed": False,
                "priorExposure": [tuple(question) in attempted for question in questions],
                "recordedDifficulties": [difficulty(*question) for question in questions],
                "difficulty": level,
                "secondsPerQuestion": time_limit,
                "questionStartedAt": now,
                "deadline": now + time_limit if time_limit is not None else None,
                "finishedAt": None,
            }
            self.save(conn, session)
            return self.state(session, now)

    @staticmethod
    def performance(history):
        outcomes = latest_answers(history)
        missed = {}
        for (topic, _), result in outcomes.items():
            if not result["correct"]:
                missed[topic] = missed.get(topic, 0) + 1
        return set(outcomes), missed

    @staticmethod
    def select_questions(topics, attempted, count, level="mixed"):
        pools = {}
        for topic in topics:
            groups = []
            for first in range(0, TOPIC_BY_ID[topic]["variants"], VARIANTS_PER_FAMILY):
                if level != "mixed" and difficulty(topic, first) != level:
                    continue
                values = list(range(first, first + VARIANTS_PER_FAMILY))
                random.shuffle(values)
                values.sort(key=lambda variant: (topic, variant) not in attempted)
                groups.append(values)
            random.shuffle(groups)
            pools[topic] = groups
        topics = list(topics)
        random.shuffle(topics)
        selected = []
        while len(selected) < count:
            cycle = [
                (topic, pool) for topic in topics for pool in pools[topic] if pool
            ]
            if not cycle:
                raise ApiError(400, "Недостаточно задач для выбранных настроек.")
            unseen = [(topic, pool) for topic, pool in cycle if (topic, pool[-1]) not in attempted]
            candidates = unseen or cycle
            # Take one distinct topic per turn before using another family from it.
            seen_topics = set()
            for topic, pool in candidates:
                if topic in seen_topics:
                    continue
                seen_topics.add(topic)
                selected.append([topic, pool.pop()])
                pools[topic].remove(pool)
                if pool:
                    pools[topic].append(pool)
                if len(selected) == count:
                    break
        return selected

    def progress(self):
        signature = (self.path.stat().st_mtime_ns, self.path.stat().st_size)
        with self._cache_lock:
            cached = self._progress_cache
        if cached is not None and cached[0] == signature:
            # Return a fresh JSON tree so callers cannot mutate the cache.
            report = json.loads(cached[1])
        else:
            report = None
        if report is None:
            with closing(sqlite3.connect(self.path)) as conn:
                conn.execute("BEGIN")
                history = self.load_all(conn)
                completed = {row[0] for row in conn.execute("SELECT topic_id FROM completed_lessons")}
                report = summarize(history, completed)
                with self._cache_lock:
                    if signature == (self.path.stat().st_mtime_ns, self.path.stat().st_size):
                        self._progress_cache = (signature, json.dumps(report, ensure_ascii=False))
        now = self.clock()
        for active in report.get("activeSessions", []):
            deadline = active.pop("deadline", None)
            active["remainingSeconds"] = max(0, math.ceil(deadline - now)) if deadline is not None else None
            active["expired"] = deadline is not None and now >= deadline
        report["active"] = next(iter(report.get("activeSessions", [])), None)
        return report

    def access(self, session_id, action=None, payload=None):
        with self.transaction(write=action is not None) as conn:
            row = conn.execute("SELECT body FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise ApiError(404, "Тренировка не найдена.")
            session = json.loads(row[0])
            now = self.clock()
            # Reads, including HEAD, never expire or save the session.
            current_request = action == "finish" or (
                payload is not None and type(payload.get("index")) is int
                and payload["index"] == session["index"]
            )
            changed = self.expire(session, now) if action and current_request else False
            if action and not session["finishedAt"]:
                if action == "finish":
                    self.finish(session, now, early=True)
                    changed = True
                else:
                    index = payload.get("index")
                    if type(index) is not int:
                        raise ApiError(400, "Не указан номер задачи.")
                    if session["index"] == index and action != "expire":
                        self.apply(session, action, payload, now)
                        changed = True
            if changed:
                self.save(conn, session)
            return self.state(session, now)

    def expire(self, session, now):
        if session["deadline"] is None or now < session["deadline"]:
            return False
        self.record(session, None, False, session["deadline"], timed_out=True)
        session["lastNotice"] = f"Время на задачу {session['index'] + 1} истекло. Ответ не был отправлен."
        self.advance(session, now)
        return True

    def apply(self, session, action, payload, now):
        _, question = self.get_question(session)
        index = str(session["index"])
        outcome = session["outcomes"].get(index)
        if action == "answer" and outcome is None:
            raw = payload.get("answer")
            try:
                if question.get("response"):
                    correct = grading.structured_matches(raw, question["response"], question["answer"])
                elif session["lang"] == "en" and not self.multiple_choice(session, question):
                    correct = grading.sat_matches(raw, question["answer"])
                else:
                    correct = self.matches(parse_answer(raw), question["answer"])
            except grading.AnswerError as error:
                raise ApiError(400, str(error)) from None
            self.record(session, raw, correct, now)
            if session["mode"] == "test":
                self.advance(session, now)
        elif action == "hint" and session["mode"] != "test" and outcome is None:
            session["hintCount"] = min(session["hintCount"] + 1, len(question["hints"]))
        elif action == "next" and session["mode"] != "test" and outcome is not None:
            self.advance(session, now)

    def coach_context(self, session_id, index):
        with self.transaction() as conn:
            row = conn.execute("SELECT body FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise ApiError(404, "Тренировка не найдена.")
            session = json.loads(row[0])
            if session["mode"] == "test":
                raise ApiError(403, "ИИ-наставник доступен в обучении и разборе.")
            if type(index) is not int or session["finishedAt"] or index != session["index"]:
                raise ApiError(409, "Задача уже сменилась. Открой текущую задачу.")
            topic, question = self.get_question(session)
            session["coachUsed"] = True
            self.save(conn, session)
            return {
                "topic": topic["title"],
                "problem": question["prompt"],
                "verifiedHints": question["hints"],
            }

    @staticmethod
    def matches(value, target):
        return grading.number_matches(value, target)

    @staticmethod
    def record(session, raw, correct, now, timed_out=False):
        started = session.get("questionStartedAt")
        session["outcomes"][str(session["index"])] = {
            "correct": correct,
            "submitted": raw.strip() if raw and raw.strip() else None,
            "timedOut": timed_out,
            "seconds": max(0, math.floor(now - started)) if started is not None else None,
            "recordedAt": now,
            "assistance": ("assisted" if session["hintCount"] or session.get("coachUsed")
                or session.get("priorExposure", [False] * len(session["questions"]))[session["index"]] else "independent")
                if session.get("assistanceVersion") == 1 else "unknown",
        }

    @staticmethod
    def finish(session, now, early=False):
        timed = [item["seconds"] for item in session["outcomes"].values() if item.get("seconds") is not None]
        started = session.get("questionStartedAt")
        if early and started is not None and str(session["index"]) not in session["outcomes"]:
            timed.append(max(0, math.floor(now - started)))
        session["elapsedSeconds"] = sum(timed) if timed else None
        session["finishedAt"] = timestamp()
        session["deadline"] = None

    def advance(self, session, now):
        session["index"] += 1
        session["hintCount"] = 0
        session["coachUsed"] = False
        if session["index"] == len(session["questions"]):
            self.finish(session, now)
        else:
            session["questionStartedAt"] = now
            duration = session.get("secondsPerQuestion", TEST_SECONDS if session["mode"] == "test" else None)
            session["deadline"] = now + duration if duration is not None else None

    @staticmethod
    def get_question(session, index=None):
        index = session["index"] if index is None else index
        topic_id, variant = session["questions"][index]
        question = generate(topic_id, variant, session["lang"])
        if session.get("recordedDifficulties"):
            question["difficulty"] = session["recordedDifficulties"][index]
        return TOPIC_BY_ID[topic_id], question

    @staticmethod
    def feedback(question, outcome):
        result = {
            **outcome,
            "assistance": outcome.get("assistance", "unknown"),
            "answer": str(grading.rational(question["answer"]))
                if question.get("response", {}).get("kind") == "fraction" else question["answer"],
            "solution": question["solution"],
        }
        result["diagnostic"] = explain(question, outcome)
        response = question.get("response", {})
        if response.get("kind") == "graph":
            result["answerDisplay"] = graph_description(question["answer"], response)
            result["submittedDisplay"] = graph_description(outcome.get("submitted"), response)
        if response.get("kind") == "data_plot":
            from .data_plots import describe
            result["answerDisplay"] = describe(question["answer"], response)
            result["submittedDisplay"] = describe(outcome["submitted"], response) if outcome.get("submitted") else "—"
        return result

    @staticmethod
    def options(topic_id, variant, target):
        return grading.options(topic_id, variant, target, TOPIC_BY_ID[topic_id].get("answerRange"))

    @staticmethod
    def multiple_choice(session, question):
        return session["index"] % 2 == 0 or not grading.sat_input_available(question["answer"])

    def state(self, session, now):
        finished = session["finishedAt"] is not None
        outcomes = session["outcomes"]
        total = len(session["questions"])
        result = {
            "id": session["id"],
            "mode": session["mode"],
            "lang": session["lang"],
            "difficulty": session.get("difficulty", "mixed"),
            "secondsPerQuestion": session.get("secondsPerQuestion", TEST_SECONDS if session["mode"] == "test" else None),
            "elapsedSeconds": session.get("elapsedSeconds"),
            "index": session["index"],
            "total": total,
            "finished": finished,
            "question": None,
            "remainingSeconds": None,
            "expired": False,
            "lastNotice": session.get("lastNotice"),
            "hints": [],
            "feedback": None,
            "results": [],
            "correct": sum(item["correct"] for item in outcomes.values()),
            "answered": len(outcomes),
        }
        if finished:
            topic_errors = {}
            for index in range(total):
                topic, question = self.get_question(session, index)
                variant = session["questions"][index][1]
                if str(index) in outcomes and not outcomes[str(index)]["correct"]:
                    topic_errors[topic["id"]] = topic_errors.get(topic["id"], 0) + 1
                result["results"].append(
                    {
                        "id": f"{topic['id']}:{variant}",
                        "seed": variant,
                        "topic": topic["id"],
                        "title": topic["title"],
                        "prompt": question["prompt"],
                        "difficulty": question["difficulty"],
                        **self.feedback(
                            question,
                            outcomes.get(
                                str(index),
                                {"correct": False, "submitted": None, "timedOut": False},
                            ),
                        ),
                        "unanswered": str(index) not in outcomes,
                    }
                )
            result["topicErrors"] = topic_errors
            return result
        topic, question = self.get_question(session)
        variant = session["questions"][session["index"]][1]
        public_question = {
            "id": f"{topic['id']}:{variant}",
            "seed": variant,
            "topic": topic["id"],
            "title": topic["title"],
            "prompt": question["prompt"],
            "difficulty": question["difficulty"],
            "hintTotal": len(question["hints"]),
        }
        if question.get("response"):
            public_question["response"] = question["response"]
        if session["lang"] == "en" and not question.get("response") and self.multiple_choice(session, question):
            public_question["options"] = self.options(topic["id"], variant, question["answer"])
        if session["mode"] == "test" and session["deadline"] is not None:
            result["remainingSeconds"] = max(0, math.ceil(session["deadline"] - now))
            result["expired"] = now >= session["deadline"]
        if session["mode"] != "test":
            if question.get("graph"):
                public_question["graph"] = question["graph"]
            result["hints"] = question["hints"][: session["hintCount"]]
            outcome = outcomes.get(str(session["index"]))
            if outcome is not None:
                result["feedback"] = self.feedback(question, outcome)
        result["question"] = public_question
        return result
