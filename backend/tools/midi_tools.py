import pretty_midi
from langchain_core.tools import tool
import pretty_midi
from pathlib import Path
from pydantic import BaseModel, Field


class Note(BaseModel):
    pitch: int = Field(
        ge=0,
        le=127,
        description="MIDI pitch number. C4 is 60."
    )

    start: float = Field(
        ge=0,
        description="Start time of the note in seconds."
    )

    duration: float = Field(
        gt=0,
        description="Duration of the note in seconds."
    )

    velocity: int = Field(
        default=100,
        ge=1,
        le=127,
        description="MIDI velocity."
    )


class MIDIRequest(BaseModel):
    notes: list[Note] = Field(
        description="List of notes that make up the melody."
    )

    output_path: str = Field(
        default="output.mid",
        description="Path where the MIDI file should be saved."
    )

    tempo: float = Field(
        default=120.0,
        gt=0,
        description="Tempo in beats per minute."
    )




# @tool
# def create_midi(
#     notes: list[dict],
#     output_path: str = "output.mid",
#     tempo: float = 120.0
# ) -> str:
#     """
#     Create a MIDI file from musical notes.

#     notes must contain pitch, start, duration and optionally velocity.
#     pitch is a MIDI note number from 0 to 127.
#     start and duration are measured in seconds.
#     """
#     # Check if the directory specified by the user exists
#     # I could add safeguards here
#     path = Path(output_path)
#     path.parent.mkdir(parents=True, exist_ok=True)

#     midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)

#     instrument = pretty_midi.Instrument(
#         program=pretty_midi.instrument_name_to_program(
#             "Acoustic Grand Piano"
#         )
#     )

#     for n in notes:
#         note = pretty_midi.Note(
#             velocity=n.get("velocity", 100),
#             pitch=n["pitch"],
#             start=n["start"],
#             end=n["start"] + n["duration"]
#         )

#         instrument.notes.append(note)

#     midi.instruments.append(instrument)
#     midi.write(output_path)

#     return f"MIDI file created successfully: {output_path}"






@tool
def create_midi(request: MIDIRequest) -> str:
    """
    Create a MIDI file from a musical specification.

    Use this tool whenever the user asks to create or modify
    a MIDI file.
    """

    path = Path(request.output_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    midi = pretty_midi.PrettyMIDI(
        initial_tempo=request.tempo
    )

    instrument = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program(
            "Acoustic Grand Piano"
        )
    )

    for note_data in request.notes:

        note = pretty_midi.Note(
            velocity=note_data.velocity,
            pitch=note_data.pitch,
            start=note_data.start,
            end=note_data.start + note_data.duration
        )

        instrument.notes.append(note)

    midi.instruments.append(instrument)

    midi.write(str(path))

    return f"MIDI file created successfully: {path}"

