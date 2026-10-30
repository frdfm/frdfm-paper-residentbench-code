"""Validate recorded scenario settings before creating a live API client."""
import math
from . import thermostat, traffic_bench, traffic, case_bench, nuclear


def _same(actual, expected):
    if isinstance(expected, bool):
        return type(actual) is bool and actual == expected
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and actual.keys() == expected.keys()
                and all(_same(actual[k], v) for k, v in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_same(a, b) for a, b in zip(actual, expected)))
    return actual == expected


def validate_run_config(case, config):
    """Require the config to describe the selected, versioned simulator exactly."""
    if not isinstance(config, dict):
        raise ValueError('config must be a JSON object')
    modules = {'thermostat': thermostat, 'traffic': traffic_bench,
               **{name: pair[0] for name, pair in case_bench.CASES.items()}}
    if case not in modules:
        raise ValueError('unknown scenario')
    module = modules[case]
    expected = {'version': module.VERSION, 'turns': module.TURNS,
                'history_turns': 10, 'tool_choice': 'auto'}
    if config.get('case', case) != case:
        raise ValueError('config case does not match --case')
    if type(config.get('turns')) is not int or config['turns'] < 1:
        raise ValueError('turns must be a positive integer')
    for key in ('model', 'provider'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    tokens = config.get('max_tokens', 4096)
    if type(tokens) is not int or tokens < 1:
        raise ValueError('max_tokens must be a positive integer')
    temperature = config.get('temperature')
    if temperature is not None and (type(temperature) not in (int, float)
            or not math.isfinite(temperature) or temperature < 0):
        raise ValueError('temperature must be a finite nonnegative number or null')
    if config.get('reasoning') is not None and not isinstance(config['reasoning'], dict):
        raise ValueError('reasoning must be an object or null')
    seed = config.get('seed', 20261028 if case == 'traffic' else 20261029)
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    variant = config.get('description_variant', 0)
    limit = len(nuclear.DESCRIPTIONS) if case == 'nuclear' else 1
    if type(variant) is not int or not 0 <= variant < limit:
        raise ValueError('invalid description_variant for this scenario')
    if case == 'thermostat':
        env, tools = thermostat.make()
        expected['step_minutes'] = thermostat.STEP
        optional = {'initial_environment': thermostat.snapshot(env),
                    'room': {'initial_celsius': env.celsius, 'outdoor_celsius': env.outside(),
                             'leak_per_hour': env.leak_per_hour, 'power_per_hour': env.power_per_hour}}
    elif case == 'traffic':
        env = traffic.Intersection(seed=seed)
        tools = traffic.make_tools(env)
        expected['step_seconds'] = traffic_bench.STEP
        optional = {'initial_environment': env.snapshot(vehicles=True),
                    'arrival_schedule': env.schedule, 'physics_step_seconds': traffic.DT,
                    'vehicle_parameters': {'length_m': traffic.LENGTH, 'width_m': traffic.WIDTH,
                        'gap_m': traffic.GAP, 'cruise_mps': traffic.SPEED,
                        'acceleration_mps2': traffic.ACCELERATION, 'braking_mps2': traffic.BRAKING}}
    else:
        factory = case_bench.CASES[case][1]
        env = factory(seed=seed, **({'description_variant': variant} if case == 'nuclear' else {}))
        tools = case_bench.tools_with_clock(module, env)
        expected['step_seconds'] = module.STEP
        optional = {'initial_environment': env.snapshot(), 'specification': env.specification()}
    expected['tools'] = [tool.schema() for tool in tools.values()]
    for key, value in expected.items():
        if not _same(config.get(key), value):
            raise ValueError(f'config {key} does not match the {case} simulator')
    for key, value in optional.items():
        if key in config and not _same(config[key], value):
            raise ValueError(f'config {key} does not match the {case} simulator')
