"""
Chat service for plant diagnosis Q&A.

Uses OpenAI-compat /v1/chat/completions with streaming.
Supports image messages — user can send follow-up photos mid-chat.
Qwen3.5 <think>...</think> blocks are routed as separate 'r' frames
so Flutter can show them in a collapsible reasoning accordion.

Frame format:
  {"t": "r", "c": "..."}   reasoning delta
  {"t": "m", "c": "..."}   message delta
  {"t": "done"}             stream complete
  {"t": "error", "c": "..."} error
"""

import json
from typing import AsyncIterator, List

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionUserMessageParam
from typing import Optional

from app.core.config import settings
from app.models.chat_schemas import ChatMessage
from app.models.schemas import PlantAnalysisResult


def _build_system_prompt(analysis: Optional[PlantAnalysisResult], language: str) -> str:
    lang_instruction = (
        "Respond in Arabic. Use clear, accessible agricultural Arabic."
        if language == "ar"
        else "Respond in English."
    )

    # ── Free-chat mode (no scan context) ────────────────────────────────────
    if analysis is None:
        return f"""You are AgriVision, an expert plant pathologist and agricultural AI assistant.
You help farmers and gardeners with plant health questions, disease identification,
pest control, soil health, and general plant care advice.

The user has not provided a specific plant scan for this conversation.
Answer their questions based on your agricultural expertise.
If they describe symptoms, ask clarifying questions to narrow down the diagnosis.
If they send images, analyse them carefully.
Be helpful, accurate, and practical. Give specific actionable advice.
{lang_instruction}
Keep responses concise and conversational."""

    # ── Scan-context mode (linked to a specific diagnosis) ───────────────────
    severity = analysis.severity
    diagnosis = analysis.diagnosis

    return f"""You are AgriVision, an expert plant pathologist AI assistant.
You have already analysed a plant image. Here are your findings:

DIAGNOSIS: {diagnosis.name}
{'SCIENTIFIC NAME: ' + diagnosis.scientific_name if diagnosis.scientific_name else ''}
CONFIDENCE: {diagnosis.confidence * 100:.1f}%
DESCRIPTION: {diagnosis.description}

SEVERITY LEVEL: {severity.level} ({severity.score}/100)
VISUAL INDICATORS: {', '.join(severity.visual_indicators) if severity.visual_indicators else 'None noted'}

RECOMMENDATION: {analysis.recommendation}

The user may send follow-up images during the conversation for additional context.
Analyse any new images in the context of the original diagnosis above.
Be helpful, accurate, and practical. Give specific actionable advice.
{lang_instruction}
Do NOT repeat the full diagnosis summary on every message.
Keep responses concise and conversational."""


class _StreamRouter:
    """
    Routes <think>...</think> content as 'r' frames, everything else as 'm'.

    Per observed behaviour, <think> and </think> arrive as complete single
    tokens — no partial tag splits. We do a simple buffer-append approach:
    accumulate until we can rule out or confirm a tag, then flush.

    The only edge case we guard is a partial tag at the very end of a token
    (e.g. token ends with '<thi') — we hold it in the buffer until the next
    token resolves it.
    """

    _OPEN  = "<think>"
    _CLOSE = "</think>"

    # def __init__(self) -> None:
    #     self._in_think = False
    #     self._buf = ""
    def __init__(self) -> None:
        self._think_depth = 0
        self._buf = ""

    @property
    def _in_think(self) -> bool:
        return self._think_depth > 0



    def feed(self, token: str) -> list[tuple[str, str]]:
        """
        Process a token. Returns list of (type, text) pairs.
        type is 'r' for reasoning, 'm' for message.
        """
        results: list[tuple[str, str]] = []
        self._buf += token

        while self._buf:
            target = self._CLOSE if self._in_think else self._OPEN

            idx = self._buf.find(target)
            if idx == -1:
                # Tag not found. Check if the buffer *ends with* a partial tag
                # prefix — if so, hold those trailing chars in case the next
                # token completes the tag.
                partial = self._partial_tag_suffix(self._buf, target)
                safe = self._buf[: len(self._buf) - partial]
                if safe:
                    results.append(("r" if self._in_think else "m", safe))
                self._buf = self._buf[len(self._buf) - partial :]
                break
            if not self._in_think:          # was outside think
                self._think_depth += 1 
            else:
                # Emit everything before the tag
                before = self._buf[:idx]
                if before:
                    results.append(("r" if self._in_think else "m", before))
                # Toggle state, advance buffer past the tag
                self._think_depth = max(0, self._think_depth - 1)
                self._buf = self._buf[idx + len(target):]

        return results

    def flush(self) -> tuple[str, str] | None:
        if self._buf:
            out = self._buf
            self._buf = ""
            # If think was never closed, still route correctly but mark it
            return ("r" if self._in_think else "m", out)
        return None

    # Add a helper the caller can check after flush:
    @property
    def was_think_unclosed(self) -> bool:
        return self._think_depth > 0

    @staticmethod
    def _partial_tag_suffix(text: str, tag: str) -> int:
        """
        Returns the length of the longest suffix of `text` that is a
        prefix of `tag`. Used to hold back chars that might be the start
        of a tag arriving across token boundaries.
        """
        for length in range(min(len(tag) - 1, len(text)), 0, -1):
            if text.endswith(tag[:length]):
                return length
        return 0


