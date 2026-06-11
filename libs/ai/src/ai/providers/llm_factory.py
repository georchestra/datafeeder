"""LLM provider factory — returns a LangChain BaseChatModel for the requested provider."""

from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

try:
    from langchain_ollama import ChatOllama as _ChatOllama
except ImportError:
    _ChatOllama = None  # type: ignore[assignment,misc]

try:
    from langchain_mistralai import ChatMistralAI as _ChatMistralAI
except ImportError:
    _ChatMistralAI = None  # type: ignore[assignment,misc]

Provider = Literal["openai", "ollama", "mistral", "openrouter"]

_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2:1b",
    "mistral": "mistral-small-latest",
    "openrouter": "anthropic/claude-3-haiku",
}


def get_llm(
    provider: Provider,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0,
    think: bool = False,
    **kwargs: Any,
) -> BaseChatModel:
    """Return a LangChain chat model for the given provider.

    All configuration must be passed explicitly — no env var lookups.

    Args:
        provider: LLM provider name: "openai", "ollama" or "mistral".
        model: Model name. Defaults to the provider default if not provided.
        api_key: API key for the provider (openai, mistral).
        base_url: Custom base URL (openai-compatible endpoint or ollama host).
        temperature: Sampling temperature (default 0.2 for deterministic outputs).
        think: Enable/disable thinking mode (default False). Passed as model param
            for Ollama, and via model_kwargs for OpenAI-compatible endpoints.
        **kwargs: Additional provider-specific overrides.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not supported.
        ImportError: If the required provider package is not installed.
    """
    resolved_model: str = model or _DEFAULT_MODELS.get(provider, "")

    if provider == "openai":
        openai_model_kwargs: dict[str, Any] = {}
        if not think:
            openai_model_kwargs["stream_options"] = {"include_usage": False}
        return ChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            api_key=api_key,  # type: ignore[arg-type]
            base_url=base_url or None,
            model_kwargs=openai_model_kwargs,
        )

    if provider == "ollama":
        if _ChatOllama is None:
            raise ImportError("langchain-ollama is not installed. Run: pip install 'ai[ollama]'")
        return _ChatOllama(
            model=resolved_model,
            temperature=temperature,
            base_url=base_url or "http://localhost:11434",
            reasoning=think or None,
        )

    if provider == "mistral":
        if _ChatMistralAI is None:
            raise ImportError(
                "langchain-mistralai is not installed. Run: pip install 'ai[mistral]'"
            )
        return _ChatMistralAI(
            model=resolved_model,
            temperature=temperature,
            api_key=api_key,  # type: ignore[arg-type]
        )

    if provider == "openrouter":
        return ChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            api_key=api_key,  # type: ignore[arg-type]
            base_url=base_url or "https://openrouter.ai/api/v1",
            model_kwargs={},
        )

    raise ValueError(
        f"Unsupported provider '{provider}'. Available: {', '.join(_DEFAULT_MODELS.keys())}"
    )
