"""
LLM factory — provider-agnostic, matching the embeddings.py pattern.

Switch providers with LLM_PROVIDER env var:
    LLM_PROVIDER=gemini      -> Gemini (needs GOOGLE_API_KEY) -- has a genuine
                                free tier, no card required; recommended if
                                you don't already have Anthropic/OpenAI billing
                                set up. Use gemini-2.5-flash (fast, free-tier
                                friendly, plenty capable for this project).
    LLM_PROVIDER=anthropic   -> Claude (needs ANTHROPIC_API_KEY, no free tier)
    LLM_PROVIDER=openai      -> GPT     (needs OPENAI_API_KEY, limited/no free tier)

No key is bundled — the app reads it from the environment / .env file. See
.env.example and README.md for setup.
"""
import os


def get_llm(temperature: float = 0.2):
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey, add it to your .env file "
                "as GOOGLE_API_KEY=..., or switch LLM_PROVIDER to anthropic/openai "
                "with the matching key instead. See README.md."
            )
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file, or set "
                "LLM_PROVIDER=gemini (free) or openai instead. See README.md."
            )
        return ChatAnthropic(model=model, temperature=temperature)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file, or set "
                "LLM_PROVIDER=gemini (free) or anthropic instead. See README.md."
            )
        return ChatOpenAI(model=model, temperature=temperature)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
