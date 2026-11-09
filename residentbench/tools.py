"""
Tools: a function with a description.

The description says what the tool does and nothing else; the model sees
the description and the parameter schema, the loop runs the function.

    function(args, state) -> output

args is the dict of arguments the model filled in; state is the loop's
state object. The output is anything JSON can carry (other values are
passed through str()).
"""


class Tool:

    def __init__(self, name, description, function, parameters=None, required=None):
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters or {}
        self.required = list(self.parameters) if required is None else required

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def __call__(self, args, state):
        try:
            return self.function(args, state)
        except Exception as error:
            return f"error: {type(error).__name__}: {error}"


class Tools(dict):
    """
    A dict from name to Tool. A call to a name that is not in the set
    returns an error output instead of raising.
    """

    def __init__(self, *tools):
        super().__init__((tool.name, tool) for tool in tools)

    def __missing__(self, name):
        return Tool(name, "", lambda args, state: f"error: no tool named {name!r}")
