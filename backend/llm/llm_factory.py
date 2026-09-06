"""
produce different CHATs for different API providers. Currently only supports Google API's
"""

from langchain_google_genai import ChatGoogleGenerativeAI


def create_llm(provider:str, api_key: str, name:str = "gemini-3.1-flash-lite", temperature:float = 1.0):
    provider = provider.strip().lower()

    if provider == "google":
        try:
            return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=name,
            temperature=temperature
        )
        except Exception as e:
            print(f"There was an error when trying to connect to the API: {e}")
            return e