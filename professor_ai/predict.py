"""질문 모드: Claude API로 교수님의 예상 답장을 만든다. 아무것도 저장하지 않는다."""

from __future__ import annotations

import os

from . import store
from .prompt import build_system, build_user

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"


class PredictError(RuntimeError):
    pass


def load_context() -> tuple[str, dict]:
    students = store.list_students()
    if not students:
        raise PredictError("학습된 대화가 없습니다. 먼저 카톡 .txt 파일로 학습시켜 주세요.")
    transcripts = {s: store.load_messages(s) for s in students}
    professor = next(
        (store.load_meta(s).get("professor_name") for s in students if store.load_meta(s).get("professor_name")),
        "",
    )
    return professor, transcripts


def predict(student: str, mode: str, text: str, *, model: str | None = None, effort: str | None = None) -> str:
    import anthropic  # 학습 모드만 쓸 때는 SDK가 없어도 되도록

    professor, transcripts = load_context()
    system = build_system(professor, transcripts)
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경 변수 사용
    try:
        response = client.beta.messages.create(
            model=model or os.environ.get("PROFESSOR_AI_MODEL", DEFAULT_MODEL),
            max_tokens=16000,
            output_config={"effort": effort or os.environ.get("PROFESSOR_AI_EFFORT", DEFAULT_EFFORT)},
            # 대화 기록(시스템 프롬프트)은 질문마다 같으므로 캐시해서 비용을 줄인다.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": build_user(student, mode, text)}],
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise PredictError("API 키가 올바르지 않습니다. ANTHROPIC_API_KEY를 확인해 주세요.") from e
    except anthropic.RateLimitError as e:
        raise PredictError("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.") from e
    except anthropic.APIConnectionError as e:
        raise PredictError("Claude API에 연결하지 못했습니다. 인터넷 연결을 확인해 주세요.") from e
    except anthropic.APIStatusError as e:
        raise PredictError(f"Claude API 오류 ({e.status_code}): {e.message}") from e

    if response.stop_reason == "refusal":
        raise PredictError("이 메시지에는 답장을 만들 수 없다고 응답했습니다. 표현을 바꿔 다시 시도해 주세요.")
    reply = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if not reply:
        raise PredictError("빈 답장이 왔습니다. 다시 시도해 주세요.")
    return reply
