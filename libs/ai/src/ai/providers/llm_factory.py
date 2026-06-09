"""LLM provider factory — returns a LangChain BaseChatModel for the requested provider.

Provider-Specific Compatibility:
- `reasoning` kwarg (passed as `think` parameter) is handled differently per provider:
  * ChatOllama: accepts `reasoning=bool | None` (provider-specific feature)
  * ChatOpenRouter: accepts `reasoning=dict | None` with {"effort": "light|medium|hard"} levels
  * ChatOpenAI, ChatMistralAI: don't support reasoning parameter
- Version pinning (==X.Y.*) ensures consistent behavior across environments.
- Tests validate each provider can be instantiated without errors.

See: pyproject.toml for strict version constraints.
"""

from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

try:
    from langchain_ollama import ChatOllama as _ChatOllama
except ImportError:
    _ChatOllama = None  # type: ignore[assignment,misc]

try:
    from langchain_mistralai import ChatMistralAI as _ChatMistralAI
except ImportError:
    _ChatMistralAI = None  # type: ignore[assignment,misc]

try:
    from langchain_openrouter import ChatOpenRouter as _ChatOpenRouter
except ImportError:
    _ChatOpenRouter = None  # type: ignore[assignment,misc]

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
    api_key: str = "",
    base_url: str | None = None,
    temperature: float = 0,
    think: bool = False,
) -> BaseChatModel:
    """Return a LangChain chat model for the given provider.

    All configuration must be passed explicitly — no env var lookups.

    Args:
        provider: LLM provider name: "openai", "ollama", "mistral", or "openrouter".
        model: Model name. Defaults to the provider default if not provided.
        api_key: API key for the provider (openai, mistral, openrouter). Defaults to empty string.
        base_url: Custom base URL (openai-compatible endpoint or ollama host).
        temperature: Sampling temperature (default 0 for deterministic outputs).
        think: Provider-specific reasoning toggle:
            - ollama: enables/disables reasoning (bool → LLM decision)
            - openrouter: controls reasoning effort (False="none", True="high")
            - openai, mistral: parameter ignored (not supported by these providers)

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not supported.
        ImportError: If the required provider package is not installed.

    Note:
        Provider SDK version changes may affect parameter handling. Strict version
        pinning (==X.Y.*) ensures consistent behavior. If parameter compatibility
        issues arise, update version constraints and run provider smoke tests.
    """
    resolved_model: str = model or _DEFAULT_MODELS.get(provider, "")

    if provider == "openai":
        openai_model_kwargs: dict[str, Any] = {}
        if not think:
            openai_model_kwargs["stream_options"] = {"include_usage": False}
        return ChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            api_key=SecretStr(api_key) if api_key else None,
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
            api_key=SecretStr(api_key) if api_key else None,
        )

    if provider == "openrouter":
        if _ChatOpenRouter is None:
            raise ImportError(
                "langchain-openrouter is not installed. Run: pip install 'ai[openrouter]'"
            )
        return _ChatOpenRouter(
            model=resolved_model,
            temperature=temperature,
            api_key=SecretStr(api_key) if api_key else None,
            reasoning=None if think else {"effort": "none"},
        )
