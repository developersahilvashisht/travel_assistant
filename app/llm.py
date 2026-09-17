"""
LLM_PROVIDER=gemini-> Gemini
"""
import os


def get_llm(temperature: float = 0.2):
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError(
                "GOOGLE_API_KEY is not set."
            )
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
