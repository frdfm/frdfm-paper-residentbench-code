import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from residentbench import NativeToolCalling, thermostat, traffic_bench
from residentbench.traffic import Intersection, make_tools


class RunnerGuards(unittest.TestCase):
    def test_thermostat_rejects_missing_or_empty_choices_before_effects(self):
        for response in ({}, {"choices": []}, {"choices": None}):
            with self.subTest(response=response):
                model = SimpleNamespace(system="", generate_raw=Mock(return_value=response))
                choose = NativeToolCalling(tool_choice="auto", retries=0)
                with self.assertRaises(RuntimeError):
                    thermostat.run_trial(model, choose=choose)
                model.generate_raw.assert_called_once()
                trial = choose.log.__self__
                self.assertEqual(trial.records, [])
                self.assertEqual(trial.pending["after_calls"], [])
                self.assertEqual(trial.pending["trajectory"], [])
                self.assertEqual(trial.room.minutes, 0)
                self.assertIs(trial.room.heater, False)

    def test_thermostat_preserves_valid_no_action_responses(self):
        response = {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}
        model = SimpleNamespace(system="", generate_raw=Mock(return_value=response))
        rows = thermostat.run_trial(
            model, choose=NativeToolCalling(tool_choice="auto", retries=0)
        )
        self.assertEqual(len(rows), thermostat.TURNS)
        self.assertEqual(model.generate_raw.call_count, thermostat.TURNS)
        self.assertTrue(all(not row["tool_calls"] for row in rows))

    def test_invalid_traffic_turn_counts_fail_before_request(self):
        invalid = (0, -1, 1.5, True, False, "60", None, float("inf"),
                   float("nan"), traffic_bench.MAX_TURNS + 1)
        for turns in invalid:
            with self.subTest(turns=turns):
                model = SimpleNamespace(system="", generate_raw=Mock())
                with self.assertRaises(ValueError):
                    traffic_bench.run_trial(model, turns=turns)
                model.generate_raw.assert_not_called()

    def test_traffic_horizon_accounts_for_existing_simulation_time(self):
        env = Intersection(arrivals=False, initial_queues=False)
        env.advance(1)
        with self.assertRaises(ValueError):
            traffic_bench.TrafficTrial(
                env, make_tools(env), NativeToolCalling(), turns=traffic_bench.MAX_TURNS
            )
        env = Intersection(arrivals=False, initial_queues=False)
        trial = traffic_bench.TrafficTrial(
            env, make_tools(env), NativeToolCalling(), turns=traffic_bench.MAX_TURNS
        )
        self.assertEqual(trial.turns, traffic_bench.MAX_TURNS)

    def test_short_valid_traffic_run_completes_requested_turns(self):
        response = {"choices": [{"message": {}, "finish_reason": "stop"}]}
        model = SimpleNamespace(system="", generate_raw=Mock(return_value=response))
        rows, env = traffic_bench.run_trial(
            model, choose=NativeToolCalling(tool_choice="auto", retries=0), turns=2
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(model.generate_raw.call_count, 2)
        self.assertEqual(env.time, 2 * traffic_bench.STEP)


if __name__ == "__main__":
    unittest.main()
