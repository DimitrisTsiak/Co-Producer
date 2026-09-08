# Co-Producer

An AI-powered co-producer agent, built with Streamlit, that utilizes LLMs to generate and revise MIDI compositions.

## Features

- **MIDI Generation**: Instruct the LLM to create melodies with specific characteristics (e.g., "generate a piano MIDI inspired by Chopin" or "generate a dark piano chord progression").
- **Iterative Revision**: Ask the agent to modify a generated piece (e.g., "add a chord progression and a bassline to the melody", or "change the chord progression to sound more sad and nostalgic").
- **Musical Insights**: Leverage the LLM's inherent knowledge to analyze music and explain why certain melodies or progressions evoke specific moods.

## Installation

1. Clone the repository and navigate to the project root.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

*(Note: Ensure you have set up your `.env` file with the necessary API keys, such as `GOOGLE_GEMINI_KEY`)*

## Usage

To start the Streamlit server and interact with the agent, run:

```bash
streamlit run streamlit_chat.py
```

## Project Structure

```text
co-producer/
├── README.md
├── requirements.txt
├── .env                         # Environment variables (API keys)
├── streamlit_chat.py            # Main Streamlit chat interface
├── midi_outputs/                # Directory where generated .mid files are saved
└── backend/
    ├── agent/
    │   ├── music_agent.py       # Core MusicAgent logic
    │   └── prompts.py           # System prompts for the LLM
    ├── llm/
    │   └── llm_factory.py       # Factory to instantiate LLM models
    ├── memory/
    │   ├── base.py              # Base memory class
    │   └── short_term_memory.py # Short-term conversation memory
    └── tools/
        └── midi_tools.py        # Tools for creating/editing MIDI
```