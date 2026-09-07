import os
from dotenv import load_dotenv
from backend.llm.llm_factory import create_llm
from backend.tools.midi_tools import create_midi





if __name__ == "__main__":
    load_dotenv()
    GOOGLE_API_KEY = os.getenv('GOOGLE_GEMINI_KEY')


    model = create_llm(provider='google',
                       api_key=GOOGLE_API_KEY,
                       name='gemini-3.7-flash')


    model_with_tools = model.bind_tools([create_midi])

    response = model_with_tools.invoke(
        "Create a simple happy melody in C major."
    )

    print(response)