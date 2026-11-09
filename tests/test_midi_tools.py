"""Unit, validation, security, and smoke tests for backend.tools.midi_tools."""

from pathlib import Path
import shutil
import uuid

import pretty_midi
from pydantic import ValidationError
import pytest

from backend.tools.midi_tools import (
    BASE_DIR,
    MIDIRequest,
    Note,
    beats_to_seconds,
    create_midi,
    pitch_to_midi,
)


class TestPitchToMidi:
    """Tests for pitch_to_midi conversion."""

    @pytest.mark.parametrize(
        ("pitch", "expected"),
        [
            ("C4", 60),
            ("A4", 69),
            ("D#4", 63),
            ("Bb3", 58),
            ("C0", 12),
            ("60", 60),
            (60, 60),
        ],
    )
    def test_valid_pitches(self, pitch, expected):
        assert pitch_to_midi(pitch) == expected

    @pytest.mark.parametrize("bad_pitch", ["128", 128, -5, "H4", "invalid"])
    def test_invalid_pitches_raise(self, bad_pitch):
        with pytest.raises(Exception):
            pitch_to_midi(bad_pitch)


class TestBeatsToSeconds:
    """Tests for beats_to_seconds conversion."""

    def test_standard_conversion(self):
        assert beats_to_seconds(2.0, 120.0) == pytest.approx(1.0)
        assert beats_to_seconds(1.5, 60.0) == pytest.approx(1.5)
        assert beats_to_seconds(0.0, 90.0) == pytest.approx(0.0)

    @pytest.mark.parametrize("bad_tempo", [0.0, -60.0])
    def test_non_positive_tempo_raises(self, bad_tempo):
        with pytest.raises(ValueError, match="Tempo must be greater than 0"):
            beats_to_seconds(1.0, bad_tempo)


class TestSchemas:
    """Validation tests for Note and MIDIRequest Pydantic models."""

    def test_valid_note_defaults(self):
        note = Note(pitch="C4", start=0.0, duration=1.0)
        assert note.velocity == 100

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"pitch": "C4", "start": -0.5, "duration": 1.0},
            {"pitch": "C4", "start": 0.0, "duration": 0.0},
            {"pitch": "C4", "start": 0.0, "duration": -1.0},
            {"pitch": "C4", "start": 0.0, "duration": 1.0, "velocity": 0},
            {"pitch": "C4", "start": 0.0, "duration": 1.0, "velocity": 128},
        ],
    )
    def test_invalid_note_parameters_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            Note(**kwargs)

    def test_invalid_midi_request_rejected(self):
        with pytest.raises(ValidationError):
            MIDIRequest(notes=[])

        with pytest.raises(ValidationError):
            MIDIRequest(
                notes=[Note(pitch="C4", start=0.0, duration=1.0)],
                tempo=0,
            )


class TestCreateMidi:
    """Security and functional smoke tests for the create_midi tool."""

    @pytest.mark.parametrize(
        "unsafe_path",
        [
            "../outside.mid",
            "midi_outputs/../../outside.mid",
            "outside.mid",
            "midi_outputs",
            "/tmp/evil.mid",
        ],
    )
    def test_path_traversal_rejected(self, unsafe_path):
        payload = {
            "request": {
                "notes": [{"pitch": "C4", "start": 0.0, "duration": 1.0}],
                "output_path": unsafe_path,
            }
        }
        with pytest.raises(ValueError, match="Output path is outside the permitted directory"):
            create_midi.invoke(payload)

    def test_generates_valid_midi_file(self):
        payload = {
            "request": {
                "notes": [
                    {"pitch": "C4", "start": 0.0, "duration": 1.0, "velocity": 80},
                    {"pitch": "E4", "start": 1.0, "duration": 1.0, "velocity": 90},
                    {"pitch": "G4", "start": 2.0, "duration": 2.0, "velocity": 100},
                ],
                "tempo": 120.0,
                "time_signature": "3/4",
                "output_path": "midi_outputs/pytest_smoke.mid",
            }
        }
        created_path_str = create_midi.invoke(payload)
        created_path = Path(created_path_str).resolve()

        try:
            assert created_path.exists()
            assert created_path.is_relative_to(BASE_DIR.resolve())

            midi = pretty_midi.PrettyMIDI(str(created_path))
            assert len(midi.instruments) == 1
            notes = midi.instruments[0].notes
            assert len(notes) == 3
            assert [n.pitch for n in notes] == [60, 64, 67]
            assert [n.velocity for n in notes] == [80, 90, 100]
            assert notes[0].start == pytest.approx(0.0)
            assert notes[0].end == pytest.approx(0.5)
            assert len(midi.time_signature_changes) == 1
            assert midi.time_signature_changes[0].numerator == 3
            assert midi.time_signature_changes[0].denominator == 4
        finally:
            if created_path.exists():
                created_path.unlink()



