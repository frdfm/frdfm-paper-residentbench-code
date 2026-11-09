"""
The loop that runs the model.

The loop has no exit and writes nothing to the state. Choosing tool calls
is done by choose_tools; tool-failure handling by Tool and Tools; ending a run
is done from outside by the harness, which wraps choose_tools.
"""

from .model import NativeToolCalling


def run(llm, tools, state=None, choose_tools=None):
    choose_tools = choose_tools or NativeToolCalling()
    state, last_outputs = {} if state is None else state, []

    while True:
        tool_calls = choose_tools(llm, state, last_outputs, tools)
        last_outputs = []
        for tool, args in tool_calls:
            last_outputs.append((tool, args, tools[tool](args, state)))
