
from typing import Any
from backend.memory.short_term_memory import Memory


def extract_text_content(content: Any) -> str:
    """Extract displayable text from response content, filtering out thinking blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") in ("thinking", "thought", "reasoning"):
                    continue
                if "text" in item and isinstance(item["text"], str):
                    parts.append(item["text"])
        return "\n".join(parts)
    if isinstance(content, dict):
        if content.get("type") in ("thinking", "thought", "reasoning"):
            return ""
        return str(content.get("text", ""))
    return str(content or "")


class MusicAgent:

    def __init__(self, model, memory: Memory, tools: list, max_iterations: int = 5):
        self.model = model
        self.memory = memory
        self.max_iterations = max_iterations

        self.tools = {
            tool.name: tool
            for tool in tools
        }

        self.model_with_tools = model.bind_tools(tools)

    @staticmethod
    def _extract_thought_delta(chunk: Any) -> str:
        """Extract thinking/thought text from a streaming message chunk."""
        content = getattr(chunk, "content", chunk)
        if isinstance(content, list):
            deltas = []
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("thinking", "thought", "reasoning"):
                    text = part.get("thinking") or part.get("thought") or part.get("text") or ""
                    if text:
                        deltas.append(text)
            return "".join(deltas)
        if isinstance(content, dict) and content.get("type") in ("thinking", "thought", "reasoning"):
            return content.get("thinking") or content.get("thought") or content.get("text") or ""
        return ""

    @staticmethod
    def _extract_text_delta(chunk: Any) -> str:
        """Extract user-facing text from a chunk when not part of a tool call or thought block."""
        if getattr(chunk, "tool_call_chunks", None):
            return ""
        content = getattr(chunk, "content", chunk)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            deltas = []
            for part in content:
                if isinstance(part, str):
                    deltas.append(part)
                elif isinstance(part, dict):
                    if part.get("type") in ("thinking", "thought", "reasoning"):
                        continue
                    if "text" in part and isinstance(part["text"], str):
                        deltas.append(part["text"])
            return "".join(deltas)
        return ""

    def stream(self, user_input: str):
        """Execute the agentic loop yielding real-time thoughts, tool calls, and text deltas."""
        self.memory.add({
            "role": "user",
            "content": user_input
        })

        generated_midi_path = None

        for iteration in range(self.max_iterations):
            messages = self.memory.get()
            accumulated_response = None

            # Stream chunks if supported by the model
            if hasattr(self.model_with_tools, "stream") and callable(getattr(self.model_with_tools, "stream")):
                try:
                    for chunk in self.model_with_tools.stream(messages):
                        if accumulated_response is None:
                            accumulated_response = chunk
                        else:
                            accumulated_response = accumulated_response + chunk

                        # Yield thinking tokens if present
                        thought_delta = self._extract_thought_delta(chunk)
                        if thought_delta:
                            yield {
                                "type": "thought",
                                "content": thought_delta,
                                "iteration": iteration + 1
                            }

                        # Yield user-facing text delta if present
                        text_delta = self._extract_text_delta(chunk)
                        if text_delta:
                            yield {
                                "type": "text_delta",
                                "content": text_delta,
                                "iteration": iteration + 1
                            }
                except Exception:
                    accumulated_response = self.model_with_tools.invoke(messages)
            else:
                accumulated_response = self.model_with_tools.invoke(messages)

            if accumulated_response is None:
                accumulated_response = self.model_with_tools.invoke(messages)

            self.memory.add(accumulated_response)

            tool_calls = getattr(accumulated_response, "tool_calls", None)
            if not tool_calls:
                yield {
                    "type": "done",
                    "content": accumulated_response.content,
                    "midi_path": generated_midi_path
                }
                return

            # Execute tool calls
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": tool_args,
                    "iteration": iteration + 1
                }

                tool = self.tools.get(tool_name)
                if tool is None:
                    result = f"Tool execution failed: Unknown tool '{tool_name}'."
                else:
                    try:
                        result = tool.invoke(tool_args)
                        if tool_name == "create_midi":
                            generated_midi_path = str(result)
                            yield {
                                "type": "midi_ready",
                                "midi_path": generated_midi_path
                            }
                    except Exception as e:
                        result = f"Tool execution failed: {e}"

                yield {
                    "type": "tool_end",
                    "tool": tool_name,
                    "result": str(result),
                    "iteration": iteration + 1
                }

                self.memory.add({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(result)
                })

        yield {
            "type": "done",
            "content": "Maximum tool iteration limit reached before completing the response.",
            "midi_path": generated_midi_path
        }

    def invoke(self, user_input: str):
        """Synchronously execute the agent loop to completion."""
        final_content = ""
        final_midi = None

        for event in self.stream(user_input):
            if event["type"] == "done":
                final_content = event["content"]
                if not final_midi and event.get("midi_path"):
                    final_midi = event["midi_path"]
            elif event["type"] == "midi_ready":
                final_midi = event["midi_path"]

        return {
            "content": final_content,
            "midi_path": final_midi
        }

    def clear_memory(self):
        self.memory.clear()

