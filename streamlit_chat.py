import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from backend.llm.llm_factory import create_llm
from backend.agent.music_agent import MusicAgent
from backend.memory.short_term_memory import ShortMemory
from backend.tools.midi_tools import create_midi
from backend.agent.prompts import SYSTEM_PROMPT

load_dotenv()


def initialize_agent():

    api_key = os.getenv("GOOGLE_GEMINI_KEY")

    model = create_llm(
        provider="google",
        api_key=api_key,
        name="gemini-3.5-flash-lite"
    )

    memory = ShortMemory(
        system_prompt=SYSTEM_PROMPT
    )

    return MusicAgent(
        model=model,
        memory=memory,
        tools=[create_midi]
    )


# -------------------------
# Page configuration
# -------------------------

st.set_page_config(
    page_title="Music Midi Agent",
    page_icon="🎵",
    layout="centered"
)


# -------------------------
# Initialize agent
# -------------------------

if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []


# -------------------------
# UI
# -------------------------

st.title("🎵 Music Generation Agent")

st.caption(
    "Describe a melody or ask the agent to modify your existing composition."
)


# Display conversation history
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -------------------------
# Chat input
# -------------------------

user_input = st.chat_input(
    "Describe the music you want..."
)


if user_input:

    # Display user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)


    # Run agent
    with st.chat_message("assistant"):

        with st.spinner("Composing..."):

            response = st.session_state.agent.invoke(
                user_input
            )

        st.markdown(response)

        output_dir = Path("midi_outputs")

        # Download midi
        midi_files = list(output_dir.glob("*.mid"))

        if midi_files:
            latest_midi = max(
                midi_files,
                key=lambda p: p.stat().st_mtime
            )

            with open(latest_midi, "rb") as f:
                st.download_button(
                    label="🎹 Download MIDI",
                    data=f,
                    file_name=latest_midi.name,
                    mime="audio/midi"
                )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })


