"""Optional model adapter interface. Default OFF. Never called in tests or by default.

No provider is connected in this repository: ``ExternalLLMAdapter`` is a labelled placeholder that
raises until an operator supplies an implementation and enables SS_LLM_ENABLED. Any model output is
shown to users labelled as model-assisted and can only ADD reasons; it can never lower a warning.
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class LLMResult(TypedDict):
    reasons: list[str]
    model: str


class LLMNotConfigured(RuntimeError):
    pass


class LLMAdapter(Protocol):
    name: str

    def analyse(self, text: str) -> LLMResult | None: ...


class NullLLMAdapter:
    name = "none"

    def analyse(self, text: str) -> LLMResult | None:
        return None


class ExternalLLMAdapter:
    """Placeholder for a real provider. Outstanding dependency: provider choice, DPA, API key."""

    name = "external-unconfigured"

    def analyse(self, text: str) -> LLMResult | None:
        raise LLMNotConfigured("No LLM provider is configured for this deployment")
