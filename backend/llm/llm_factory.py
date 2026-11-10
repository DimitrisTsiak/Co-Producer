"""
produce different CHATs for different API providers. Currently only supports Google API's
"""

from langchain_google_genai import ChatGoogleGenerativeAI


def create_llm(
    provider: str,
    api_key: str,
    name: str = "gemini-3.1-flash-lite",
    temperature: float = 1.0,
    include_thoughts: bool = True
) -> ChatGoogleGenerativeAI:
    provider = provider.strip().lower()

    if provider == "google":
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=name,
            temperature=temperature,
            include_thoughts=include_thoughts
        )

    raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers: 'google'.")