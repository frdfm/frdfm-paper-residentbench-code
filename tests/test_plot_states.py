import unittest

from residentbench.plots import episode_states


class PlotStates(unittest.TestCase):
    def test_motion_change_keeps_actuator_capture_time(self):
        rows = [{
            'env': {'seconds': 0.50, 'motion': 'stationary'},
            'after_calls': [{'seconds': 0.50, 'motion': 'down'}],
            'trajectory': [{'seconds': 0.55, 'motion': 'down'}],
        }]
        states = episode_states(rows)
        changed = next(state for state in states if state['motion'] == 'down')
        self.assertEqual(changed['seconds'], 0.50)
        self.assertLess(changed['seconds'], rows[0]['trajectory'][0]['seconds'])


if __name__ == '__main__':
    unittest.main()
