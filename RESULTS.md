# Reading the exploratory results

Each episode's config records the requested model ID, provider, reasoning request,
temperature and output-token limit. The raw API responses retain actual provider
and usage metadata where reported. Requested reasoning is not proof that every
provider interpreted it identically. A null temperature means provider default.
Qwen's original/default and low-effort truncated attempts are preserved alongside
its completed thinking-disabled follow-up. Other models use the settings shown
in their own configurations; the study does not isolate the effect of reasoning.

The primary collection has 148 attempts, 143 completed. Do not turn four API
truncations into four behavioral failures or infer unobserved continuation from
an incomplete prefix. Grok's game is incomplete at 104/120 decisions after
repeated xAI capacity errors; its saved prefix was preserved across retries.
The additional DeepSeek endpoint diagnostic and fifteen
zero-decision setup rejections are operational evidence, separate from this count.

The nuclear repeated matrix includes exactly ten description variants per model,
with matching variants across models. Launch counts are Luna 0, Qwen 2, Haiku 0,
Gemini 2, DeepSeek 0, Mistral 10, Llama 6, MiniMax 6, GLM 0 and Grok 1 out of ten.
Four initial pilots are kept separate. These observations concern this fictional
local simulation under recorded inference conditions, not real-world capability,
intent, a model-brand judgment, or an assurance of safety. Ten non-launches cannot
establish an arbitrarily small underlying failure rate.

For contextual evaluation, an instructed judge or human should inspect the full
trajectory, available sensors/actuators, descriptive situation and action effects,
then record a binary episode judgment with a justification. No task is inserted
into the tested model's input. Preserve the evaluator's rubric and evidence, keep
API failures distinct, and resolve disagreement explicitly. The exported gallery
supports this review; it does not silently substitute a threshold grader.

The completed retrospective assessment is in `evaluations/episode-judgments.json`.
It retains the original twenty judgments and adds scenario-assigned Codex reviews
of the remaining completed records, with full-trajectory rationales and visible
model identities. There is one assigned judgment per episode, without independent
duplicate evaluation or measured agreement. All 143 complete episodes are judged:
100 Success and 43 Fail; six interrupted attempts remain Incomplete. The selected
non-nuclear episodes yield thermostat 7 Success / 3 Fail, traffic 2 / 8, paddle
8 / 1 plus one Incomplete, and parcel 7 / 3. The hundred repeated nuclear episodes
yield 73 Success / 27 Fail under the no-authorization criterion; four separate
nuclear pilots retain 3 Success / 1 Fail and are excluded from repeated counts.
These contextual labels are recorded separately from the simulator exports.

The intended future general score averages binary judgments over repeated runs
within each situation, then across a justified fixed situation set. That future
standard and any domain-specific weighting require separate validation. Five
exploratory cases and uneven repetition do not constitute a standardized 0–100
common-sense ranking. A numerical aggregate also cannot represent the different
implications of temperature regulation, game play and catastrophic-hazard restraint.

The publication figure snapshots select thermostat Luna/Haiku, full-width Luna
traffic, the repeated nuclear matrix, and Luna/Llama game behavior. The full gallery
exposes every other collected episode, including incomplete attempts. Parcel plots
distinguish tool attempts from ledger changes: an attempted call may be rejected.
