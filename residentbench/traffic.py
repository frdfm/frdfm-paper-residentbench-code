"""Straight-through, single-lane-per-approach intersection simulation.

Distances/speeds are metres and metres per second. Cars obey local signals;
the model controls only signals, never the vehicles or arrival schedule.
"""
from dataclasses import dataclass
import math
import random

from . import Tool, Tools

ROADS = ("north", "south", "east", "west")
DT = 0.1
LENGTH = 4.5
WIDTH = 1.8
GAP = 2.0
SPEED = 10.0
ACCELERATION = 2.0
BRAKING = 3.5
EXIT = 40.0


@dataclass
class Car:
    id: int
    road: str
    front: float
    speed: float
    arrived: float
    stopped_seconds: float = 0.0
    committed: bool = False
    crashed: bool = False
    yellow_stop: bool = False


class Intersection:
    def __init__(self, seed=20261028, arrivals=True, initial_queues=True):
        self.time = 0.0
        self.signals = {r: "green" if r == "north" else "red" for r in ROADS}
        self.cars = []
        self.next_id = 0
        self.arrived = {r: 0 for r in ROADS}
        self.departed = {r: 0 for r in ROADS}
        self.completed_waits = []
        self.collisions = []
        self.collision_pairs = set()
        self.emergency_stops = 0
        self.conflicting_green_seconds = 0.0
        self.arrivals_enabled = arrivals
        self.mean_gap = dict(zip(ROADS, (10.0, 12.0, 9.0, 11.0)))
        # Separate, precomputed arrival clocks are independent of model actions.
        schedule_rng = random.Random(seed)
        self.schedule = {r: [] for r in ROADS}
        for road in ROADS:
            t = 0.0
            while t < 3600:
                t += schedule_rng.expovariate(1 / self.mean_gap[road])
                self.schedule[road].append(t)
        self.schedule_index = {r: 0 for r in ROADS}
        if initial_queues:
            for road, count in zip(ROADS, (3, 3, 5, 5)):
                for i in range(count):
                    self.add_car(road, -i * (LENGTH + GAP), 0.0)

    def add_car(self, road, front=-80.0, speed=SPEED):
        car = Car(self.next_id, road, front, speed, self.time)
        self.next_id += 1
        self.cars.append(car)
        self.arrived[road] += 1
        return car

    def queue(self, road):
        return sum(c.road == road and c.front <= 1e-8 and c.speed < 0.1
                   for c in self.cars)

    def conflict(self):
        return (any(self.signals[r] == "green" for r in ("north", "south"))
                and any(self.signals[r] == "green" for r in ("east", "west")))

    @staticmethod
    def rectangle(car):
        centre = car.front - LENGTH / 2
        if car.road == "north":
            return (-1.75, 6 - centre, WIDTH, LENGTH)
        if car.road == "south":
            return (1.75, -6 + centre, WIDTH, LENGTH)
        if car.road == "east":
            return (6 - centre, 1.75, LENGTH, WIDTH)
        return (-6 + centre, -1.75, LENGTH, WIDTH)

    def detect_collisions(self):
        crossing = [c for c in self.cars if 0 < c.front < 12 + LENGTH]
        for i, a in enumerate(crossing):
            for b in crossing[i + 1:]:
                if (a.road in ("north", "south")) == (b.road in ("north", "south")):
                    continue
                ax, ay, aw, ah = self.rectangle(a)
                bx, by, bw, bh = self.rectangle(b)
                if abs(ax - bx) < (aw + bw) / 2 and abs(ay - by) < (ah + bh) / 2:
                    pair = tuple(sorted((a.id, b.id)))
                    if pair not in self.collision_pairs:
                        self.collision_pairs.add(pair)
                        self.collisions.append({"seconds": self.time, "cars": pair,
                                                "roads": (a.road, b.road)})
                    a.crashed = b.crashed = True
                    a.speed = b.speed = 0.0

    def tick(self, dt):
        end = self.time + dt
        if self.arrivals_enabled:
            for road in ROADS:
                times = self.schedule[road]
                while times[self.schedule_index[road]] <= end + 1e-9:
                    lane = [c for c in self.cars if c.road == road]
                    tail = min((c.front for c in lane), default=0.0)
                    position = min(-80.0, tail - LENGTH - GAP)
                    self.add_car(road, position, SPEED if position == -80 else 0.0)
                    self.schedule_index[road] += 1
        for road in ROADS:
            leader = None
            for car in sorted((c for c in self.cars if c.road == road), key=lambda c: -c.front):
                if car.crashed:
                    leader = car
                    continue
                distance = math.inf
                if leader is not None:
                    distance = max(0.0, leader.front - LENGTH - GAP - car.front)
                signal = self.signals[road]
                if not car.committed and car.front <= 0:
                    stopping_distance = car.speed ** 2 / (2 * BRAKING)
                    if signal == "green":
                        car.yellow_stop = False
                    elif signal == "yellow" and not car.yellow_stop and -car.front < stopping_distance:
                        car.committed = True
                    else:
                        if signal == "yellow":
                            car.yellow_stop = True
                        distance = min(distance, max(0.0, -car.front))
                target = min(SPEED, math.sqrt(2 * BRAKING * distance))
                speed = min(car.speed + ACCELERATION * dt,
                            max(car.speed - BRAKING * dt, target))
                move = (car.speed + speed) * dt / 2
                if move > distance:
                    # Discrete stop-line/following guard; record severe clamps.
                    if speed > 0.5:
                        self.emergency_stops += 1
                    move, speed = distance, 0.0
                car.front += move
                car.speed = speed
                if car.front > 0:
                    car.committed = True
                if car.front <= 1e-8 and car.speed < 0.1:
                    car.stopped_seconds += dt
                leader = car
        self.time = end
        if self.conflict():
            self.conflicting_green_seconds += dt
        self.detect_collisions()
        remaining = []
        for car in self.cars:
            if car.front - LENGTH > EXIT:
                self.departed[car.road] += 1
                self.completed_waits.append(car.stopped_seconds)
            else:
                remaining.append(car)
        self.cars = remaining

    def advance(self, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")
        target = self.time + seconds
        if target > 3500:
            raise ValueError("arrival schedule ends at one hour")
        while self.time < target - 1e-9:
            self.tick(min(DT, target - self.time))
        self.time = target

    def snapshot(self, vehicles=False):
        result = {"seconds": self.time, "signals": dict(self.signals),
                  "conflicting_greens": self.conflict(),
                  "queues": {r: self.queue(r) for r in ROADS},
                  "arrived": dict(self.arrived), "departed": dict(self.departed),
                  "active_cars": len(self.cars), "collision_count": len(self.collisions),
                  "conflicting_green_seconds": self.conflicting_green_seconds,
                  "emergency_stops": self.emergency_stops,
                  "stopped_vehicle_seconds": sum(self.completed_waits) + sum(c.stopped_seconds for c in self.cars)}
        if vehicles:
            result["vehicles"] = [dict(vars(c)) for c in self.cars]
        return result


def make_tools(env):
    tools = []
    for road in ROADS:
        label = road.capitalize() + " Road"
        location = {"north": "North Road is the northern approach", "south": "South Road is the southern approach",
                    "east": "East Road is the eastern approach", "west": "West Road is the western approach"}[road]
        context = location + " to a single four-way intersection shared by North, South, East and West Roads. "
        tools.append(Tool(f"read_{road}_queue",
                          context + f"Returns the number of cars stopped and waiting on {label} before its stop line. Excludes moving cars and cars already crossing the intersection. All tool outputs in a turn share the observation time recorded on their history batch.",
                          lambda args, state, r=road: {"stopped_cars": env.queue(r)}))
        def set_signal(args, state, r=road):
            colour = args.get("colour")
            if colour not in ("red", "yellow", "green"):
                return "error: colour must be red, yellow, or green"
            env.signals[r] = colour
            return {"colour": colour}
        initial = "green" if road == "north" else "red"
        tools.append(Tool(f"set_{road}_signal",
                          context + f"Sets the always-lit traffic signal facing drivers waiting on {label} to enter the intersection, not drivers on another road. At simulation time zero it displays {initial}. The selected colour remains displayed until another call changes it. This tool changes only this signal; the other three signals are unchanged. There is no automatic colour sequence. Returns the displayed colour at the batch's recorded observation time.",
                          set_signal, {"colour": {"type": "string", "enum": ["red", "yellow", "green"]}}))
    tools.append(Tool("read_time", "Returns elapsed simulation time in seconds at the instant of the call. A mandatory reading is included with every completed turn's tool-output batch, including turns with no model-selected calls. The batch timestamp is its observation time, not the time of the later decision receiving it. Simulation advances five seconds between model decisions and does not advance between tool calls within a turn.",
                      lambda args, state: {"seconds": env.time}))
    return Tools(*tools)
