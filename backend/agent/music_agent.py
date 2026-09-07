
from backend.memory.short_term_memory import Memory


class MusicAgent:

    def __init__(self, model, memory: Memory, tools: list):
        self.model = model
        self.memory = memory

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

        while True:

            messages = self.memory.get()
            response = self.model_with_tools.invoke(messages)

            self.memory.add(response)

            if not response.tool_calls:
                return response.content

            # Execute tools
            for tool_call in response.tool_calls:

                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                tool = self.tools[tool_name]

                try:
                    result = tool.invoke(tool_args)

                except Exception as e:
                    result = f"Tool execution failed: {e}"

                # Store tool result
                self.memory.add({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(result)
                })

    def clear_memory(self):
        self.memory.clear()

