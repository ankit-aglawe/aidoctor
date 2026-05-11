---
name: react-rules
version: 1.0.0
description: |
  React / TSX / JSX coding standards for AI-generated code. Use whenever
  writing, editing, or reviewing React components. Triggers on .tsx, .jsx,
  .ts (with React), or .js (with React). Covers state and effects bugs,
  re-render performance traps, accessibility, dead code, security, and
  architectural smells. Output should pass review with zero violations on
  the first try, not after a fix-up pass.
triggers:
  - writing react
  - editing react component
  - .tsx file
  - .jsx file
  - react component
  - react hook
  - useeffect
  - usestate
benefits-from: [scan, simplify, audit]
---

# react-rules

Rules tuned for AI-generated React. The patterns LLMs reflexively produce in React are well-documented: stale closures in `useEffect`, `key={index}` on dynamic lists, direct state mutation, missing cleanup on subscriptions, `dangerouslySetInnerHTML` from user input, and entire class components when hooks would have done. This skill catches them BEFORE you emit the code.

> **Attribution.** This skill builds on the rule research from [react-doctor](https://github.com/millionco/react-doctor) by [@aidenybai](https://twitter.com/aidenybai) (MIT licensed, © millionco). Rule IDs and categorization are adapted; explanations are rewritten in the aidoctor style. See LICENSE for full attribution.

## When to use

Every React file you generate, edit, or refactor. **No exceptions for "small" demos, prototypes, or "throwaway" components.** Stale closures and missing cleanup leak through all three.

## Iron Law

```
NO REACT EMITTED WITHOUT THE 6-POINT PRE-FLIGHT PASSING
```

If any of the six checks below is unclear, resolve it **before** generating code. "I'll fix it after" is the failure mode this rule exists to prevent. **Spirit over letter** — paraphrasing the pre-flight ("I'll just glance at it") is the same violation as skipping it.

## Read this BEFORE you type a single line of React

A 30-second pre-flight that prevents most violations:

1. **Hooks first**: if you're generating a new component, use a **function component with hooks**. Do not write `class X extends React.Component`. Class components are 2018-era — every modern React codebase prefers hooks.
2. **useEffect deps**: if you're about to write `useEffect(() => { ... }, [])`, ask: does anything inside the effect close over a prop or state value? If yes, that value MUST be in the dependency array. Empty `[]` is only correct when the effect captures NOTHING from the surrounding scope.
3. **Cleanup**: if your `useEffect` subscribes to anything (event listener, websocket, interval, timeout, observer), it MUST return a cleanup function. Memory leak otherwise.
4. **Keys**: if you're rendering a list, use a **stable unique ID** as the `key` prop. Never `key={index}` — re-orders and inserts break.
5. **Immutability**: if you're updating state, return a new object/array. Never `state.foo = bar` or `state.push(x)`. The setter (`setState`, `setX`) takes the new value or a function returning the new value.
6. **Accessibility**: if you're putting `onClick` on a `<div>` or `<span>`, stop. Use a `<button>`. If you're rendering an `<img>`, give it an `alt`. If your `<input>` has no visible label, give it `aria-label`.

If all six are clear, continue. If any is unclear, resolve it before generating code.

## Anti-rationalization

These internal monologues all produce violations. Recognize and stop.

| Thought | Reality |
|---|---|
| "I'll add the cleanup later, this is just a demo" | Subscriptions without cleanup leak forever. Add the cleanup now. |
| "Empty deps array is fine, the effect doesn't really need to re-run" | If the effect closes over a prop/state, empty deps means STALE captures. Add the deps. |
| "Using `index` as key is fine, the list won't change" | Lists DO change. Even if not today, the bug ships when they do. |
| "I'll memoize this with `useMemo` to be safe" | Premature optimization. `useMemo` has overhead. Only when the computation is provably expensive. |
| "Class components still work, who cares" | Class components break hooks-based teammates, break Suspense, break concurrent rendering. Use hooks. |
| "It's just a small inline object, the re-renders don't matter" | Inline `{}` and `[]` as props cause child re-renders. Hoist them or use `useMemo`. |
| "I'll add the alt text later" | Screen reader users see your demo too. Add the alt now. |
| "Different words so the rule doesn't apply" | Spirit over letter. Paraphrasing the rule is the same violation. |

## When a rule genuinely can't be followed

There are real exceptions. The escape hatch is **narrow** and **explicit**:

- **`useEffect(() => {...}, [])` is genuinely empty-deps** because the effect truly captures nothing. Verify by reading every variable inside the effect. If any is a prop or state, the deps array is wrong.
- **`dangerouslySetInnerHTML` is necessary** because you control the source completely AND it's been sanitized via DOMPurify or equivalent. Mark the line: `{/* aidoctor: disable=react-dangerous-html reason: sanitized by DOMPurify above */}`
- **Index as key** is acceptable when the list is **truly static** and never reorders / inserts / removes. Mark the line: `{/* aidoctor: disable=react-key-prop-index reason: list is build-time constant */}`

If you reach for a disable comment more than once per file, you're wrong about the exception — rewrite instead.

## The rules

Each rule has a stable `rule_id`. Bodies show what's forbidden and what's required. **Rules are ordered by blast radius — top categories cause the worst damage if shipped.**

### Security

#### `react-dangerous-html` (error) — `dangerouslySetInnerHTML` with unsanitized content

`dangerouslySetInnerHTML={{__html: userInput}}` is a stored-XSS vector if `userInput` comes from anywhere outside your code (URL params, API responses, form input, localStorage). AI generates this pattern when asked to "render HTML from the server" without thinking about source trust.

**DON'T**
```jsx
function Comment({ body }) {
  return <div dangerouslySetInnerHTML={{ __html: body }} />;
}
```

**DO**
```jsx
import DOMPurify from "isomorphic-dompurify";

function Comment({ body }) {
  const safe = DOMPurify.sanitize(body);
  return <div dangerouslySetInnerHTML={{ __html: safe }} />;
}
```

#### `react-href-javascript` (error) — `href` containing javascript: protocol

`href={\`javascript:${expr}\`}` is a script injection if any part of `expr` is attacker-controllable. Even seemingly-safe values become unsafe when interpolated.

**DON'T**
```jsx
<a href={`javascript:${onClickCode}`}>Click</a>
```

**DO**
```jsx
<button onClick={() => handler()}>Click</button>
```

### State & Effects

#### `react-useeffect-missing-deps` (error) — `useEffect` deps array missing closed-over values

If the effect body reads a prop or state value, that value MUST appear in the deps array. Empty `[]` with closed-over references creates stale closures: the effect runs once with the initial values and never sees updates.

**DON'T**
```jsx
function Profile({ userId }) {
  useEffect(() => {
    fetch(`/api/users/${userId}`).then(...);
  }, []);  // userId is captured but not in deps — stale
}
```

**DO**
```jsx
function Profile({ userId }) {
  useEffect(() => {
    fetch(`/api/users/${userId}`).then(...);
  }, [userId]);
}
```

#### `react-useeffect-no-cleanup` (error) — Subscription without cleanup

If the effect subscribes (event listener, websocket, interval, timeout, observer, subscription), it MUST return a cleanup function. Without it, leaks accumulate every render cycle.

**DON'T**
```jsx
useEffect(() => {
  const id = setInterval(() => tick(), 1000);
}, []);
```

**DO**
```jsx
useEffect(() => {
  const id = setInterval(() => tick(), 1000);
  return () => clearInterval(id);
}, []);
```

#### `react-direct-state-mutation` (error) — Mutating state without setter

State is immutable. `items.push(x)` or `obj.foo = 'bar'` followed by `setItems(items)` does NOT trigger a re-render because React uses reference equality. AI generates this pattern when asked to "add an item to the list".

**DON'T**
```jsx
function addItem(item) {
  items.push(item);
  setItems(items);
}
```

**DO**
```jsx
function addItem(item) {
  setItems([...items, item]);
}
```

#### `react-derived-state-useeffect` (warning) — Storing derived state via `useEffect`

If the value can be computed from existing props/state, compute it inline (or with `useMemo`). Don't store it in state and use `useEffect` to keep it in sync — that creates two sources of truth and an extra render cycle.

**DON'T**
```jsx
const [fullName, setFullName] = useState("");
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);
```

**DO**
```jsx
const fullName = `${firstName} ${lastName}`;
// or for expensive computations:
const fullName = useMemo(() => `${firstName} ${lastName}`, [firstName, lastName]);
```

#### `react-stale-closure` (warning) — Event handler captures stale state

If an event handler closes over state without dependency tracking (e.g., inside a `useEffect` with stale deps), it operates on the old value. Use the functional setter form to get current state, or include the value in deps.

**DON'T**
```jsx
function Counter() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setCount(count + 1), 1000);  // count is stale after first run
    return () => clearInterval(id);
  }, []);
}
```

**DO**
```jsx
function Counter() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setCount(c => c + 1), 1000);  // functional setter
    return () => clearInterval(id);
  }, []);
}
```

### Performance

#### `react-key-prop-index` (warning) — Using array index as `key`

`key={index}` breaks React's reconciliation when items insert, remove, or reorder. React reuses DOM nodes based on the key — wrong keys cause stale state on the wrong elements.

**DON'T**
```jsx
{todos.map((todo, i) => <TodoItem key={i} todo={todo} />)}
```

**DO**
```jsx
{todos.map(todo => <TodoItem key={todo.id} todo={todo} />)}
```

#### `react-inline-object-prop` (warning) — Passing inline `{}` or `[]` as prop

Inline objects create new references every render, which propagates re-renders to children even when the actual data hasn't changed. Hoist or memoize.

**DON'T**
```jsx
<Chart options={{ animation: false, theme: 'dark' }} />
```

**DO**
```jsx
const CHART_OPTIONS = { animation: false, theme: 'dark' };

function Parent() {
  return <Chart options={CHART_OPTIONS} />;
}
```

#### `react-overuse-memo` (warning) — `useMemo`/`useCallback` on cheap computations

`useMemo` and `useCallback` have overhead. Using them on cheap operations is premature optimization that often makes things slower. Only use when the wrapped computation is genuinely expensive (5ms+) or when reference identity is required for a deep-comparison child.

**DON'T**
```jsx
const sum = useMemo(() => a + b, [a, b]);  // cheap, no benefit
```

**DO**
```jsx
const sum = a + b;
// or for real cost:
const filtered = useMemo(
  () => hugeList.filter(complexPredicate),
  [hugeList]
);
```

### Architecture

#### `react-class-component` (error) — Generating class component instead of hooks

Class components are 2018-era. Hooks (introduced 2019) are the modern pattern. New code should be function-based unless integrating with a legacy codebase that requires classes.

**DON'T**
```jsx
class Counter extends React.Component {
  constructor(props) {
    super(props);
    this.state = { count: 0 };
  }
  render() { return <div>{this.state.count}</div>; }
}
```

**DO**
```jsx
function Counter() {
  const [count, setCount] = useState(0);
  return <div>{count}</div>;
}
```

#### `react-god-component` (warning) — Component longer than 200 lines

Components past 200 lines have too many responsibilities. Split into smaller components. AI generates god components when asked for "the whole feature" — push back on the prompt and break it into parts.

#### `react-mixed-concerns` (warning) — Data fetching + state management + rendering in one component

When one component does data fetching, complex state derivation, AND rendering, it's hard to test and reuse. Extract data fetching into a custom hook. Extract presentational pieces. Keep components focused.

### Accessibility

#### `react-missing-alt` (warning) — `<img>` without `alt` prop

Screen readers can't describe images without alt text. Decorative images need `alt=""` explicitly (signals "ignore me" to screen readers); content images need descriptive alt text.

**DON'T**
```jsx
<img src="/avatar.jpg" />
```

**DO**
```jsx
<img src="/avatar.jpg" alt={`${user.name}'s avatar`} />
```

#### `react-click-non-button` (warning) — `onClick` on `<div>` or `<span>`

Non-interactive elements don't trigger from keyboard, don't appear in accessibility tree as buttons, and aren't announced as actionable by screen readers. Use a `<button>` styled as needed.

**DON'T**
```jsx
<div onClick={handleClick}>Click me</div>
```

**DO**
```jsx
<button type="button" onClick={handleClick}>Click me</button>
```

#### `react-input-no-label` (warning) — `<input>` without label or `aria-label`

Inputs need accessible names. Either an associated `<label>` or `aria-label` attribute.

**DON'T**
```jsx
<input type="email" placeholder="Email" />
```

**DO**
```jsx
<label>
  Email
  <input type="email" />
</label>
// or:
<input type="email" aria-label="Email address" />
```

### Dead Code

#### `react-unused-prop` (warning) — Prop destructured but never used

If a prop appears in the destructuring but never in the function body, either remove it or use it. Often it's a leftover from refactoring.

#### `react-commented-jsx` (warning) — Commented-out JSX shipped to production

Block-commented JSX clutters files and signals indecision. Delete the dead code. Git keeps history.

**DON'T**
```jsx
return (
  <div>
    <h1>Welcome</h1>
    {/* <OldHero /> */}
    <NewHero />
  </div>
);
```

**DO**
```jsx
return (
  <div>
    <h1>Welcome</h1>
    <NewHero />
  </div>
);
```

## Common AI-slop combinations

Slop travels in packs. If you spot one, scan for the others — patching individual lines won't fix the underlying pattern.

```jsx
// "useEffect + missing cleanup + missing deps + index key" — four bugs, one component
function NotificationsList({ userId }) {
  const [items, setItems] = useState([]);

  useEffect(() => {                                // 
    const id = setInterval(async () => {           //  react-useeffect-no-cleanup (no clearInterval)
      const r = await fetch(`/api/notes/${userId}`); //  react-useeffect-missing-deps (userId not in deps)
      setItems(await r.json());
    }, 5000);
  }, []);                                          //

  return items.map((item, i) =>                    //
    <Note key={i} item={item} />                   //  react-key-prop-index
  );
}
```

Four rules tripped. Rewrite as one block.

## Pre-emit verification checklist

After drafting, before emitting. Every box must check. If any fails, **rewrite — do not annotate-and-ship.**

- [ ] Component is a function (not a class) unless the codebase requires classes
- [ ] Every `useEffect` that closes over props or state has those values in the deps array
- [ ] Every `useEffect` that subscribes returns a cleanup function
- [ ] State updates use the setter with a new value (or functional setter) — no direct mutation
- [ ] List rendering uses a stable unique ID as `key`, never `index`
- [ ] No `dangerouslySetInnerHTML` with unsanitized content
- [ ] No `href` containing `javascript:` protocol
- [ ] `<img>` has `alt` (descriptive or `""` for decorative)
- [ ] `onClick` on `<button>`, not `<div>` / `<span>`
- [ ] Inputs have a label or `aria-label`
- [ ] No commented-out JSX
- [ ] No unused destructured props
- [ ] No `useMemo`/`useCallback` on cheap computations

Any unchecked? Fix, then respond.

## Related skills

- `/aidoctor:scan` — language-agnostic CLI lint check (Python rules deepest today; React rules in v1.0+)
- `/aidoctor:simplify` — three-angle review of changed code (works on React diffs)
- `/aidoctor:audit` — six-dimensional whole-project review (works on React projects)
- `python-rules` — sibling rule pack for Python
- https://github.com/millionco/react-doctor — original React-AI-slop research this skill builds on

## Cross-reference to react-doctor source

This skill's 19 rules are a starter subset. react-doctor's full catalog has 140+ rules across the same categories. Our IDs are semantically equivalent but use different naming for brevity. Mapping:

| Our rule_id | react-doctor's rule_id | Notes |
|---|---|---|
| `react-key-prop-index` | `react-no-array-index-as-key` | identical semantics |
| `react-useeffect-no-cleanup` | `react-effect-needs-cleanup` | identical semantics |
| `react-useeffect-missing-deps` | `react-rerender-dependencies` | identical semantics (also covered by react-hooks/exhaustive-deps) |
| `react-direct-state-mutation` | `react-no-direct-state-mutation` | identical semantics |
| `react-inline-object-prop` | `react-no-inline-prop-on-memo-component` | ours broader; theirs scoped to memo'd children |
| `react-derived-state-useeffect` | `react-no-derived-state-effect` | identical semantics |
| `react-stale-closure` | (via `react-rerender-dependencies`) | overlapping concern |
| `react-overuse-memo` | `react-no-usememo-simple-expression` | identical semantics |
| `react-class-component` | `react-no-legacy-class-lifecycles` | ours broader (refuses ALL class components); theirs scoped to legacy lifecycle methods |
| `react-god-component` | `react-no-giant-component` | identical (we both threshold lines) |
| `react-dangerous-html` | `react/no-danger` (orchestrated) | identical semantics |
| `react-href-javascript` | (curated) | not in react-doctor — added for completeness |
| `react-missing-alt` | `jsx-a11y/alt-text` (orchestrated) | identical semantics |
| `react-click-non-button` | `jsx-a11y/no-static-element-interactions` (orchestrated) | identical semantics |
| `react-input-no-label` | `jsx-a11y/label-has-associated-control` (orchestrated) | identical semantics |
| `react-unused-prop` | (curated) | dead-code patterns; react-doctor uses knip orchestration for this |
| `react-commented-jsx` | (curated) | dead-code patterns; react-doctor uses knip orchestration for this |
| `react-mixed-concerns` | (curated) | architecture smell; not specifically in react-doctor |

**Roadmap expansion (v1.1+):** add the remaining react-doctor categories — bundle size (`react-no-barrel-import`, `react-no-moment`, `react-prefer-dynamic-import`), AI-slop UI tells (`react-no-pure-black-background`, `react-no-gradient-text`, `react-design-no-em-dash-in-jsx-text`), more performance (`react-rendering-hoist-jsx`, `react-no-layout-property-animation`), and the React Compiler rules (`react-hooks-js/*`). Each new rule goes through the same iter-N A/B testing methodology.

**Attribution.** This skill's rule SEMANTICS are derived from [react-doctor](https://github.com/millionco/react-doctor) (MIT, © 2026 Aiden Bai / Million Software, Inc.). Rule wording, examples, and the SKILL.md structure are original to aidoctor. Full MIT text in the aidoctor repo's `LICENSE` + `THIRD_PARTY_LICENSES`.
