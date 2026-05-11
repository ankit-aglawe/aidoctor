# aidoctor TODOs

Deferred items from `/plan-ceo-review` and `/plan-eng-review` (2026-05-11).

## v1.1 (post-launch, weeks 2-4)

### 0. `aidoctor simplify` — three-angle review beyond static linting [P1]
- **What:** New subcommand `aidoctor simplify [PATH]` that emits three parallel review prompts: reuse (duplicated logic, stdlib re-implementations), quality (parameter sprawl, copy-paste, nested ternaries, stringly-typed code), efficiency (N+1 patterns, missed asyncio.gather, hot-path file re-reads).
- **Why:** Static rules are the checkup; `simplify` is the full physical. Differentiates aidoctor from ruff/pylint (static only). Inherits the proven 3-agent pattern from gstack's /simplify but Python-tuned.
- **Shape:** 100% delegation — prints structured prompts to stdout, user pipes into Claude/Cursor/Codex/Gemini. Same model as the agent-install prompt. No API key required.
- **Pro variant (v1.2):** `aidoctor simplify --with claude` detects the user's installed agent CLI and dispatches directly. Still no aidoctor-side LLM cost.
- **Effort:** M (CC: ~4 hours — three prompt templates, agent-CLI detection, integration test)
- **Priority:** P1 — strongest "wow" feature for v1.1 launch tweet.



### 1. LRU cache eviction for CST cache
- **What:** Add bounded-size LRU eviction to `~/.cache/aidoctor/cst-cache/`. Currently grows unbounded.
- **Why:** Big repo scans accumulate hundreds of MB. Power users will notice.
- **Where:** `src/aidoctor/utils/cache.py`
- **Trigger:** When cache size exceeds 500MB or after 30 days.
- **Effort:** S (CC: ~2 hours)
- **Priority:** P2

### 2. `--jobs N` flag platform testing
- **What:** Verify multiprocessing.Pool behavior on Windows + macOS + Linux. macOS spawn-start vs Linux fork-start differs.
- **Why:** v1 ships with default cpu_count(); cross-platform issues likely surface in week 1.
- **Effort:** S (CC: ~1 hour test fixtures + CI matrix)
- **Priority:** P1 (do early in v1.1)

### 3. Optional ruff integration
- **What:** If a user has `ruff` available, run ruff first and merge its findings into aidoctor's output under a separate "Style" category.
- **Why:** Power users want one-stop scoring; ruff covers what we don't.
- **Effort:** M (CC: ~4 hours)
- **Priority:** P2

### 4. Dropped v1 rules (5 rules)
- **What:** Re-attempt the rules dropped in D13:
  - `heuristic-hallucinated-import` (needs package index)
  - `async-fn-missing-await` (needs cross-fn data flow)
  - `suspicious-docstring-boilerplate` (needs regex tuning)
  - `generic-variable-names-in-long-fn` (needs FP reduction)
  - `commented-out-code-blocks` (needs AST-shape detection)
- **Why:** Each was dropped because of false-positive risk; v1.1 can tune them with real user feedback.
- **Effort:** M (CC: ~6 hours total)
- **Priority:** P2

## v1.2-v1.5

### 5. Deferred agent platforms
- **What:** Add skill installer support for Codex, Aider, Copilot Workspace.
- **Why:** Their public skill formats didn't exist at v1 launch.
- **Blocker:** Wait for each platform to publish a skill format spec.
- **Effort:** S per platform (CC: ~1 hour each once spec exists)
- **Priority:** P3 (drive by user requests)

### 6. Per-rule severity override
- **What:** `[tool.aidoctor.severity]` section in config to override default rule severity.
- **Why:** Teams want to promote a warning to error or vice versa.
- **Effort:** S (CC: ~1 hour)
- **Priority:** P2

### 7. TOML rule spec refactor
- **What:** Once we have ~50+ rules, refactor the TOML spec to support rule grouping, plugin imports, and external rule packs.
- **Why:** The v1 spec design will likely diverge in shape as rules grow.
- **Trigger:** When adding rule #50 feels awkward in current spec.
- **Effort:** M (CC: ~4 hours)
- **Priority:** P2

## v2 (months 3-6)

