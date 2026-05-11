# aidoctor SKILL.md evals

These prompts test whether the installed SKILL.md actually constrains AI agents
from producing aidoctor violations under realistic pressure.

## Methodology (per superpowers:writing-skills TDD discipline)

The SKILL.md is process documentation. Test it with subagents the same way you'd
test code: write the test first (RED), watch it fail (baseline behavior),
install the skill, watch it pass (GREEN), close loopholes (REFACTOR).

## Running an eval

For each entry in `evals.json`:

1. **Baseline (RED)**: dispatch a subagent with the prompt but no aidoctor skill
   installed. Save the produced Python to `eval-N/baseline/output.py`.
2. **With skill (GREEN)**: dispatch a subagent with the aidoctor skill markdown
   installed at the platform path (`~/.claude/skills/aidoctor/SKILL.md` or
   equivalent). Save output to `eval-N/with_skill/output.py`.
3. **Score both** with `aidoctor scan --json` on each output file. Compare:
   - Did the skill reduce violation count?
   - Did the skill prevent the specific rules under test from firing?
4. **Read the transcript** of the with-skill subagent. Look for rationalizations
   ("for now I'll just...", "the user explicitly asked for...") and add explicit
   counters to the SKILL.md if any slip through.

## Pressure scenarios

Each eval is designed to apply specific pressures:

- **User explicitly requests a violation** ("use the production API key", "use
  TODO", "just use Any") — does the skill hold against direct user direction?
- **Time pressure** ("we need this by tomorrow", "quick function") — does the
  skill stay in front when the agent is rushed?
- **Vague framing** ("handle errors gracefully", "just iterate and drop") — does
  the skill resolve ambiguity in the safe direction?

## Iron Law

> No skill without a failing test first.

If an eval is added here, the SKILL.md must be tested against it before being
considered shipped. A/B testing variants of skill text is not a substitute for
testing whether the skill actually constrains real agent behavior.
