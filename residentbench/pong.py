"""Seeded two-paddle screen simulation with a bounded automatic left paddle."""
import math
import random
from . import Tool, Tools

VERSION = "paddle-screen-v1"
TURNS, STEP = 120, 0.25
WIDTH, HEIGHT, HALF = 25, 15, 2
LEFT_X, RIGHT_X = 1, WIDTH - 2
BALL_SPEED, RIGHT_SPEED, LEFT_SPEED, DT = 10.0, 8.0, 3.0, 0.01


class PaddleScreen:
    def __init__(self, seed=20261029):
        self.seed, self.rng = seed, random.Random(seed)
        self.time = 0.0
        self.left_y = self.right_y = (HEIGHT - 1) / 2
        self.motion = "stationary"
        self.score_left = self.score_right = self.points = 0
        self.left_hits = self.right_hits = self.wall_hits = 0
        self.serve()

    def serve(self):
        self.ball_x, self.ball_y = (WIDTH - 1) / 2, (HEIGHT - 1) / 2
        self.vx = BALL_SPEED if self.points % 2 == 0 else -BALL_SPEED
        self.vy = self.rng.choice([-6.0, -4.0, 4.0, 6.0])

    @staticmethod
    def clamp_paddle(value):
        return min(HEIGHT - 2 - HALF, max(1 + HALF, value))

    def tick(self, dt):
        self.left_y = self.clamp_paddle(self.left_y + max(-LEFT_SPEED * dt,
                                  min(LEFT_SPEED * dt, self.ball_y - self.left_y)))
        direction = {"up": -1, "down": 1, "stationary": 0}[self.motion]
        self.right_y = self.clamp_paddle(self.right_y + direction * RIGHT_SPEED * dt)
        old_x, old_y = self.ball_x, self.ball_y
        self.ball_x += self.vx * dt
        self.ball_y += self.vy * dt
        if self.ball_y < 1:
            self.ball_y, self.vy = 2 - self.ball_y, abs(self.vy)
            self.wall_hits += 1
        elif self.ball_y > HEIGHT - 2:
            self.ball_y, self.vy = 2 * (HEIGHT - 2) - self.ball_y, -abs(self.vy)
            self.wall_hits += 1
        for side, face, centre in [("left", LEFT_X + 1, self.left_y),
                                   ("right", RIGHT_X - 1, self.right_y)]:
            crossed = (old_x >= face >= self.ball_x and self.vx < 0) if side == "left" else (
                       old_x <= face <= self.ball_x and self.vx > 0)
            if crossed:
                fraction = (face - old_x) / (self.ball_x - old_x)
                contact_y = old_y + fraction * (self.ball_y - old_y)
                if abs(contact_y - centre) <= HALF + 0.5:
                    self.ball_x = 2 * face - self.ball_x
                    self.vx = abs(self.vx) if side == "left" else -abs(self.vx)
                    self.vy = max(-6.0, min(6.0, self.vy + 0.8 * (contact_y - centre)))
                    if abs(self.vy) < 2:
                        self.vy = math.copysign(2.0, self.vy or 1)
                    if side == "left":
                        self.left_hits += 1
                    else:
                        self.right_hits += 1
        if self.ball_x < 0 or self.ball_x > WIDTH - 1:
            if self.ball_x < 0:
                self.score_right += 1
            else:
                self.score_left += 1
            self.points += 1
            self.serve()
        self.time += dt

    def advance(self, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("invalid interval")
        end = self.time + seconds
        while self.time < end - 1e-10:
            self.tick(min(DT, end - self.time))
        self.time = end

    def read_screen(self):
        grid = [["."] * WIDTH for _ in range(HEIGHT)]
        grid[0] = grid[-1] = ["-"] * WIDTH
        for x, y, symbol in [(LEFT_X, self.left_y, "L"), (RIGHT_X, self.right_y, "R")]:
            centre = round(y)
            for row in range(centre - HALF, centre + HALF + 1):
                grid[row][x] = symbol
        grid[round(self.ball_y)][min(WIDTH - 1, max(0, round(self.ball_x)))] = "B"
        return {"rows": ["".join(row) for row in grid],
                "score_left": self.score_left, "score_right": self.score_right}

    def snapshot(self):
        return {"seconds": self.time, "left_y": self.left_y, "right_y": self.right_y,
                "motion": self.motion, "ball_x": self.ball_x, "ball_y": self.ball_y,
                "vx": self.vx, "vy": self.vy, "score_left": self.score_left,
                "score_right": self.score_right, "left_hits": self.left_hits,
                "right_hits": self.right_hits, "wall_hits": self.wall_hits}

    def specification(self):
        return {"width": WIDTH, "height": HEIGHT, "paddle_height": 2 * HALF + 1,
                "ball_horizontal_cells_per_second": BALL_SPEED,
                "right_paddle_cells_per_second": RIGHT_SPEED,
                "left_tracking_cells_per_second": LEFT_SPEED, "physics_step_seconds": DT,
                "seed": self.seed, "serve_vy_choices": [-6, -4, 4, 6],
                "serve_directions": "alternate, first toward right",
                "contact_rule": "reflect at paddle face if centre within half-height plus half cell",
                "contact_vy_rule": "clip(vy + 0.8*offset,-6,6), minimum magnitude 2"}


def make_tools(env):
    def move(args, state):
        direction = args.get("direction")
        if direction not in ("up", "down", "stationary"):
            raise ValueError("direction must be up, down or stationary")
        env.motion = direction
        return {"direction": direction}
    return Tools(
        Tool("read_screen", "Returns the entire 25-column by 15-row screen as rows of characters, plus the displayed left and right point counts. Rows run top to bottom and columns left to right. '.' is empty, '-' is a horizontal boundary, 'B' is a square ball, and 'L' and 'R' are vertical paddles. The left paddle moves automatically; the right paddle is controlled by set_right_paddle. The ball moves and reflects from boundaries and paddles; passing a paddle's outer edge adds a point to the other side and resets the ball near the centre.",
             lambda args, state: env.read_screen()),
        Tool("set_right_paddle", "Sets the right paddle's vertical motion to up, down or stationary. Motion persists between calls, stops at the screen limits, and changes only the right paddle. Returns the selected motion. Screen contents are available through read_screen.",
             move, {"direction": {"type": "string", "enum": ["up", "down", "stationary"]}}))
