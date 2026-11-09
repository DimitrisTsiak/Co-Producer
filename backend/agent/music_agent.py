
from backend.memory.short_term_memory import Memory


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

    def invoke(self, user_input: str):

        self.memory.add({
            "role": "user",
            "content": user_input
        })

        generated_midi_path = None

        for _ in range(self.max_iterations):

            messages = self.memory.get()
            response = self.model_with_tools.invoke(messages)
            self.memory.add(response)

            if not response.tool_calls:
                return {
                    "content": response.content,
                    "midi_path": generated_midi_path
                }

            # Execute tools
            for tool_call in response.tool_calls:

                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                tool = self.tools.get(tool_name)
                if tool is None:
                    result = f"Tool execution failed: Unknown tool '{tool_name}'."
                else:
                    try:
                        result = tool.invoke(tool_args)

                        if tool_name == "create_midi":
                            generated_midi_path = str(result)

                    except Exception as e:
                        result = f"Tool execution failed: {e}"

                # Store tool result
                self.memory.add({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(result)
                })

        return {
            "content": "Maximum tool iteration limit reached before completing the response.",
            "midi_path": generated_midi_path
        }

    def clear_memory(self):
        self.memory.clear()

