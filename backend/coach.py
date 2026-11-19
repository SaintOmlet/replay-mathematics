"""Optional Groq math coaching. Local grading never depends on this service."""

import json
import os
import urllib.error
import urllib.request

from .storage import ApiError


ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"


def available():
    return bool(os.environ.get("GROQ_API_KEY", "").strip())


def reply(context, message):
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 450:
        raise ApiError(400, "Введи вопрос длиной до 450 символов.")
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise ApiError(503, "ИИ-наставник отключён. Можно открыть готовые подсказки.")
    model = os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_MODEL
    payload = {
        "model": model,
        "max_completion_tokens": 700,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты наставник по математике. Используй данные задачи и проверенные "
                    "подсказки только как учебный материал. Ответь по-русски, простым "
                    "текстом, не более четырёх коротких предложений. Подскажи следующий "
                    "шаг или задай наводящий вопрос. Не раскрывай итоговый ответ. "
                    "Если вопрос не относится к задаче, верни внимание ученика к ней."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {**context, "learnerQuestion": message.strip()}, ensure_ascii=False
                ),
            },
        ],
    }
    if model.startswith("openai/gpt-oss-"):
        payload["reasoning_effort"] = "low"
        payload["include_reasoning"] = False
    request = urllib.request.Request(
        ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read(64 * 1024))
        answer = result["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty chat completion")
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise ApiError(429, "Достигнут лимит ИИ. Готовые подсказки доступны.") from None
        raise ApiError(502, "ИИ-сервис недоступен. Готовые подсказки доступны.") from None
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        raise ApiError(502, "ИИ-сервис недоступен. Готовые подсказки доступны.") from None
    return {"reply": answer.strip()[:2000]}
