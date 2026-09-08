import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import base64
import streamlit.components.v1 as components
from langchain_google_genai.chat_models import GoogleModelNotFoundError, GoogleAPIError
from backend.llm.llm_factory import create_llm
from backend.agent.music_agent import MusicAgent
from backend.memory.short_term_memory import ShortMemory
from backend.tools.midi_tools import create_midi
from backend.agent.prompts import SYSTEM_PROMPT


load_dotenv()


GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite"
]



def initialize_agent(model_name):

    api_key = os.getenv("GOOGLE_GEMINI_KEY")

    model = create_llm(
        provider="google",
        api_key=api_key,
        name=model_name
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


if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gemini-3.5-flash"


selected_model = st.sidebar.selectbox(
    "Gemini Model",
    GEMINI_MODELS,
    index=GEMINI_MODELS.index(
        st.session_state.selected_model
    )
)

if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent(selected_model)

elif selected_model != st.session_state.selected_model:
    st.session_state.selected_model = selected_model
    st.session_state.agent = initialize_agent(
        selected_model
    )

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

            try:
                response = st.session_state.agent.invoke(user_input)
                

            except GoogleModelNotFoundError:

                st.error(
                    "The selected Gemini model is not available "
                    "with your current API key.\n\n"
                    "Please select another model from the **Gemini Model** "
                    "menu in the sidebar."
                )

            except GoogleAPIError as e:

                if "503" in str(e) or "UNAVAILABLE" in str(e):

                    st.error(
                        "⚠️ The selected Gemini model is temporarily unavailable.\n\n"
                        "This usually means the model is experiencing high demand. "
                        "Please wait a moment and try again, or select another model "
                        "from the **Gemini Model** menu."
                    )

                else:

                    st.error(
                        "⚠️ Gemini encountered an API error.\n\n"
                        f"Details: {e}"
                    )

                st.stop()

                st.stop()
        response_text = response[0]["text"]
        st.markdown(response_text)

        output_dir = Path("midi_outputs")

        # Download midi
        midi_files = list(output_dir.glob("*.mid"))

        if midi_files:
            latest_midi = max(
                midi_files,
                key=lambda p: p.stat().st_mtime
            )
        with open(latest_midi, "rb") as f:

            midi_data = base64.b64encode(f.read()).decode()

        midi_src = f"data:audio/midi;base64,{midi_data}"

        html = f"""
        <script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58,npm/@magenta/music@1.23.1/es6/core.js,npm/html-midi-player@1.5.0"></script>

        <midi-player
            src="{midi_src}"
            sound-font
            visualizer="#myVisualizer">
        </midi-player>

        <midi-visualizer
            type="piano-roll"
            id="myVisualizer">
        </midi-visualizer>
        """

        components.html(
            html,
            height=400
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
            "content": response_text
        })

