import os

from dotenv import load_dotenv

from backend.llm.llm_factory import create_llm
from backend.memory.short_term_memory import ShortMemory
from backend.agent.music_agent import MusicAgent
from backend.tools.midi_tools import create_midi


SYSTEM_PROMPT = """
You are a music generation assistant.

You can create MIDI files using the create_midi tool.

When the user asks you to create or modify music, use the
appropriate tool rather than merely describing what the music
would sound like.

Use the conversation history to understand references such as:

- "make it slower"
- "change the melody"
- "add a bass line"
- "use the same melody but in A minor"

Be concise and conversational.
"""


def main():

    load_dotenv()

    model = create_llm(
        provider="google",
        api_key=os.getenv("GOOGLE_GEMINI_KEY"),
        name="gemini-3.5-flash-lite"
    )

    memory = ShortMemory(
        system_prompt=SYSTEM_PROMPT
    )

    agent = MusicAgent(
        model=model,
        memory=memory,
        tools=[create_midi]
    )

    print("Music Agent")
    print("Type 'exit' or 'quit' to stop.")
    print("Type 'clear' to clear the conversation.")
    print("-" * 50)

    while True:

        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            break

        if user_input.lower() == "clear":
            agent.clear_memory()
            print("Memory cleared.")
            continue

        try:
            response = agent.invoke(user_input)
            print(f"\nAgent: {response}")

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()