### 8. LLM-powered `aidoctor explain` mode (D8 deferred)
- **What:** `aidoctor explain <rule-id>` reads offending code and uses LLM to write personalized explanation.
- **Why:** Real differentiator from any other Python linter.
- **Constraints:** BYO API key (env var). Default to free tier with rate limits.
- **Effort:** L (CC: ~8 hours)
- **Priority:** P1 for v2

### 9. Web playground at ai-py.doctor (D9 deferred)
- **What:** Hosted web page where users paste code and get a score. No install required.
- **Why:** Lowest-friction try mechanism for Twitter/HN shares.
- **Hosting:** Fly.io or Cloudflare Workers (~$5-20/month). Static analysis only, no code execution.
- **Effort:** L (CC: ~10 hours including auth + abuse handling)
- **Priority:** P1 for v2

### 10. Sister `py-scan` runtime tool
- **What:** Live-runtime profiler that wraps a Python script and flags AI-slop patterns at runtime (N+1 queries, missing async, slow paths). Mirror of Aiden Bai's react-scan + react-doctor pattern.
- **Why:** Twin-tool strategy is the proven star multiplier (react-scan has ~30k stars).
- **Effort:** XL (separate breakout project)
- **Priority:** P1 for v2 once aidoctor establishes brand

### 11. VS Code extension
- **What:** Inline rule violations in editor, hover-explain, quick-fix actions.
- **Why:** Each install is a sticky integration with daily brand impressions.
- **Effort:** L (CC: ~12 hours for VS Code extension scaffolding + LSP server)
- **Priority:** P2 for v2

## v3 (months 6-12)

### 12. Framework plugin packs
- **What:** `django-doctor`, `fastapi-doctor`, `ml-doctor` as plugin packs that extend aidoctor with framework-specific rules.
- **Why:** Vertical depth without bloating core.
- **Effort:** XL (each pack is ~30 rules)
- **Priority:** P2 for v3

### 13. Enterprise dashboard
- **What:** Private leaderboard for orgs (scan all internal repos, score over time, team rankings).
- **Why:** Monetization path; enterprise pays for visibility.
- **Effort:** XL (separate web app + auth + billing)
- **Priority:** P3 (only if v1+v2 prove traction)

## v1.1+ — Inspired by hermes-agent (Nous Research)

Studied 2026-05-11. Their patterns worth adopting when aidoctor grows a third-party rule-pack ecosystem.

### 14. Quarantine + scan + confirm install flow
- **What:** When users install third-party rule packs from a URL/GitHub, fetch to quarantine dir → security-scan for dangerous code → show metadata panel → user consents → copy to live dir.
- **Why:** Trust model for community-contributed rule packs. Inspired by `hermes_cli/skills_hub.py:do_install()`.
- **Effort:** M (CC: ~4 hours)
- **Priority:** P3 — only when we have a real community rule-pack ecosystem
- **Blocker:** Wait for v1 traction to justify

### 15. Short-name resolver with multi-source registry
- **What:** `aidoctor install <short-name>` resolves across official + GitHub + community sources. e.g. `aidoctor install pep8-rules` finds it on PyPI or aidoctor's curated registry.
- **Why:** Cleaner UX than hardcoded paths. Pattern from hermes-agent's `_resolve_short_name`.
- **Effort:** M (CC: ~3 hours)
- **Priority:** P3 — depends on rule-pack ecosystem existing first

### 16. Per-target enable/disable config
- **What:** Toggle individual rules per agent target. Same rule could be on for Claude, off for Continue.dev. Stored in `~/.aidoctor/config.yaml`.
- **Why:** Power user use case. Pattern from `hermes_cli/skills_config.py`.
- **Effort:** S (CC: ~2 hours)
- **Priority:** P2 — request-driven

## Won't do

- **Remote telemetry by default**: privacy-first. No opt-out shipped in v1, ever. Opt-in only if added at all.
- **Pure stdlib `ast` engine**: rejected in D11; libcst's richer API is load-bearing.
- **Direct `python-doctor` branding**: rejected in D1 in favor of ai-python-doctor wedge.
- **GitHub Action for arbitrary languages**: aidoctor is Python-specific by design. Multi-language splits the wedge.
