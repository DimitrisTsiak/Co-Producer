from backend.tools import midi_tools
import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import uuid
import base64
import streamlit.components.v1 as components
from langchain_core.globals import set_debug
from langchain_google_genai.chat_models import GoogleModelNotFoundError, GoogleAPIError, GoogleRateLimitError, GoogleInvalidRequestError
from backend.llm.llm_factory import create_llm
from backend.agent.music_agent import MusicAgent
from backend.memory.short_term_memory import ShortMemory
from backend.tools.midi_tools import create_midi
from backend.agent.prompts import SYSTEM_PROMPT, CHOPIN_PROMPT

set_debug(True)

load_dotenv()


GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite"
]


def render_midi(midi_path: str):
    if not midi_path or not Path(midi_path).exists():
        return
    path_obj = Path(midi_path)
    with open(path_obj, "rb") as f:
        midi_data = base64.b64encode(f.read()).decode()
    midi_src = f"data:audio/midi;base64,{midi_data}"
    

    viz_id = f"visualizer_{path_obj.stem}"
    html = f"""
    <script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58,npm/@magenta/music@1.23.1/es6/core.js,npm/html-midi-player@1.5.0"></script>
    <midi-player
        src="{midi_src}"
        sound-font
        visualizer="#{viz_id}">
    </midi-player>
    <midi-visualizer
        type="piano-roll"
        id="{viz_id}">
    </midi-visualizer>
    """
    components.html(html, height=400)
    with open(path_obj, "rb") as f:
        st.download_button(
            label="🎹 Download MIDI",
            data=f,
            file_name=path_obj.name,
            mime="audio/midi",
            key=f"dl_{path_obj.stem}"  
        )




def initialize_agent(model_name, api_key, chopin_mode: bool = False):
    system_prompt = SYSTEM_PROMPT
    if chopin_mode:
        system_prompt = f"{SYSTEM_PROMPT}\n\nCHOPIN MODE ACTIVE - ROMANTIC PIANO STYLISTIC GUIDELINES:\n\n{CHOPIN_PROMPT}"

    model = create_llm(
        provider="google",
        api_key=api_key,
        name=model_name
    )

    memory = ShortMemory(
        system_prompt=system_prompt
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


# -------------------------
# API KEY CHECK
# -------------------------

default_key = os.getenv("GOOGLE_GEMINI_KEY") or ""

st.sidebar.header("🔑 Authentication")
api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    value=default_key,
    placeholder="AIzaSy...",
    help="Get a free Gemini API key from Google AI Studio (https://aistudio.google.com/)"
)

st.sidebar.markdown(
    "[Get a Gemini API Key](https://aistudio.google.com/app/apikey)"
)

st.sidebar.markdown(
    "[Check the source code on GitHub](https://github.com/DimitrisTsiak/Co-Producer)"
)

chopin_mode = st.sidebar.toggle(
    "Chopin Mode",
    value=st.session_state.get("chopin_mode", False),
    help="When activated, adds Chopin composition guidelines to the system prompt."
)

if not api_key:
    st.info("👈 Please enter your Google Gemini API key in the sidebar to start composing!")
    st.stop()


# -------------------------
# Initialize Agent
# -------------------------
if "api_key" not in st.session_state:
    st.session_state.api_key = api_key

key_changed = api_key != st.session_state.api_key
model_changed = selected_model != st.session_state.get("selected_model")
mode_changed = chopin_mode != st.session_state.get("chopin_mode")

if "agent" not in st.session_state:
    st.session_state.selected_model = selected_model
    st.session_state.api_key = api_key
    st.session_state.chopin_mode = chopin_mode
    st.session_state.agent = initialize_agent(selected_model, api_key, chopin_mode=chopin_mode)
