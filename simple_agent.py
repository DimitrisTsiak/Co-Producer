import os
from dotenv import load_dotenv
from backend.llm.llm_factory import create_llm





if __name__ == "__main__":
    load_dotenv()
    GOOGLE_API_KEY = os.getenv('GOOGLE_GEMINI_KEY')


    model = create_llm(provider='google',
                       api_key=GOOGLE_API_KEY,
                       name='gemini-3.7-flash')

    response = model.invoke("Why do parrots talk?")
    print(response)
