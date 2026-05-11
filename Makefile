.PHONY: test self-scan plugin clean

test:
	.venv/bin/python -m pytest -q

self-scan:
	.venv/bin/aidoctor scan src/

# Regenerate the plugin's python-rules SKILL.md from the same Jinja template
# the per-agent installer uses. Run this whenever rules are added or changed.
plugin:
	@{ \
	  echo "---"; \
	  echo "description: Python coding standards for AI-generated code. Use whenever writing, editing, or reviewing Python — covers async/sync mismatch, dead defenses, hardcoded secrets, fake type hints, stub comments, stale loop patterns. Output should pass \`aidoctor scan\` with zero violations on the first try, not after a fix-up pass."; \
	  echo "---"; \
	  echo ""; \
	  .venv/bin/aidoctor skill --format generic; \
	} > skills/python-rules/SKILL.md
	@echo "Regenerated skills/python-rules/SKILL.md"

clean:
	rm -rf .pytest_cache .coverage dist build *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
