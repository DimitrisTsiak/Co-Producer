import pretty_midi
from langchain_core.tools import tool
import pretty_midi
from pathlib import Path
from pydantic import BaseModel, Field
import uuid


class Note(BaseModel):
    # pitch: int = Field(
    #     ge=0,
    #     le=127,
    #     description="MIDI pitch number. C4 is 60."
    # )
    pitch: str = Field(
    description="Musical pitch name, e.g. C4, D#4, Bb3."
    )

    # start: float = Field(
    #     ge=0,
    #     description="Start time of the note in seconds."
    # )

    # duration: float = Field(
    #     gt=0,
    #     description="Duration of the note in seconds."
    # )

    start: float = Field( 
        ge=0, 
        description="Start position in beats." 
        ) 
    
    duration: float = Field( 
        gt=0, 
        description="Duration in beats." 
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

    time_signature: str = Field( 
        default="4/4", 
        description="Time signature, e.g. 4/4." 
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



def pitch_to_midi(pitch: str) -> int: 
    "C4->60"
    return pretty_midi.note_name_to_number(pitch)

def beats_to_seconds(beats: float, tempo: float) -> float: 
    seconds_per_beat = 60.0 / tempo 
    return beats * seconds_per_beat


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
        pitch = pretty_midi.note_name_to_number(note_data.pitch)

        start = beats_to_seconds( 
            note_data.start, 
            request.tempo 
            ) 
        duration = beats_to_seconds( 
            note_data.duration, 
            request.tempo 
            )

        note = pretty_midi.Note( 
            velocity=note_data.velocity, 
            pitch=pitch, 
            start=start, 
            end=start + duration )

        instrument.notes.append(note)

    midi.instruments.append(instrument)

    target_file = Path(request.output_path)
    unique_filename = f"{uuid.uuid4().hex[:6]}_{target_file.name}"
    path = target_file.parent / unique_filename

    midi.write(str(path))


    return str(path)

