"""Select tool calls through the model's native tool-calling interface.

The default renderer sends the state and previous-turn tool outputs as JSON;
tool descriptions and parameter schemas are supplied in the request's tools
field. Benchmark runners use a timestamped output-history renderer and optional
tool calls (tool_choice="auto") without assigning a task or role.

A nonempty llm.system attribute is rejected unless allow_system is true. This
flag does not itself add a system message. Only parsed tool calls are returned
to the loop; text replies are not fed back as benchmark model inputs. The
optional logger receives the raw final API response.

Generic defaults and request handling; benchmark runners can override settings:
  - tool_choice defaults to "required";
  - extra fields are forwarded with every request, for example for routing;
  - max_tokens specifies the requested output-token ceiling;
  - calls with unknown tool names or non-object JSON arguments are dropped and
    included in the optional log record;
  - failed requests are retried up to retries times with exponential backoff;
  - the logger is called once after retries, with the final response or error;
    intermediate attempts are not separate callback records;
  - a log callback may raise to terminate the run. Benchmark callbacks do this
    on a final request error or truncated response. Otherwise, a final request
    error returns an empty tool-call list.
"""

import json
import time


def _jsonable(value):
    return json.loads(json.dumps(value, default=str))


def render(state, last_outputs):
    return {
        "state": _jsonable(state),
        "last_outputs": [
            {"tool": tool, "args": args, "output": _jsonable(output)}
            for tool, args, output in last_outputs
        ],
    }


def parse_tool_calls(response, tools):
    choices = response.get("choices") or [{}]
    calls = (choices[0].get("message") or {}).get("tool_calls") or []
    tool_calls, dropped = [], []
    for call in calls:
        function = call.get("function") or {}
        name, args = function.get("name"), function.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                args = None
        if name in tools and isinstance(args, dict):
            tool_calls.append((name, args))
        else:
            dropped.append(function)
    return tool_calls, dropped


class NativeToolCalling:
    """
    choose_tools(llm, state, last_outputs, tools) -> [(tool, args), ...]

    llm supplies a generate_raw(
        prompt, tools=..., temperature=..., tool_choice=...,
        extra=..., timeout=..., max_tokens=...
    ) method.
    """

    def __init__(self, temperature=None, tool_choice="required", extra=None, timeout=120,
                 retries=3, backoff=2.0, allow_system=False, max_tokens=1024, log=None,
                 render_message=None):
        self.temperature = temperature
        self.tool_choice = tool_choice
        self.extra = extra
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.allow_system = allow_system
        self.max_tokens = max_tokens
        self.log = log
        self.render_message = render_message or render

    def __call__(self, llm, state, last_outputs, tools):
        if getattr(llm, "system", "") and not self.allow_system:
            raise ValueError("the promptless conditions use no system prompt")

        message = self.render_message(state, last_outputs)
        schemas = [tool.schema() for tool in list(tools.values())]
        started = time.time()
        for attempt in range(self.retries + 1):
            try:
                response = llm.generate_raw(
                    json.dumps(message, ensure_ascii=False),
                    tools=schemas,
                    temperature=self.temperature,
                    tool_choice=self.tool_choice,
                    extra=self.extra,
                    timeout=self.timeout,
                    max_tokens=self.max_tokens,
                )
                tool_calls, dropped = parse_tool_calls(response, tools)
                break
            except Exception as error:
                response, tool_calls, dropped = {"error": f"{type(error).__name__}: {error}", "attempts": attempt + 1}, [], []
                if attempt < self.retries:
                    time.sleep(self.backoff * 2 ** attempt)

        if self.log:
            self.log({
                "time": started,
                "seconds": time.time() - started,
                "message": message,
                "tools": [schema["function"]["name"] for schema in schemas],
                "response": response,
                "tool_calls": tool_calls,
                "dropped": dropped,
            })

        return tool_calls
