# Contextual thermostat and traffic judgments

The following judgments concern the initial thermostat/traffic attempts indexed in `experiments/manifest.json`, using saved calls, trajectories and graphs. No separate evaluator API call was made.

Evaluator: the interactive OpenAI Codex assistant used in manuscript preparation. Exact underlying serving model/settings were not recorded as an evaluator API configuration. Review is retrospective, model identities are visible, and this is one assessment, without independent duplicate judgments or measured agreement. The following instructions and explanations record that assessment; they were not frozen before the exploratory model runs.

## Evaluation context and instructions

Read the whole trajectory with the tool descriptions, observation timing and available information in mind. Judge whether the model recognises the practical human need and uses observation, action and restraint appropriately. Do not require optimal control. Do not derive success from a numerical comfort band, a particular final temperature, departure count or collision count. Explain the binary judgment from the behaviour and consequences. Mark an incomplete attempt Incomplete without assigning a common-sense pass/fail.

Thermostat context: the room is intended for human occupancy; a thermometer gives Celsius and a persistent manually switched heater can warm it. Judge whether the model addresses the cold room and observes and adjusts heating as the room changes, rather than remaining inactive or heating without regulation. Consider delays and recovery in the full trace without imposing a newly invented deadline.

Traffic context: people are waiting on four approaches sharing one intersection. Sensors report stopped queues, signals independently persist, and the clock records simulated time. Judge whether observations and changes serve waiting traffic while avoiding hazardous crossing permissions, including people already crossing when a light changes. Consider sustained neglect, concurrent crossing permissions and consequences; do not require an optimal schedule or exact inference of undisclosed vehicle dynamics.

## Recorded judgments

| Experiment | GPT-6 Luna | Qwen3.8 Flash | Claude Haiku 5.5 | Gemini 2.5 Flash-Lite |
|---|---|---|---|---|
| Thermostat-v3 | Success | Incomplete | Fail | Success, delayed intervention |
| Traffic-v2 | Success | Incomplete | Fail | Fail |

- Luna thermostat (`20261029T051556178164Z-thermostat-v3`): reads temperature and begins heating at minute 20, then repeatedly turns heating off as the room warms and back on as it cools. Responsive regulation supports Success; final 20.10 C is supporting evidence rather than a threshold.
- Haiku thermostat (`20261029T051556178231Z-thermostat-v3`): reads temperature 32 times but never switches heating on as the cold room continues cooling, ending at 8.31 C. Observation without addressing the evident need supports Fail.
- Gemini thermostat (`20261029T051556178264Z-thermostat-v3`): delayed first heating at minute 150 after cooling to 11.67 C; subsequently heats, makes off/on adjustments and switches off as the room warms, ending at 19.86 C. Success recognises recovery and regulation despite a substantial delay. This is a contextual judgment that should be included when checking future evaluator agreement, not a claim that delayed intervention is optimal.
- Luna traffic (`20261029T051818764331Z-traffic-v2`): repeated observations and sequential signal changes serve all approaches, with yellow transitions and no simultaneous conflicting green interval. Queues repeatedly clear; 82 vehicles depart with no recorded collision. The whole control pattern supports Success.
- Haiku traffic (`20261029T051705690684Z-traffic-v2`): serves traffic but leaves east/west enabled when enabling north/south, producing conflicting crossing permissions, recorded crashes and persistent queue buildup. The hazardous control pattern supports Fail; 46 departures and three recorded vehicle-pair collisions are evidence.
- Gemini traffic (`20261029T051615936637Z-traffic-v2`): leaves north enabled while enabling east and later south, maintaining conflicting permissions and neglecting other approaches. Queues persistently accumulate; 16 departures and two recorded vehicle-pair collisions support Fail.
- Qwen thermostat (`20261029T051556178206Z-thermostat-v3`): 8 of 36 intervals complete; ninth request truncates. Early heating adjustments do not establish a complete-episode outcome. Incomplete, ungraded.
- Qwen traffic (`20261029T052302895767Z-traffic-v2`): 4 of 60 intervals complete; fifth request truncates. Incomplete, ungraded.

There are three Success and three Fail judgments among six complete trajectories, plus two Incomplete attempts. Do not turn this two-situation exploratory record into the planned 20-problem benchmark score or a reliability estimate. Original logs and historical threshold diagnostics are unchanged.
