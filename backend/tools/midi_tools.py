"""MIDI generation tools and Pydantic schemas for the MusicAgent."""

from pathlib import Path
import uuid
from langchain_core.tools import tool
import pretty_midi
from pydantic import BaseModel, Field


class Note(BaseModel):
    """Represents a single musical note in beat-based timing."""

    pitch: str = Field(
        description="Musical pitch name, e.g. C4, D#4, Bb3."
    )
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
        description="MIDI velocity (1-127)."
    )


BASE_DIR = Path("midi_outputs").resolve()


class MIDIRequest(BaseModel):
    """Input schema for creating a MIDI file."""

    notes: list[Note] = Field(
        min_length=1,
        description="List of notes that make up the composition."
    )
    output_path: str = Field(
        default="midi_outputs/output.mid",
        description="Path where the MIDI file should be saved (must be inside midi_outputs/)."
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


def pitch_to_midi(pitch: str | int) -> int:
    """Convert a musical pitch name (e.g. 'C4') or MIDI number to a MIDI integer (0-127)."""
    if isinstance(pitch, int) or (isinstance(pitch, str) and pitch.strip().isdigit()):
        midi_num = int(pitch)
        if not 0 <= midi_num <= 127:
            raise ValueError(f"MIDI pitch number must be between 0 and 127, got {midi_num}.")
        return midi_num
    return pretty_midi.note_name_to_number(pitch.strip())


def beats_to_seconds(beats: float, tempo: float) -> float:
    """Convert beats to seconds for a given tempo in BPM."""
    if tempo <= 0:
        raise ValueError("Tempo must be greater than 0.")
    seconds_per_beat = 60.0 / tempo
    return beats * seconds_per_beat


@tool
def create_midi(request: MIDIRequest) -> str:
    """
    Create a MIDI file from a musical specification.

    Use this tool whenever the user asks to create or modify
    a MIDI file.
    """
    base_dir = BASE_DIR.resolve()
    target_file = Path(request.output_path).resolve()

    if not target_file.is_relative_to(base_dir) or target_file == base_dir:
        raise ValueError("Output path is outside the permitted directory.")

    target_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    midi = pretty_midi.PrettyMIDI(
        initial_tempo=request.tempo
    )

    if request.time_signature:
        try:
            num_str, den_str = request.time_signature.strip().split("/")
            midi.time_signature_changes.append(
                pretty_midi.TimeSignature(int(num_str), int(den_str), 0.0)
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid time_signature '{request.time_signature}'. Expected format like '4/4'.") from exc

    instrument = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program(
            "Acoustic Grand Piano"
        )
    )

    for note_data in request.notes:
        pitch = pitch_to_midi(note_data.pitch)

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
            end=start + duration
        )

        instrument.notes.append(note)

    midi.instruments.append(instrument)

    unique_filename = f"{uuid.uuid4().hex[:6]}_{target_file.name}"
    path = target_file.parent / unique_filename

    midi.write(str(path))

    return str(path)

