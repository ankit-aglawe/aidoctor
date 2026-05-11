---
name: js-rules
version: 1.0.0
description: |
  JavaScript / TypeScript coding standards for AI-generated code (excluding
  React — that's react-rules). Use whenever writing, editing, or reviewing
  plain JS or TS — Node services, CLI tools, libraries, utilities. Triggers
  on .js, .ts, .mjs, .cjs files. Covers TypeScript escape hatches, async/error
  handling traps, and JS idioms that AI agents reflexively get wrong.
triggers:
  - writing javascript
  - writing typescript
  - editing js
  - editing ts
  - .ts file
  - .mjs file
  - node service
  - typescript module
benefits-from: [scan, simplify, audit, react-rules]
---

# js-rules

Rules tuned for AI-generated JavaScript and TypeScript. AI agents reflexively reach for `any`, `as` casts that silence type errors, `var`, `==`, empty `catch` blocks, and floating promises. This skill catches them BEFORE you emit the code.

> **Scope.** This skill covers plain JS / TS. React-specific patterns (hooks, JSX, components) live in `react-rules`. If you're writing a `.tsx` or `.jsx` file, both skills auto-apply.

## When to use

Every JS or TS file you generate, edit, or refactor — Node services, CLI tools, libraries, utility modules. **No exceptions for "small" scripts or "throwaway" code.** Floating promises and `any` everywhere leak through all three.

## Iron Law

```
NO JS/TS EMITTED WITHOUT THE 5-POINT PRE-FLIGHT PASSING
```

If any of the five checks below is unclear, resolve it **before** generating code. "I'll fix it after" is the failure mode this rule exists to prevent. **Spirit over letter** — paraphrasing the pre-flight is the same violation as skipping it.

## Read this BEFORE you type a single line of JS/TS

A 30-second pre-flight that prevents most violations:

1. **Types**: if you're about to type `any`, stop. Do you mean `unknown` (forces narrowing)? Do you know the actual type from the call sites? Do you mean a generic `T`? `any` disables type-checking — only acceptable when interfacing with truly untyped libraries.
2. **Casts**: if you're about to write `x as T` or `@ts-ignore`, stop. `as` is a runtime no-op that lies to the compiler. Use a type guard (`typeof`, `instanceof`, `in`, user-defined predicate) or a schema validator (zod, valibot). `@ts-expect-error` with a reason is the legitimate escape hatch; bare `@ts-ignore` rots.
3. **Async**: if you're about to call a Promise-returning function, `await` it (or explicitly `void` it with a `.catch`). Floating promises swallow rejections and become unhandled-rejection events that nobody reads.
4. **Errors**: if you're about to write `try { ... } catch (e) {}` or `.catch(() => {})`, stop. Empty catch blocks hide real bugs. Either handle the specific failure, log + rethrow, or remove the try entirely.
5. **Idioms**: never `var` (use `const` or `let`). Never `==` (use `===`). Never `throw "string"` (throw an `Error` instance).

If all five are clear, continue. If any is unclear, resolve it before generating code.

## Anti-rationalization

These internal monologues all produce violations. Recognize and stop.

| Thought | Reality |
|---|---|
| "I'll just use `any` here — I'll fix the type later" | You won't. Use `unknown` and narrow with a guard, or read the real type from the call site. |
| "The `as` cast silences the error, that's good enough" | `as` is a lie. If the runtime shape doesn't match, you get a silent corruption. Use a guard. |
| "It's just a quick script, no need for await" | Floating promises crash differently in Node 15+ (process exits) vs browsers (unhandled rejection event). Add `await` or `void promise.catch(...)`. |
| "Empty catch is fine, this can't really fail" | Then remove the `try`. If it can fail, handle the failure. Empty catches hide programmer bugs. |
| "I'll add a `.catch` later, the happy path works" | The catch is the protocol. Without it, every rejection is an unhandled-rejection event. |
| "`var` works the same as `let`, who cares" | `var` has function scope and hoisting. Real bugs come from accidental reassignment + scoping. Use `const` by default. |
| "`==` is fine for null checks" | `null == undefined` is the one place it works. Everywhere else, `===`. |
| "Different words so the rule doesn't apply" | Spirit over letter. Paraphrasing the rule is the same violation. |

## When a rule genuinely can't be followed

There are real exceptions. The escape hatch is **narrow** and **explicit**:

- **`any` is correct** when interfacing with a runtime-typed library that has no type definitions. Use the line-level disable: `// aidoctor: disable=js-any-everywhere reason: untyped lib X v1.2`
- **`@ts-expect-error` is correct** when working around a known TypeScript bug. Include a reason and link to the issue: `// @ts-expect-error TS 5.9 bug — microsoft/TypeScript#54321`
- **`void promise` (fire-and-forget)** is correct for logging, audit trails, telemetry — where the call should not block the response path. Always pair with `.catch(err => logger.error(...))`.

If you're reaching for a disable comment more than once per file, you're wrong about the exception — rewrite instead.

## The rules

Each rule has a stable `rule_id`. Bodies show what's forbidden and what's required.

### Types (TypeScript)

#### `js-any-everywhere` (error) — `any` on a public boundary

`any` on a public function parameter, return type, or exported variable disables type-checking at the boundary. Every caller silently loses type safety. AI reaches for `any` when uncertain about the real type — replace with the specific type, a union, a generic, or `unknown` (which forces explicit narrowing).

**DON'T**
```ts
function process(data: any): any {
  return data.value;
}
```

**DO**
```ts
function process(data: { value: number }): number {
  return data.value;
}
// or, if truly opaque:
function process(data: unknown): number {
  if (typeof data === "object" && data && "value" in data) return Number(data.value);
  throw new TypeError("bad payload");
}
```

#### `js-as-cast-hiding-error` (error) — `x as T` to silence type errors

`x as T` is a lie to the compiler. If the runtime shape doesn't match, you get silent corruption.

**DON'T**
```ts
const user = JSON.parse(raw) as User;
```

**DO**
```ts
const user = UserSchema.parse(JSON.parse(raw)); // zod / valibot
```

#### `js-as-any-double-cast` (error) — `x as any as T`

There is no scenario where `as any as T` is correct. AI emits it when `as T` fails because source and target are unrelated. The fix is a real type guard or schema validation.

**DON'T**
```ts
const config = raw as any as AppConfig;
```

**DO**
```ts
const config = parseAppConfig(raw);
```

#### `js-ts-ignore-without-reason` (error) — bare `@ts-ignore`

Use `@ts-expect-error` (which fails when the error goes away) AND include a one-line reason. Bare `@ts-ignore` rots.

**DON'T**
```ts
// @ts-ignore
foo.bar.baz();
```

**DO**
```ts
// @ts-expect-error upstream types missing baz — tracking in GH-491
foo.bar.baz();
```

#### `js-non-null-assertion` (warning) — `x!` postfix without guard

The `!` operator asserts non-null with no runtime check. Wrong assertion = runtime crash. AI uses `arr.find(...)!` to silence strictNullChecks.

**DON'T**
```ts
const user = users.find(u => u.id === id)!;
return user.email;
```

**DO**
```ts
const user = users.find(u => u.id === id);
if (!user) throw new Error(`no user ${id}`);
return user.email;
```

#### `js-untyped-function-param` (warning) — function params without type annotation in TS

In `.ts` files, parameters must be annotated. Implicit `any` defeats the point.

**DON'T**
```ts
function total(items) { return items.reduce((a, b) => a + b, 0); }
```

**DO**
```ts
function total(items: number[]): number { return items.reduce((a, b) => a + b, 0); }
```

#### `js-enum-instead-of-union` (warning) — TS `enum`

`enum` produces runtime objects, breaks tree-shaking, confuses const-vs-numeric semantics. Prefer string literal unions or `as const` objects.

**DON'T**
```ts
enum Status { Active, Pending, Closed }
```

**DO**
```ts
type Status = "active" | "pending" | "closed";
```

### Async

#### `js-floating-promise` (error) — Promise-returning call without `await`/`void`/`.catch`

A floating promise silently swallows rejections. AI forgets `await` when the surrounding function is async.

**DON'T**
```ts
async function handle(req: Request) {
  saveAudit(req); // floating — rejection becomes unhandled
  return ok();
}
```

**DO**
```ts
async function handle(req: Request) {
  await saveAudit(req);
  return ok();
}
// fire-and-forget intentionally:
void saveAudit(req).catch(err => logger.error(err));
```

#### `js-promise-chain-instead-of-await` (warning) — `.then().catch()` in async function

Inside `async`, use `await` + `try/catch`. Mixing styles is harder to read and harder to debug.

**DON'T**
```ts
async function load(id: string) {
  return fetch(`/u/${id}`).then(r => r.json()).catch(e => null);
}
```

**DO**
```ts
async function load(id: string) {
  try {
    const r = await fetch(`/u/${id}`);
    return await r.json();
  } catch (e) {
    logger.warn("load failed", e);
    return null;
  }
}
```

#### `js-await-in-loop` (warning) — sequential `await` in a `for` loop

Serializes I/O that should run in parallel. Use `Promise.all(items.map(...))` when operations are independent.

**DON'T**
```ts
const results = [];
for (const id of ids) {
  results.push(await fetch(`/u/${id}`));
}
```

**DO**
```ts
const results = await Promise.all(ids.map(id => fetch(`/u/${id}`)));
```

#### `js-unhandled-rejection-then` (warning) — `.then(onSuccess)` without `.catch`

Every top-level promise chain needs error handling. Inside `async`, prefer `await` + `try/catch`.

**DON'T**
```ts
fetchUser(id).then(u => render(u));
```

**DO**
```ts
fetchUser(id).then(u => render(u)).catch(e => showError(e));
```

### Error Handling

#### `js-empty-catch` (error) — empty `catch` block

Silently swallows every error including programmer bugs. AI generates empty catches to "be safe" — that's the opposite of safe.

**DON'T**
```ts
try {
  await client.charge(amount);
} catch (e) {}
```

**DO**
```ts
try {
  await client.charge(amount);
} catch (e) {
  logger.error("charge failed", { amount, e });
  throw e;
}
```

#### `js-catch-any-implicit` (warning) — `e.message` on `unknown` catch variable

In strict mode, `catch (e)` is typed `unknown`. AI assumes `e.message` exists. Narrow before use.

**DON'T**
```ts
try { ... } catch (e) { logger.error(e.message); }
```

**DO**
```ts
try { ... } catch (e) {
  logger.error(e instanceof Error ? e.message : String(e));
}
```

#### `js-throw-non-error` (error) — `throw "string"` or `throw {object}`

Loses stack traces, breaks `instanceof Error` checks. Always throw an `Error` (or subclass).

**DON'T**
```ts
if (!user) throw "user not found";
```

**DO**
```ts
class NotFoundError extends Error { name = "NotFoundError"; }
if (!user) throw new NotFoundError(`user ${id} not found`);
```

### Idioms

#### `js-var-instead-of-const` (error) — `var` keyword

`var` has function scope and hoisting quirks. No reason to use it in code written after 2015.

**DON'T**
```js
var name = "ankit";
```

**DO**
```js
const name = "ankit";
```

#### `js-loose-equality` (warning) — `==` or `!=`

Type coercion has surprising rules. Always `===` and `!==`.

**DON'T**
```js
if (count == "0") { ... }
```

**DO**
```js
if (count === 0) { ... }
```

#### `js-callback-hell` (warning) — nested callbacks 3+ deep

Convert to async/await. Modern Node has promise versions of every stdlib API.

**DON'T**
```js
fs.readFile(a, (err, ra) => {
  fs.readFile(b, (err, rb) => {
    fs.writeFile(c, ra + rb, err => done(err));
  });
});
```

**DO**
```js
import { readFile, writeFile } from "node:fs/promises";
const [ra, rb] = await Promise.all([readFile(a), readFile(b)]);
await writeFile(c, ra + rb);
```

#### `js-console-log-shipped` (warning) — `console.log` in production code

Use a real logger (pino, winston, debug). Remove `console.log` before commit.

**DON'T**
```ts
async function checkout(cart: Cart) {
  console.log("cart", cart);
  return await client.charge(cart);
}
```

**DO**
```ts
import logger from "./logger";
async function checkout(cart: Cart) {
  logger.debug({ cartId: cart.id }, "checkout");
  return await client.charge(cart);
}
```

### Modules

#### `js-unused-import` (warning) — imported but never used

Dead code. Remove. Type-only imports should use `import type`.

#### `js-default-export-mixed` (warning) — mixing default + named exports

Creates two import styles for one file. Pick named exports as default — they tree-shake better and refactor better.

## Common AI-slop combinations

Slop travels in packs.

```ts
// "any everywhere + floating promise + empty catch" — three bugs, one function
async function handleWebhook(payload: any): any {
  try {
    saveAudit(payload);                      // js-floating-promise (no await)
    const result = await process(payload);
    return result as ProcessedPayload;       // js-as-cast-hiding-error
  } catch (e) {}                             // js-empty-catch
}
```

Four rules tripped. Rewrite with typed payload, awaited audit, schema-validated result, logged + rethrown error.

## Pre-emit verification checklist

After drafting, before emitting. Every box must check.

- [ ] No `any` on a public boundary; `unknown` + narrowing where the type is opaque
- [ ] No `as T` casts that silence errors; type guards or schema validators instead
- [ ] No bare `@ts-ignore`; only `@ts-expect-error` with a reason
- [ ] Non-null assertion (`!`) only after a guard the compiler can't see
- [ ] All function params annotated in `.ts` files
- [ ] No `enum` (use string literal unions or `as const`)
- [ ] Every Promise-returning call is `await`ed, `void`ed with `.catch`, or `return`ed
- [ ] Inside `async`, prefer `await` + `try/catch` over `.then().catch()`
- [ ] Parallel-eligible awaits use `Promise.all`, not sequential `for await`
- [ ] Every top-level promise chain has a `.catch`
- [ ] No empty `catch` blocks
- [ ] `catch (e)` narrows `e` (instanceof Error or String(e))
- [ ] Only `Error` instances are thrown (never strings or plain objects)
- [ ] `const` or `let`, never `var`
- [ ] `===` and `!==`, never `==` or `!=`
- [ ] No callback chains 3+ deep
- [ ] No `console.log` in shipped code
- [ ] No unused imports
- [ ] Consistent export style (named, with documented `export default` exceptions)

Any unchecked? Fix, then respond.

## Related skills

- `/aidoctor:scan` — language-agnostic lint check
- `/aidoctor:simplify` — three-angle review of changed code
- `/aidoctor:audit` — six-dimensional whole-project review
- `python-rules` — sibling rule pack for Python
- `react-rules` — sibling rule pack for React / JSX / TSX
