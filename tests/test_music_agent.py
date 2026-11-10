"""Integration tests for MusicAgent ReAct loop using a scripted mock LLM."""

from types import SimpleNamespace
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
import pytest

from backend.agent.music_agent import MusicAgent
from backend.memory.short_term_memory import ShortMemory


class FakeLLM:
    """Mock LLM returning a pre-scripted sequence of responses."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(list(messages))
        if not self.responses:
            raise RuntimeError("FakeLLM received more calls than scripted responses.")
        return self.responses.pop(0)


class TestMusicAgent:
    """Tests for MusicAgent."""

    def test_direct_response_without_tool_call(self):
        fake_llm = FakeLLM([
            SimpleNamespace(content="I can help you compose music!", tool_calls=[])
        ])
        memory = ShortMemory(system_prompt="System instructions")
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[])

        result = agent.invoke("Hello")
        assert result["content"] == "I can help you compose music!"
        assert result["midi_path"] is None
        assert len(fake_llm.calls) == 1

    def test_tool_call_then_final_response(self):
        @tool
        def create_midi(melody: str) -> str:
            """Mock create_midi tool."""
            return "midi_outputs/generated.mid"

        fake_llm = FakeLLM([
            SimpleNamespace(
                content="",
                tool_calls=[{"id": "call_1", "name": "create_midi", "args": {"melody": "C4 E4 G4"}}],
            ),
            SimpleNamespace(
                content="Here is your C major chord.",
                tool_calls=[],
            ),
        ])
        memory = ShortMemory(system_prompt="System instructions")
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[create_midi])

        result = agent.invoke("Play C major")
        assert result["content"] == "Here is your C major chord."
        assert result["midi_path"] == "midi_outputs/generated.mid"
        assert len(fake_llm.calls) == 2

    def test_unknown_tool_handled_gracefully(self):
        fake_llm = FakeLLM([
            SimpleNamespace(
                content="",
                tool_calls=[{"id": "call_bad", "name": "unknown_tool", "args": {}}],
            ),
            SimpleNamespace(
                content="Tool was unavailable, but I am still here to help.",
                tool_calls=[],
            ),
        ])
        memory = ShortMemory()
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[])

        result = agent.invoke("Do something with unknown tool")
        assert result["content"] == "Tool was unavailable, but I am still here to help."
        tool_messages = [m for m in memory.get() if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "Unknown tool 'unknown_tool'" in tool_messages[0]["content"]

    def test_tool_exception_recorded_in_memory(self):
        @tool
        def failing_tool(x: int) -> str:
            """Tool that throws an exception."""
            raise ValueError("Something went wrong inside the tool.")

        fake_llm = FakeLLM([
            SimpleNamespace(
                content="",
                tool_calls=[{"id": "call_fail", "name": "failing_tool", "args": {"x": 1}}],
            ),
            SimpleNamespace(
                content="Recovered after tool error.",
                tool_calls=[],
            ),
        ])
        memory = ShortMemory()
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[failing_tool])

        result = agent.invoke("Run failing tool")
        assert result["content"] == "Recovered after tool error."
        tool_messages = [m for m in memory.get() if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "Tool execution failed: Something went wrong inside the tool." in tool_messages[0]["content"]

    def test_max_iterations_stops_infinite_loop(self):
        @tool
        def infinite_tool(val: str) -> str:
            """Tool that returns a dummy value."""
            return val

        endless_responses = [
            SimpleNamespace(
                content="",
                tool_calls=[{"id": f"call_{i}", "name": "infinite_tool", "args": {"val": "test"}}],
            )
            for i in range(10)
        ]
        fake_llm = FakeLLM(endless_responses)
        memory = ShortMemory()
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[infinite_tool], max_iterations=3)

        result = agent.invoke("Loop")
        assert "Maximum tool iteration limit reached" in result["content"]
        assert len(fake_llm.calls) == 3



# ---------------------------------------------------------------------------
# Additional agent loop scenarios
# ---------------------------------------------------------------------------


def _tool_call(call_id: str, name: str, args: dict | None = None) -> dict:
    return {"id": call_id, "name": name, "args": args or {}}


def _role(msg) -> str | None:
    """Return a normalized role for dict messages and LangChain message objects."""
    if isinstance(msg, dict):
        return msg.get("role")
    return {"ai": "assistant", "human": "user", "tool": "tool", "system": "system"}.get(
        getattr(msg, "type", None)
    )


class TestMusicAgentScenarios:
    """Additional MusicAgent behaviour, using real LangChain AIMessage objects."""

    def test_multiple_tool_calls_in_one_response(self):
        @tool
        def tool_a(x: str) -> str:
            """Tool A."""
            return f"A:{x}"

        @tool
        def tool_b(x: str) -> str:
            """Tool B."""
            return f"B:{x}"

        fake_llm = FakeLLM([
            AIMessage(content="", tool_calls=[
                _tool_call("call_a", "tool_a", {"x": "1"}),
                _tool_call("call_b", "tool_b", {"x": "2"}),
            ]),
            AIMessage(content="Both done."),
        ])
        memory = ShortMemory()
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[tool_a, tool_b])

        result = agent.invoke("Run both")

        assert result["content"] == "Both done."
        tool_messages = [m for m in memory.get() if _role(m) == "tool"]
        assert [(m["tool_call_id"], m["content"]) for m in tool_messages] == [
            ("call_a", "A:1"),
            ("call_b", "B:2"),
        ]

    def test_failed_create_midi_leaves_midi_path_none(self):
        @tool
        def create_midi(melody: str) -> str:
            """Mock create_midi that always fails."""
            raise ValueError("Output path is outside the permitted directory.")

        fake_llm = FakeLLM([
            AIMessage(content="", tool_calls=[_tool_call("c1", "create_midi", {"melody": "x"})]),
            AIMessage(content="Sorry, I could not save that file."),
        ])
        agent = MusicAgent(model=fake_llm, memory=ShortMemory(), tools=[create_midi])

        result = agent.invoke("Save outside")

        assert result["midi_path"] is None
        assert result["content"] == "Sorry, I could not save that file."

    def test_latest_successful_midi_path_is_returned(self):
        outputs = iter(["midi_outputs/first.mid", "midi_outputs/second.mid"])

        @tool
        def create_midi(melody: str) -> str:
            """Mock create_midi returning a new path each call."""
            return next(outputs)

        fake_llm = FakeLLM([
            AIMessage(content="", tool_calls=[_tool_call("c1", "create_midi", {"melody": "v1"})]),
            AIMessage(content="", tool_calls=[_tool_call("c2", "create_midi", {"melody": "v2"})]),
            AIMessage(content="Here is the improved version."),
        ])
        agent = MusicAgent(model=fake_llm, memory=ShortMemory(), tools=[create_midi])

        result = agent.invoke("Make it, then improve it")

        assert result["midi_path"] == "midi_outputs/second.mid"

    def test_memory_message_order_for_tool_turn(self):
        @tool
        def create_midi(melody: str) -> str:
            """Mock create_midi."""
            return "midi_outputs/song.mid"

        fake_llm = FakeLLM([
            AIMessage(content="", tool_calls=[_tool_call("c1", "create_midi", {"melody": "x"})]),
            AIMessage(content="Done."),
        ])
        memory = ShortMemory(system_prompt="SYS")
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[create_midi])

        agent.invoke("Compose")

        assert [_role(m) for m in memory.get()] == [
            "system", "user", "assistant", "tool", "assistant",
        ]

    def test_memory_carries_across_turns(self):
        fake_llm = FakeLLM([
            AIMessage(content="Here is a dark melody."),
            AIMessage(content="Slowed it down."),
        ])
        agent = MusicAgent(model=fake_llm, memory=ShortMemory(system_prompt="SYS"), tools=[])

        agent.invoke("Write a dark melody")
        agent.invoke("Make it slower")

        second_call_messages = fake_llm.calls[1]
        contents = [m["content"] if isinstance(m, dict) else m.content for m in second_call_messages]
        assert contents == [
            "SYS",
            "Write a dark melody",
            "Here is a dark melody.",
            "Make it slower",
        ]

    def test_tools_are_bound_to_model(self):
        @tool
        def create_midi(melody: str) -> str:
            """Mock create_midi."""
            return "x.mid"

        fake_llm = FakeLLM([])
        agent = MusicAgent(model=fake_llm, memory=ShortMemory(), tools=[create_midi])

        assert fake_llm.bound_tools == [create_midi]
        assert agent.tools == {"create_midi": create_midi}

    def test_clear_memory_resets_history(self):
        fake_llm = FakeLLM([AIMessage(content="Hi!")])
        memory = ShortMemory(system_prompt="SYS")
        agent = MusicAgent(model=fake_llm, memory=memory, tools=[])

        agent.invoke("Hello")
        assert len(memory.get()) == 3

        agent.clear_memory()
        assert memory.get() == [{"role": "system", "content": "SYS"}]

    def test_real_aimessage_list_content_is_passed_through(self):
        # Gemini can return content as a list of blocks; the agent passes it through
        # unchanged and the UI is responsible for extracting the text.
        blocks = [{"type": "text", "text": "Here is your melody."}]
        fake_llm = FakeLLM([AIMessage(content=blocks)])
        agent = MusicAgent(model=fake_llm, memory=ShortMemory(), tools=[])

        result = agent.invoke("Compose")

        assert result["content"] == blocks
        assert result["midi_path"] is None


class TestMusicAgentStreaming:
    """Tests for real-time thought and text streaming in MusicAgent."""

    def test_stream_yields_thoughts_tool_and_done(self):
        from langchain_core.messages import AIMessageChunk

        class StreamingFakeLLM:
            def __init__(self, streams: list):
                self.streams = list(streams)

            def bind_tools(self, tools):
                return self

            def stream(self, messages):
                if not self.streams:
                    raise RuntimeError("No more streams configured")
                return iter(self.streams.pop(0))

        chunks_turn_1 = [
            AIMessageChunk(content=[{"type": "thinking", "thinking": "Planning a melody in D minor..."}]),
            AIMessageChunk(content="", tool_call_chunks=[{
                "name": "create_midi",
                "args": '{"output_path": "midi_outputs/stream_test.mid"}',
                "id": "c_stream_1",
                "index": 0,
            }]),
        ]
        chunks_turn_2 = [
            AIMessageChunk(content="Here is "),
            AIMessageChunk(content="your piece in D minor."),
        ]

        @tool
        def create_midi(output_path: str = "midi_outputs/stream_test.mid") -> str:
            """Mock create_midi tool."""
            return output_path

        model = StreamingFakeLLM([chunks_turn_1, chunks_turn_2])
        agent = MusicAgent(model=model, memory=ShortMemory(), tools=[create_midi])

        events = list(agent.stream("Play D minor"))
        event_types = [e["type"] for e in events]

        assert "thought" in event_types
        assert "tool_start" in event_types
        assert "midi_ready" in event_types
        assert "text_delta" in event_types
        assert "done" in event_types

        thought_events = [e for e in events if e["type"] == "thought"]
        assert thought_events[0]["content"] == "Planning a melody in D minor..."

        midi_events = [e for e in events if e["type"] == "midi_ready"]
        assert midi_events[0]["midi_path"] == "midi_outputs/stream_test.mid"

        text_deltas = [e["content"] for e in events if e["type"] == "text_delta"]
        assert "".join(text_deltas) == "Here is your piece in D minor."
