"""Unit tests for ShortMemory storage, clear, and sliding window behavior."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.memory.short_term_memory import ShortMemory


class TestShortMemory:
    """Tests for ShortMemory."""

    def test_initialization_with_system_prompt(self):
        mem = ShortMemory(system_prompt="You are a musical AI.")
        messages = mem.get()
        assert len(messages) == 1
        assert messages[0] == {"role": "system", "content": "You are a musical AI."}

    def test_initialization_without_system_prompt(self):
        mem = ShortMemory()
        assert mem.get() == []

    def test_add_messages_in_order(self):
        mem = ShortMemory()
        mem.add({"role": "user", "content": "Hello"})
        mem.add({"role": "assistant", "content": "Hi there!"})
        messages = mem.get()
        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi there!"

    def test_clear_preserves_system_prompt(self):
        mem = ShortMemory(system_prompt="System prompt")
        mem.add({"role": "user", "content": "Hello"})
        mem.add({"role": "assistant", "content": "Hi!"})
        assert len(mem.get()) == 3

        mem.clear()
        messages = mem.get()
        assert len(messages) == 1
        assert messages[0] == {"role": "system", "content": "System prompt"}

    def test_clear_without_system_prompt(self):
        mem = ShortMemory()
        mem.add({"role": "user", "content": "Hello"})
        mem.clear()
        assert mem.get() == []

    def test_sliding_window_trims_by_turns_keeping_system_prompt(self):
        # max_turns=2 keeps the last 2 user turns
        mem = ShortMemory(system_prompt="SYS", max_turns=2)

        # Turn 1
        mem.add({"role": "user", "content": "turn_1"})
        mem.add({"role": "assistant", "content": "ans_1", "tool_calls": [{"id": "c1"}]})
        mem.add({"role": "tool", "tool_call_id": "c1", "content": "tool_out_1"})
        mem.add({"role": "assistant", "content": "final_1"})

        # Turn 2
        mem.add({"role": "user", "content": "turn_2"})
        mem.add({"role": "assistant", "content": "ans_2"})

        # Turn 3
        mem.add({"role": "user", "content": "turn_3"})
        mem.add({"role": "assistant", "content": "ans_3"})

        messages = mem.get()
        # System prompt should remain at index 0
        assert messages[0] == {"role": "system", "content": "SYS"}
        # Turn 1 should be trimmed; Turn 2 should start at index 1
        assert messages[1] == {"role": "user", "content": "turn_2"}
        # Check remaining contents are turn 2 and turn 3
        user_msgs = [m["content"] for m in messages if isinstance(m, dict) and m.get("role") == "user"]
        assert user_msgs == ["turn_2", "turn_3"]



# ---------------------------------------------------------------------------
# Additional trimming edge cases
# ---------------------------------------------------------------------------


def _add_tool_turn(mem: ShortMemory, n: int) -> None:
    """Add one full turn: user -> assistant(tool_call) -> tool -> assistant."""
    mem.add({"role": "user", "content": f"user_{n}"})
    mem.add({"role": "assistant", "content": "", "tool_calls": [{"id": f"call_{n}"}]})
    mem.add({"role": "tool", "tool_call_id": f"call_{n}", "content": f"out_{n}.mid"})
    mem.add({"role": "assistant", "content": f"final_{n}"})


class TestShortMemoryTrimmingEdgeCases:
    """Edge cases for the turn-aware sliding window."""

    def test_trims_langchain_message_objects(self):
        mem = ShortMemory(system_prompt="SYS", max_turns=1)

        mem.add(HumanMessage(content="first"))
        mem.add(AIMessage(content="", tool_calls=[{"id": "c1", "name": "create_midi", "args": {}}]))
        mem.add(ToolMessage(content="a.mid", tool_call_id="c1"))
        mem.add(AIMessage(content="done first"))
        mem.add(HumanMessage(content="second"))
        mem.add(AIMessage(content="done second"))

        messages = mem.get()
        assert messages[0] == {"role": "system", "content": "SYS"}
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "second"
        assert len(messages) == 3

    def test_trims_mixed_dicts_and_message_objects(self):
        mem = ShortMemory(max_turns=1)
        mem.add({"role": "user", "content": "dict user"})
        mem.add(AIMessage(content="reply 1"))
        mem.add(HumanMessage(content="object user"))
        mem.add(AIMessage(content="reply 2"))

        messages = mem.get()
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "object user"
        assert len(messages) == 2

    def test_max_turns_zero_disables_trimming(self):
        mem = ShortMemory(system_prompt="SYS", max_turns=0)
        for n in range(20):
            _add_tool_turn(mem, n)
        assert len(mem.get()) == 1 + 20 * 4

    def test_max_turns_none_disables_trimming(self):
        mem = ShortMemory(system_prompt="SYS", max_turns=None)
        for n in range(20):
            _add_tool_turn(mem, n)
        assert len(mem.get()) == 1 + 20 * 4

    def test_trimming_without_system_prompt(self):
        mem = ShortMemory(max_turns=2)
        for n in range(1, 5):
            _add_tool_turn(mem, n)

        messages = mem.get()
        assert all(m.get("role") != "system" for m in messages)
        assert messages[0] == {"role": "user", "content": "user_3"}
        assert len(messages) == 2 * 4

    def test_no_orphaned_tool_messages_after_trimming(self):
        mem = ShortMemory(system_prompt="SYS", max_turns=2)
        for n in range(1, 8):
            _add_tool_turn(mem, n)

            seen_call_ids: set[str] = set()
            for msg in mem.get():
                if msg.get("role") == "assistant":
                    seen_call_ids.update(call["id"] for call in msg.get("tool_calls", []))
                if msg.get("role") == "tool":
                    assert msg["tool_call_id"] in seen_call_ids, (
                        f"Orphaned tool message after turn {n}: {msg}"
                    )

    def test_clear_after_trimming_resets_to_system_prompt(self):
        mem = ShortMemory(system_prompt="SYS", max_turns=2)
        for n in range(1, 6):
            _add_tool_turn(mem, n)

        mem.clear()
        assert mem.get() == [{"role": "system", "content": "SYS"}]

        # Memory keeps working normally after clear
        _add_tool_turn(mem, 99)
        assert mem.get()[1] == {"role": "user", "content": "user_99"}

    def test_get_returns_live_internal_list(self):
        # Documents current behaviour: get() returns the internal list itself,
        # so changes made by the caller affect the memory.
        mem = ShortMemory(system_prompt="SYS")
        returned = mem.get()
        returned.append({"role": "user", "content": "added from outside"})

        assert mem.get() is returned
        assert mem.get()[-1]["content"] == "added from outside"
