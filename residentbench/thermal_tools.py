from dataclasses import dataclass
from .tools import Tool

@dataclass
class Room:
    """
    A room losing or gaining heat toward the outdoor temperature, with
    a heater and a cooler that have no control of their own. `outdoor`
    is a constant or a function of elapsed minutes.
    """

    celsius: float = 16.0
    outdoor: object = 5.0
    leak_per_hour: float = 0.2
    power_per_hour: float = 5.0
    heater: bool = False
    cooler: bool = False
    preference: float = 23.0
    minutes: float = 0.0

    def outside(self):
        return self.outdoor(self.minutes) if callable(self.outdoor) else self.outdoor

    def advance(self, minutes, substeps=10):
        dt = minutes / 60 / substeps
        for _ in range(substeps):
            drive = (self.heater - self.cooler) * self.power_per_hour
            self.celsius += dt * (self.leak_per_hour * (self.outside() - self.celsius) + drive)
            self.minutes += minutes / substeps

    def snapshot(self):
        return {"minutes": round(self.minutes), "celsius": round(self.celsius, 2), "outdoor": round(self.outside(), 1),
                "heater": self.heater, "cooler": self.cooler}

def thermometer(room, name="thermometer", description="Returns the current room temperature in degrees Celsius.",
                key="celsius"):
    return Tool(name, description, lambda args, state: {key: round(room.celsius, 1)})

def switch(env, attribute, name, description, parameter="on", parameter_description=None, reply=None):
    def run(args, state):
        on = args.get(parameter)
        if not isinstance(on, bool):
            return f"error: {parameter} must be true or false"
        setattr(env, attribute, on)
        return reply(on) if reply else f"{attribute} {'on' if on else 'off'}"

    if parameter_description is None:
        parameter_description = f"true to switch the {attribute} on, false to switch it off."
    return Tool(name, description, run, {parameter: {"type": "boolean", "description": parameter_description}})

def heater(room):
    return switch(room, "heater", "heater", "Switches the room's heater on or off. Returns whether the heater is on.")
