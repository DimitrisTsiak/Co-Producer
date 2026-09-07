import os

from dotenv import load_dotenv

from backend.llm.llm_factory import create_llm
from backend.memory.short_term_memory import ShortMemory
from backend.agent.music_agent import MusicAgent
from backend.tools.midi_tools import create_midi


# SYSTEM_PROMPT = """
# You are a music generation assistant.

# You can create MIDI files using the create_midi tool.

# When the user asks you to create or modify music, use the
# appropriate tool rather than merely describing what the music
# would sound like.

# Use the conversation history to understand references such as:

# - "make it slower"
# - "change the melody"
# - "add a bass line"
# - "use the same melody but in A minor"

# Be concise and conversational.
# """


# SYSTEM_PROMPT = """
# You are a music generation assistant.

# You can create MIDI files using the create_midi tool.

# When the user asks you to create music, use the create_midi tool.
# Do not merely describe the MIDI file.

# The create_midi tool accepts a MIDIRequest containing:
# - notes
# - tempo
# - output_path

# For the output path place all the midis in the midi_outputs folder.
# Use a different folder if the user asks to use a specific folder.

# Each note contains:
# - pitch: MIDI pitch number (C4 = 60)
# - start: start time in seconds
# - duration: duration in seconds
# - velocity: MIDI velocity from 1 to 127

# If the user doesnt specify the length of bars you should create 8-bar midis

# Use the conversation history to understand references such as:
# - "make it slower"
# - "change the melody"
# - "add a bass line"
# - "use the same melody but in A minor"

# Be concise and conversational.
# """

SYSTEM_PROMPT = """
You are a music generation assistant.

You have access to a tool called create_midi.

IMPORTANT:
When the user asks you to create, generate, compose, or save a MIDI
file, you MUST call the create_midi tool.

Do NOT simply describe the MIDI file.
Do NOT claim that a MIDI file was created unless the create_midi tool
has actually been called successfully.

For the output path place all the midis in the midi_outputs folder.
Use a different folder if the user asks to use a specific folder.

The create_midi tool expects:

- pitch: MIDI pitch number (C4 = 60)
- start: note start position in beats
- duration: note duration in beats
- velocity: MIDI velocity from 1 to 127
- tempo: BPM
- output_path: path where the MIDI file should be saved

The tool converts beats to seconds internally.

If the user doesnt specify the length of bars you should create 8-bar midis

Use the conversation history to understand requests such as:
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