else:
    if key_changed or model_changed:
        st.session_state.selected_model = selected_model
        st.session_state.api_key = api_key
        new_model = create_llm(
            provider="google",
            api_key=api_key,
            name=selected_model
        )
        st.session_state.agent.set_model(new_model)

    if mode_changed:
        st.session_state.chopin_mode = chopin_mode
        system_prompt = (
            f"{SYSTEM_PROMPT}\n\nCHOPIN MODE ACTIVE - ROMANTIC PIANO STYLISTIC GUIDELINES:\n\n{CHOPIN_PROMPT}"
            if chopin_mode
            else SYSTEM_PROMPT
        )
        st.session_state.agent.set_system_prompt(system_prompt)


if "messages" not in st.session_state:
    st.session_state.messages = []


# -------------------------
# UI
# -------------------------

st.title("🎵 Music Generation Agent")

st.caption(
    "Describe a melody or ask the agent to modify your existing midi composition."
)


# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("thoughts"):
            with st.expander("Thinking Process", expanded=False):
                st.markdown(message["thoughts"])
        st.markdown(message["content"]) 
        if message.get("midi_path"):
            render_midi(message["midi_path"])

# -------------------------
# Chat input
# -------------------------

user_input = st.chat_input(
    "Describe the melody you want (e.g. a dark piano midi)..."
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

        thought_placeholder = st.empty()
        status_placeholder = st.empty()
        text_placeholder = st.empty()
        midi_placeholder = st.empty()

        thoughts_accumulated = ""
        text_accumulated = ""
        midi_path = None

        status_placeholder.info(
            "Waiting for response from the Gemini model... "
            "If this takes longer than expected, consider selecting a different model from the sidebar."
        )

        try:
            for event in st.session_state.agent.stream(user_input):
                event_type = event.get("type")

                if event_type == "thought":
                    status_placeholder.empty()
                    thoughts_accumulated += event.get("content", "")
                    with thought_placeholder.expander("Thinking Process", expanded=True):
                        st.markdown(thoughts_accumulated)

                elif event_type == "tool_start":
                    status_placeholder.info("Composing MIDI notes...")

                elif event_type == "midi_ready":
                    midi_path = event.get("midi_path")
                    status_placeholder.empty()
                    with midi_placeholder.container():
                        render_midi(midi_path)

                elif event_type == "text_delta":
                    status_placeholder.empty()
                    text_accumulated += event.get("content", "")
                    text_placeholder.markdown(text_accumulated)

                elif event_type == "done":
                    status_placeholder.empty()
                    if not text_accumulated:
                        raw_content = event.get("content", "")
                        if isinstance(raw_content, list):
                            text_accumulated = "\n".join(
                                block["text"] if isinstance(block, dict) and "text" in block else str(block)
                                for block in raw_content
                                if not isinstance(block, dict) or "text" in block
                            )
                        else:
                            text_accumulated = str(raw_content)
                        text_placeholder.markdown(text_accumulated)

                    if not midi_path and event.get("midi_path"):
                        midi_path = event.get("midi_path")
                        with midi_placeholder.container():
                            render_midi(midi_path)

        except GoogleInvalidRequestError:
            status_placeholder.empty()
            st.error("The provided API key is not valid. Please provide a valid Google API key.")
            st.stop()

        except GoogleModelNotFoundError:
            status_placeholder.empty()
            st.error(
                "The selected Gemini model is not available "
                "with your current API key.\n\n"
                "Please select another model from the **Gemini Model** "
                "menu in the sidebar."
            )
            st.stop()

        except GoogleRateLimitError:
            status_placeholder.empty()
            st.error(
                "⚠️ Gemini API rate limit reached.\n\n"
                "Please wait a moment and try again, or select another model."
            )
            st.stop()

        except GoogleAPIError as e:
            status_placeholder.empty()
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

        # Once complete, collapse the thinking box so it stays clean
        if thoughts_accumulated:
            with thought_placeholder.expander("Thinking Process", expanded=False):
                st.markdown(thoughts_accumulated)

        st.session_state.messages.append({
            "role": "assistant",
            "content": text_accumulated,
            "midi_path": midi_path,
            "thoughts": thoughts_accumulated if thoughts_accumulated else None
        })