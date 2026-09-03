"""A Strands Model that wraps a primary and a fallback provider, so a rate
limit on the primary (Groq's free tier is the common case - a shared daily
token cap) automatically fails over to the fallback instead of the whole
app going dark until someone notices and flips LLM_PROVIDER by hand.

Only triggers on ModelThrottledException - Strands' provider-agnostic
"the model service is throttling requests" signal - never on a genuine
model/programming error, which should surface normally rather than being
silently masked by a fallback call.
"""

import logging
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages, SystemContentBlock
from strands.types.exceptions import ModelThrottledException
from strands.types.tools import ToolChoice, ToolSpec

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _strip_reasoning_content(messages: Messages) -> Messages:
    """Reasoning/thinking blocks are provider-specific, and can carry a
    provider-specific signature (Anthropic's extended thinking) that no
    other provider can produce or verify - replaying a Groq/OpenAI-produced
    reasoningContent block to Anthropic crashes its formatter looking for a
    "signature" key that was never there. Conversation history built up
    against the primary provider before the fallback kicked in must have
    these stripped before being replayed to a different provider. Drops any
    message left with no content after stripping, rather than sending an
    empty content array.
    """
    cleaned: Messages = []
    for message in messages:
        content = [block for block in message.get("content", []) if "reasoningContent" not in block]
        if content:
            cleaned.append({**message, "content": content})
    return cleaned


class FallbackModel(Model):
    """Delegates every call to `primary` first; if it raises
    ModelThrottledException before yielding anything, retries the same call
    against `fallback` instead. If `primary` has already started streaming a
    response, a later throttle is NOT papered over - the two providers'
    partial outputs can't be safely spliced together, so it's raised as-is
    rather than risking a corrupted/duplicated reply.
    """

    def __init__(self, primary: Model, fallback: Model, primary_name: str = "primary", fallback_name: str = "fallback"):
        self._primary = primary
        self._fallback = fallback
        self._primary_name = primary_name
        self._fallback_name = fallback_name

    def update_config(self, **model_config: Any) -> None:
        self._primary.update_config(**model_config)
        self._fallback.update_config(**model_config)

    def get_config(self) -> Any:
        return self._primary.get_config()

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        cancel_signal: Any = None,
        **kwargs: Any,
    ):
        yielded_any = False
        try:
            async for event in self._primary.stream(
                messages,
                tool_specs,
                system_prompt,
                tool_choice=tool_choice,
                system_prompt_content=system_prompt_content,
                invocation_state=invocation_state,
                cancel_signal=cancel_signal,
                **kwargs,
            ):
                yielded_any = True
                yield event
            return
        except ModelThrottledException:
            if yielded_any:
                raise
            logger.warning(
                "%s model throttled, falling back to %s", self._primary_name, self._fallback_name
            )

        async for event in self._fallback.stream(
            _strip_reasoning_content(messages),
            tool_specs,
            system_prompt,
            tool_choice=tool_choice,
            system_prompt_content=system_prompt_content,
            invocation_state=invocation_state,
            cancel_signal=cancel_signal,
            **kwargs,
        ):
            yield event

    async def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ):
        yielded_any = False
        try:
            async for event in self._primary.structured_output(output_model, prompt, system_prompt, **kwargs):
                yielded_any = True
                yield event
            return
        except ModelThrottledException:
            if yielded_any:
                raise
            logger.warning(
                "%s model throttled, falling back to %s", self._primary_name, self._fallback_name
            )

        async for event in self._fallback.structured_output(
            output_model, _strip_reasoning_content(prompt), system_prompt, **kwargs
        ):
            yield event