# ---------------------------------------------------------------------------
# Additional create_midi edge cases
# ---------------------------------------------------------------------------


def _note(pitch="C4", start=0.0, duration=1.0, velocity=100):
    return {"pitch": pitch, "start": start, "duration": duration, "velocity": velocity}


def _invoke(**request):
    """Call create_midi with a request payload and return the created Path."""
    return Path(create_midi.invoke({"request": request})).resolve()


@pytest.fixture
def created_files():
    """Collects files/folders created by a test and deletes them afterwards."""
    paths: list[Path] = []
    yield paths
    for p in paths:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


class TestCreateMidiEdgeCases:
    """Edge-case behaviour of the create_midi tool."""

    def test_same_output_path_produces_unique_files(self, created_files):
        first = _invoke(notes=[_note()], output_path="midi_outputs/pytest_dup.mid")
        second = _invoke(notes=[_note()], output_path="midi_outputs/pytest_dup.mid")
        created_files.extend([first, second])

        assert first != second
        assert first.exists() and second.exists()
        assert first.name.endswith("_pytest_dup.mid")
        assert second.name.endswith("_pytest_dup.mid")

    def test_default_output_path_stays_inside_base_dir(self, created_files):
        path = _invoke(notes=[_note()])
        created_files.append(path)

        assert path.exists()
        assert path.is_relative_to(BASE_DIR.resolve())
        assert path.name.endswith("_output.mid")

    def test_nested_subfolder_is_allowed_and_created(self, created_files):
        subfolder = BASE_DIR / f"pytest_{uuid.uuid4().hex[:8]}"
        created_files.append(subfolder)
        assert not subfolder.exists()

        path = _invoke(notes=[_note()], output_path=f"midi_outputs/{subfolder.name}/song.mid")

        assert subfolder.is_dir()
        assert path.parent == subfolder.resolve()
        assert path.exists()

    @pytest.mark.parametrize("bad_signature", ["abc", "4", "4/0", "x/4"])
    def test_invalid_time_signature_raises(self, bad_signature):
        with pytest.raises(ValueError, match="Invalid time_signature"):
            _invoke(
                notes=[_note()],
                time_signature=bad_signature,
                output_path="midi_outputs/pytest_bad_ts.mid",
            )

    @pytest.mark.parametrize("tempo", [60.0, 90.0, 140.0])
    def test_tempo_is_written_to_file(self, created_files, tempo):
        path = _invoke(notes=[_note()], tempo=tempo, output_path="midi_outputs/pytest_tempo.mid")
        created_files.append(path)

        _, tempi = pretty_midi.PrettyMIDI(str(path)).get_tempo_changes()
        assert len(tempi) >= 1
        assert tempi[0] == pytest.approx(tempo, rel=1e-3)

    def test_chord_notes_with_same_start_are_all_written(self, created_files):
        chord = [_note("C4"), _note("E4"), _note("G4")]
        path = _invoke(notes=chord, output_path="midi_outputs/pytest_chord.mid")
        created_files.append(path)

        notes = pretty_midi.PrettyMIDI(str(path)).instruments[0].notes
        assert sorted(n.pitch for n in notes) == [60, 64, 67]
        assert all(n.start == pytest.approx(0.0) for n in notes)

    def test_note_timing_at_60_bpm(self, created_files):
        path = _invoke(
            notes=[_note(start=2.0, duration=1.0)],
            tempo=60.0,
            output_path="midi_outputs/pytest_timing.mid",
        )
        created_files.append(path)

        note = pretty_midi.PrettyMIDI(str(path)).instruments[0].notes[0]
        assert note.start == pytest.approx(2.0, abs=1e-3)
        assert note.end == pytest.approx(3.0, abs=1e-3)

    def test_invalid_pitch_fails_without_writing_a_file(self):
        before = set(BASE_DIR.glob("*_pytest_badpitch.mid"))

        with pytest.raises(Exception):
            _invoke(
                notes=[_note("C4"), _note("H4", start=1.0)],
                output_path="midi_outputs/pytest_badpitch.mid",
            )

        after = set(BASE_DIR.glob("*_pytest_badpitch.mid"))
        assert after == before