def _build_openai_messages(
    system_prompt: str,
    messages: List[ChatMessage],
) -> list[ChatCompletionMessageParam]:
    result: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt}
    ]

    # Find the index of the last message that has an image
    last_image_idx = max(
        (i for i, m in enumerate(messages) if m.role == "user" and m.image_b64),
        default=None,
    )

    for i, msg in enumerate(messages):
        if msg.role == "user" and msg.image_b64:
            mime = msg.image_mime or "image/jpeg"
            if i == last_image_idx:
                # Keep full image only for the most recent one
                result.append({
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{msg.image_b64}"}},
                        {"type": "text", "text": msg.content or "Analyse this image."},
                    ],
                })
            else:
                # Older image turns: drop the image, keep the text
                result.append(
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=f"[image] {msg.content or ''}".strip(),
                    )
                )
        else:
            if msg.role == "user":
                result.append(ChatCompletionUserMessageParam(role="user", content=msg.content))
            else:
                result.append(ChatCompletionAssistantMessageParam(role="assistant", content=msg.content))

    return result


class ChatService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=settings.LM_STUDIO_BASE_URL,
            api_key="lm-studio",
            timeout=settings.LOCAL_AI_TIMEOUT,
        )
        self.model = settings.LM_STUDIO_MODEL

    async def stream_response(
        self,
        analysis: Optional[PlantAnalysisResult],
        messages: List[ChatMessage],
        language: str = "en",
    ) -> AsyncIterator[str]:

        system_prompt = _build_system_prompt(analysis, language)
        openai_messages = _build_openai_messages(system_prompt, messages)

        if not any(m["role"] == "user" for m in openai_messages):
            yield _frame("error", "No user message in history.")
            return

        router = _StreamRouter()

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                stream=True,
                temperature=0.7,
                top_p=0.8,
                presence_penalty=1.5,
                max_tokens=2048,
                extra_body={"top_k": 20, "min_p": 0.0},
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                for ftype, text in router.feed(delta):
                    yield _frame(ftype, text)

            remainder = router.flush()
            if remainder:
                yield _frame(remainder[0], remainder[1])
            if router.was_think_unclosed:
                yield _frame("warn", "unclosed_think")

            yield _frame("done")

        except APITimeoutError:
            yield _frame("error", "LM Studio timed out.")
        except APIConnectionError:
            yield _frame("error", "Cannot reach LM Studio. Is it running?")
        except APIStatusError as exc:
            yield _frame("error", f"LM Studio returned HTTP {exc.status_code}")
        except Exception as exc:
            yield _frame("error", str(exc))


def _frame(type_: str, content: str = "") -> str:
    obj: dict = {"t": type_}
    if content:
        obj["c"] = content
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


chat_service = ChatService()