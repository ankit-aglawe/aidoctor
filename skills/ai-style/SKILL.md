---
name: ai-style
version: 0.1.0
description: Universal AI-fingerprint patterns to avoid in any source code (Python, JavaScript, TypeScript, Rust, Go, React, Java, Ruby, anything). Auto-load whenever the user is writing code in any language. The patterns are language-agnostic — emojis, emphasis labels, section dividers, self-praise vocabulary, hedge leakage, inflated prints, useless docstrings, generic variable names, obvious type annotations, explanation comments. These are visible AI tells; humans rarely emit them.
triggers:
  - writing any code
  - generating code
  - refactoring code
  - reviewing AI-generated code
benefits-from: [deai, scan]
---

# ai-style — universal AI fingerprints to avoid

These are the *visible* AI tells, language-agnostic. They make code look AI-generated even when the logic is correct. Auto-loads alongside any language-specific rule pack (`python-rules`, `rust-rules`, `go-rules`, `js-rules`, `react-rules`).

## Why this skill exists

`/aidoctor:deai` removes these fingerprints from your output. This skill prevents you from emitting them in the first place. Same patterns, opposite end of the loop.

The 10 patterns below are universal — they apply to every programming language. The DETECTION side (deterministic scanner) currently only walks Python source at v2.0; tree-sitter scanning for Rust / Go / JS / TS / React ships in v2.1. But the PREVENTION side (this skill) works everywhere right now: the rules below are what the agent should avoid emitting regardless of target language.

## The 10 universal AI fingerprints

### 1. Emojis in source code

Comments, identifiers, operator positions. Not in user-facing string literals (those are intentional UX).

| Language | DON'T | DO |
|---|---|---|
| Python | `# ✅ Done` | `# checked` |
| JS/TS | `// ✨ Setup complete` | `// init done` |
| Rust | `// 🚀 Fast path` | `// fast path` |
| Go | `// 🎯 TODO` | `// TODO` |

Emojis in `print("✨ done!")`, `console.log("🎉 success")`, `println!("🚀 ...")` are inflated prints (see #5), not user-facing UX.

### 2. Emphasis labels in comments

`NOTE:`, `IMPORTANT:`, `CAREFUL:`, `CRITICAL:`, `TIP:`, `HACK:`, `WARNING:`, `REMEMBER:` prefixes are decorative. The next line either earns its own warning or doesn't need one. Same for `// NOTE:` in JS/TS/Rust/Go.

### 3. ASCII section dividers

Banners like `# ====== SECTION 1 ======` or `// ---------- helpers ----------` signal that the file is too long. Split into functions/modules instead of dividing visually.

### 4. Self-praise vocabulary in comments

Don't praise your own code in a comment. The code either is or isn't elegant; the comment doesn't change that. Vocabulary to avoid: `pythonic`, `idiomatic`, `elegant`, `clean code`, `best practice`, `robust`, `comprehensive`, `simple and effective`.

### 5. Inflated print/log statements

Don't emit:

| Language | DON'T | DO |
|---|---|---|
| Python | `print("✅ Successfully processed all items!")` | `logger.info("processed %d items", n)` |
| JS/TS | `console.log("✨ Done!")` | `console.log(\`processed ${n} items\`)` |
| Rust | `println!("🎉 All checks passed!")` | `println!("checks passed");` |
| Go | `fmt.Println("✅ Build complete!")` | `fmt.Println("build complete")` |

Pattern: any output statement with celebratory emoji + "Success/Done/Complete" vocabulary.

### 6. Useless docstrings / doc comments

A docstring (or `/** */` / `///` / `//` for godoc) that just restates the function signature is noise. Either omit it or write what the signature doesn't say (preconditions, side effects, error contract).

### 7. Generic variable names in long functions

In any function body longer than ~8 statements, avoid `data`, `result`, `value`, `item`, `output`, `tmp`, `temp`, `foo`. Pick names that say what the variable IS in this context.

### 8. Obvious type annotations on literals

Don't emit annotations that just repeat what the RHS already tells the type checker. `count: int = 5`, `name: str = "alice"`, `const count: number = 5`. Drop the annotation when inference works.

### 9. Explanation comments

Comments that just restate the next line in English. Delete the comment; the code says it. Only comment WHY, not WHAT.

### 10. Hedge leakage from AI prompts

Never emit `# As an AI, I...`, `# I cannot...`, `# Note: this implementation assumes...`. These are AI-prompt artifacts that escaped into shipped code. If the assumption is real, encode it as an assertion, not a comment.

## v2.0 detection coverage (by-rule)

The deterministic Python scanner catches 5 of the 10 fingerprints today via `ai_style.jsonl`:

| # | Pattern | Detection at v2.0 | Detection in v2.1 |
|---|---|---|---|
| 1 | Emojis in code | Python (✓) | + Rust / Go / JS / TS via tree-sitter |
| 2 | Emphasis labels | Python (✓) | + all 5 langs (per-lang comment syntax) |
| 3 | Section dividers | Python (✓) | + all 5 langs |
| 4 | Self-praise vocab | Python (✓) | + all 5 langs |
| 5 | Inflated prints | prevention only | detection planned |
| 6 | Useless docstrings | prevention only | detection planned (lexical overlap check) |
| 7 | Generic vars in long fn | prevention only | detection planned (function-length aware) |
| 8 | Obvious type annotations | prevention only | detection planned (literal-vs-annotation match) |
| 9 | Explanation comments | prevention only | detection planned (heuristic overlap) |
| 10 | Hedge leakage | Python (✓) | + all 5 langs |

**The rules in this skill are universal and language-agnostic.** Apply them whether you're emitting Python, TypeScript, Rust, Go, React, Java, Ruby, or anything else. Detection lags by language; prevention doesn't.

## Cross-reference

- `/aidoctor:deai` — removes these fingerprints from existing code (post-emit).
- `/aidoctor:scan` — runs the deterministic detector and reports.
- `python-rules` / `rust-rules` / `go-rules` / `js-rules` / `react-rules` — language-specific correctness rules, complementary to this skill.
