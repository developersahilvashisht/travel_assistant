"""
LLM factory — provider-agnostic, matching the embeddings.py pattern.

Switch providers with LLM_PROVIDER env var:
    LLM_PROVIDER=anthropic   -> Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai      -> GPT     (needs OPENAI_API_KEY)

No key is bundled — the app reads it from the environment / .env file. See
.env.example and README.md for setup.
"""
import os


def get_llm(temperature: float = 0.2):
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file, or set "
                "LLM_PROVIDER=openai and OPENAI_API_KEY instead. See README.md."
            )
        return ChatAnthropic(model=model, temperature=temperature)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file, or set "
                "LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY instead. See README.md."
            )
        return ChatOpenAI(model=model, temperature=temperature)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
