import pretty_midi
from langchain_core.tools import tool
import pretty_midi
from pathlib import Path


@tool
def create_midi(
    notes: list[dict],
    output_path: str = "output.mid",
    tempo: float = 120.0
) -> str:
    """
    Create a MIDI file from musical notes.

    notes must contain pitch, start, duration and optionally velocity.
    pitch is a MIDI note number from 0 to 127.
    start and duration are measured in seconds.
    """
    # Check if the directory specified by the user exists
    # I could add safeguards here
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)

    instrument = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program(
            "Acoustic Grand Piano"
        )
    )

    for n in notes:
        note = pretty_midi.Note(
            velocity=n.get("velocity", 100),
            pitch=n["pitch"],
            start=n["start"],
            end=n["start"] + n["duration"]
        )

        instrument.notes.append(note)

    midi.instruments.append(instrument)
    midi.write(output_path)

    return f"MIDI file created successfully: {output_path}"