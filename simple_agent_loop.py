import os

from dotenv import load_dotenv
from backend.llm.llm_factory import create_llm
from backend.tools.midi_tools import create_midi

def run_agent(model, user_request):

    tools = {
        "create_midi": create_midi
    }

    model = model.bind_tools(list(tools.values()))

    messages = [
        {
            "role": "system",
            "content": """
You are a music generation agent.

When the user asks you to create music, design the melody
and use the create_midi tool to generate an actual MIDI file.

Do not merely describe the MIDI.
Actually call the tool.

Use MIDI pitch numbers:
C4 = 60
D4 = 62
E4 = 64
F4 = 65
G4 = 67
A4 = 69
B4 = 71
"""
        },
        {
            "role": "user",
            "content": user_request
        }
    ]

    while True:

        response = model.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:

            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            tool = tools[tool_name]
            result = tool.invoke(tool_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })



if __name__ == "__main__":

    load_dotenv()

    GOOGLE_API_KEY = os.getenv("GOOGLE_GEMINI_KEY")

    model = create_llm(
        provider="google",
        api_key=GOOGLE_API_KEY,
        name="gemini-3.1-flash-lite"
    )

    result = run_agent(
        model,
        "Create 8-bar happy melody in D minor at 120 BPM inspired by chopin. save the midi in the output folder like that: output/output.mid"
    )

    print(result)