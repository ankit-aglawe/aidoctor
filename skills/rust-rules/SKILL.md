---
name: rust-rules
version: 1.0.0
description: |
  Rust coding standards for AI-generated code. Use whenever writing, editing,
  or reviewing Rust — services, CLIs, libraries. Triggers on .rs files.
  Covers panic discipline, async/sync boundaries, unsafe etiquette,
  borrow-checker fights, and Rust idioms AI agents reflexively get wrong
  (.unwrap() in prod, unnecessary .clone(), transmute misuse, blocking in async).
triggers:
  - writing rust
  - editing rust
  - .rs file
  - rust service
  - rust library
  - cargo project
benefits-from: [scan, simplify, audit]
---

# rust-rules

Rules tuned for AI-generated Rust. AI agents reflexively reach for `.unwrap()`, `.clone()`, `unsafe { transmute(...) }`, `panic!` to satisfy the type checker, and blocking `std::*` calls inside async functions. This skill catches them BEFORE you emit the code.

## When to use

Every Rust file you generate, edit, or refactor — service code, library code, CLI tools, build scripts. **No exceptions for "simple" examples or "throwaway" prototypes.** `.unwrap()` and blocking-in-async leak through all three.

## Iron Law

```
NO RUST EMITTED WITHOUT THE 5-POINT PRE-FLIGHT PASSING
```

If any of the five checks below is unclear, resolve it **before** generating code. "I'll fix it after" is the failure mode this rule exists to prevent. **Spirit over letter** — paraphrasing the pre-flight is the same violation.

## Read this BEFORE you type a single line of Rust

A 30-second pre-flight that prevents most violations:

1. **Panics**: if you're about to write `.unwrap()`, `.expect()`, `panic!`, `unreachable!`, `todo!`, or `unimplemented!`, ask: can external input reach this? If yes, you ship a panic. Propagate with `?`, return a `Result`, or match.
2. **Unsafe**: if you're about to write `unsafe { ... }`, the line above MUST be `// SAFETY: <invariant explanation>`. If you can't write the invariant, you don't know the code is sound.
3. **Async/sync**: if you're inside `async fn`, never call `std::thread::sleep`, `std::fs::*`, blocking `reqwest`, or `Runtime::block_on`. Use `tokio::fs`, `tokio::time::sleep`, `reqwest` async, or `tokio::task::spawn_blocking`.
4. **Clones**: if you're about to write `.clone()`, ask: would a borrow (`&T`) work? In most cases, yes. `.clone()` is the AI-Rust tell.
5. **`as` casts**: between integer types, `as` silently truncates. Use `try_into()` or `u32::try_from(x)?` to surface overflow.

If all five are clear, continue. If any is unclear, resolve it before generating code.

## Anti-rationalization

| Thought | Reality |
|---|---|
| "I'll just `.unwrap()` here, it can't fail" | Every prod outage starts with "it can't fail." Use `?` and return `Result`. |
| "The borrow checker is mad, I'll `.clone()`" | That's the AI-Rust tell. Try `&T` or restructure ownership. |
| "I need `unsafe` to make this compile" | Then you don't understand the invariants. Stop. Read the type errors. |
| "`as` cast is fine for this size" | "This size" depends on runtime input. Use `try_from`. |
| "I'll `.lock().unwrap()` and worry about poisoning later" | Poisoning cascades. `.unwrap_or_else(\|e\| e.into_inner())` or use `parking_lot`. |
| "`Result<T, String>` is good enough for now" | Stringly-typed errors throw away every bit of structure. Use `thiserror` or an enum. |
| "Different words so the rule doesn't apply" | Spirit over letter. Paraphrasing is the same violation. |

## When a rule genuinely can't be followed

- **`.unwrap()` in `main` / build scripts / tests** is acceptable — those are environments where panics ARE the error reporting mechanism.
- **`unsafe` with documented `// SAFETY:`** is acceptable. Document every invariant the compiler can't check.
- **`as` between integer types** is acceptable when one side is a constant the compiler can verify fits.
- **`.clone()` on `Arc<T>`** is fine (it's a refcount bump, not a deep copy) — but add a one-line comment so future readers know.

If you're reaching for a disable comment more than once per file, rewrite instead.

## The rules

### Error Handling

#### `rust-unwrap-in-prod` (error) — `.unwrap()` / `.expect()` on Result or Option in non-test code

Every `.unwrap()` is a production panic. Propagate with `?`, return a typed error, or branch with `match` / `if let`.

**DON'T**
```rust
fn load_config() -> Config {
    let raw = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&raw).unwrap()
}
```

**DO**
```rust
fn load_config() -> Result<Config, ConfigError> {
    let raw = std::fs::read_to_string("config.toml")?;
    Ok(toml::from_str(&raw)?)
}
```

#### `rust-panic-on-input` (error) — `panic!`, `unreachable!`, `todo!`, `unimplemented!` reachable from external input

If user input can reach `unreachable!()`, your service crashes on bad input. Return `Result` instead.

**DON'T**
```rust
fn parse_role(s: &str) -> Role {
    match s {
        "admin" => Role::Admin,
        "user"  => Role::User,
        _ => unreachable!("unknown role"),  // attacker sets ?role=lol
    }
}
```

**DO**
```rust
fn parse_role(s: &str) -> Result<Role, ParseRoleError> {
    match s {
        "admin" => Ok(Role::Admin),
        "user"  => Ok(Role::User),
        other   => Err(ParseRoleError::Unknown(other.into())),
    }
}
```

#### `rust-index-slice` (warning) — Indexing `v[i]` instead of `v.get(i)` when bounds aren't guaranteed

`vec[i]` panics on out-of-bounds. Use `v.get(i)` (returns `Option`) or iterate.

**DON'T**
```rust
let lookup = parts[user_supplied_index];
```

**DO**
```rust
let lookup = parts.get(user_supplied_index).ok_or(Error::OutOfRange)?;
```

#### `rust-option-result-bool-trap` (warning) — `if x.is_some()` then `x.unwrap()`

Check-then-unwrap separates the assertion from the use. Use `if let`, `?`, `.map()`, or `unwrap_or`.

**DON'T**
```rust
if maybe_user.is_some() {
    let u = maybe_user.unwrap();
    process(u);
}
```

**DO**
```rust
if let Some(u) = maybe_user {
    process(u);
}
```

#### `rust-mutex-poison-ignored` (warning) — `.lock().unwrap()` on `Mutex` without poisoning consideration

`Mutex::lock()` returns `Result<Guard, PoisonError>`. `.unwrap()` cascades panics across every thread.

**DON'T**
```rust
let data = shared.lock().unwrap();
```

**DO**
```rust
let data = shared.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
// or use parking_lot::Mutex which doesn't poison
```

#### `rust-stringly-typed-error` (warning) — Library returns `Result<T, String>` or `Result<T, Box<dyn Error>>`

Stringly-typed errors throw away structure. Callers can't match on error kinds.

**DON'T**
```rust
pub fn parse_port(s: &str) -> Result<u16, String> {
    s.parse().map_err(|e| format!("bad port: {e}"))
}
```

**DO**
```rust
#[derive(thiserror::Error, Debug)]
pub enum PortError {
    #[error("invalid port: {0}")]
    Invalid(#[from] std::num::ParseIntError),
}
pub fn parse_port(s: &str) -> Result<u16, PortError> {
    Ok(s.parse()?)
}
```

### Memory & Unsafe

#### `rust-unsafe-without-safety-comment` (error) — `unsafe` block without `// SAFETY:` comment

Every `unsafe` block needs a `// SAFETY:` line explaining why the invariants hold. No comment = the author didn't know the invariants or invented them.

**DON'T**
```rust
let s = unsafe { std::str::from_utf8_unchecked(&bytes) };
```

**DO**
```rust
// SAFETY: `bytes` originated from `String::into_bytes()`, so valid UTF-8.
let s = unsafe { std::str::from_utf8_unchecked(&bytes) };
```

#### `rust-transmute-misuse` (error) — `std::mem::transmute` where a safe cast works

`transmute` reinterprets bytes with zero checks. Almost every AI-generated transmute is wrong.

**DON'T**
```rust
let n: u32 = unsafe { std::mem::transmute([0u8, 0, 0, 1]) };
```

**DO**
```rust
let n = u32::from_be_bytes([0, 0, 0, 1]);
```

### Type System

#### `rust-integer-cast-truncation` (warning) — `as` between integer types that may truncate

`usize as u32`, `i64 as i32`, `u64 as usize` (on 32-bit) silently truncate. Use `try_into()`.

**DON'T**
```rust
let count: u32 = items.len() as u32;
```

**DO**
```rust
let count: u32 = u32::try_from(items.len()).map_err(|_| Error::TooMany)?;
```

#### `rust-floating-point-eq` (warning) — `==` or `!=` on `f32` / `f64`

`0.1 + 0.2 == 0.3` is `false`. Use epsilon comparison.

**DON'T**
```rust
if computed_rate == 0.1 { discount(); }
```

**DO**
```rust
const EPS: f64 = 1e-9;
if (computed_rate - 0.1).abs() < EPS { discount(); }
```

#### `rust-lifetime-overengineering` (warning) — explicit `<'a>` where elision works, or `'static` where a borrow would do

Most functions don't need explicit lifetimes. `'static` on generics forbids any borrowed data.

**DON'T**
```rust
fn first<'a, 'b>(s: &'a str, _t: &'b str) -> &'a str { s }
fn store<T: 'static>(x: T) { /* forbids &'a T */ }
```

**DO**
```rust
fn first(s: &str, _t: &str) -> &str { s }  // elision
fn store<T>(x: T) { /* accepts anything owned */ }
```

### Performance

#### `rust-unnecessary-clone` (warning) — `.clone()` to silence the borrow checker

The AI-Rust tell. Try borrowing first. `&str` over `String`, `&[T]` over `Vec<T>`, `&T` over deep clones.

**DON'T**
```rust
fn greet(name: String) -> String {
    format!("hello, {}", name.clone())  // name is already owned
}
let users: Vec<User> = load();
process(users.clone());
```

**DO**
```rust
fn greet(name: &str) -> String {
    format!("hello, {name}")
}
let users: Vec<User> = load();
process(&users);
```

#### `rust-collect-then-iter` (warning) — `.collect::<Vec<_>>()` then immediately iterating again

Wasted O(N) allocation. Iterators are lazy. Drop the `.collect()`.

**DON'T**
```rust
let names: Vec<String> = users.iter().map(|u| u.name.clone()).collect();
for n in names.iter() { println!("{n}"); }
```

**DO**
```rust
for n in users.iter().map(|u| &u.name) { println!("{n}"); }
```

#### `rust-string-concat-in-loop` (warning) — `s = s + ...` reallocating in a tight loop

O(N²) realloc cascade. Use `String::with_capacity` or `Vec::join`.

**DON'T**
```rust
let mut out = String::new();
for row in &rows {
    out = out + &row.name + "\n";
}
```

**DO**
```rust
let mut out = String::with_capacity(rows.len() * 32);
for row in &rows {
    out.push_str(&row.name);
    out.push('\n');
}
```

### Idioms

#### `rust-string-when-str-works` (warning) — Function takes `String` / `&String` when `&str` would do

`&str` accepts string literals, `&String`, and slices — no allocation needed. Same for `&Vec<T>` → `&[T]`, `&PathBuf` → `&Path`.

**DON'T**
```rust
fn looks_like_email(s: &String) -> bool { s.contains('@') }
looks_like_email(&"a@b.c".to_string());
```

**DO**
```rust
fn looks_like_email(s: &str) -> bool { s.contains('@') }
looks_like_email("a@b.c");
```

#### `rust-needless-return` (warning) — Trailing `return expr;` on the last expression

Rust returns the final expression. `return` is for early exits.

**DON'T**
```rust
fn double(x: i32) -> i32 { return x * 2; }
```

**DO**
```rust
fn double(x: i32) -> i32 { x * 2 }
```

#### `rust-match-single-arm` (warning) — `match` with one real arm + `_ => ...` where `if let` is clearer

**DON'T**
```rust
match maybe_user {
    Some(u) => greet(u),
    _ => {}
}
```

**DO**
```rust
if let Some(u) = maybe_user { greet(u); }
```

#### `rust-trait-object-when-generic-works` (warning) — `Box<dyn Trait>` where generics would monomorphize

`Box<dyn Trait>` adds heap allocation + vtable indirection per call. Use generics for parameters; reserve `dyn Trait` for heterogeneous collections.

**DON'T**
```rust
fn process(handler: Box<dyn Fn(i32) -> i32>) -> i32 { handler(42) }
```

**DO**
```rust
fn process(handler: impl Fn(i32) -> i32) -> i32 { handler(42) }
```

#### `rust-derive-omission` (warning) — Public struct missing `Debug` / `Clone` / `PartialEq` / `Eq` / `Hash` / `Default`

`Debug` is table stakes. Decide derives at definition time, not at first use.

**DON'T**
```rust
pub struct UserId(u64);
```

**DO**
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UserId(u64);
```

### AI-slop specific

#### `rust-block-in-async` (error) — Blocking call (`std::fs`, `std::thread::sleep`, sync `reqwest`) inside `async fn`

Blocks the executor's worker thread, stalling all other tasks. Use `tokio::*` or `spawn_blocking`.

**DON'T**
```rust
async fn read_config() -> String {
    std::thread::sleep(Duration::from_secs(1));
    std::fs::read_to_string("c.toml").unwrap()
}
```

**DO**
```rust
async fn read_config() -> std::io::Result<String> {
    tokio::time::sleep(Duration::from_secs(1)).await;
    tokio::fs::read_to_string("c.toml").await
}
```

#### `rust-block-on-in-async` (error) — `block_on` called inside `async fn`

Deadlocks or panics ("Cannot start a runtime from within a runtime"). `.await` the future directly.

**DON'T**
```rust
async fn handler() -> Data {
    tokio::runtime::Handle::current().block_on(fetch())
}
```

**DO**
```rust
async fn handler() -> Data { fetch().await }
```

#### `rust-allow-clippy-blanket` (warning) — `#[allow(clippy::all)]` or `#[allow(warnings)]` at module/crate scope

Silences every future warning. Allow specific lints with a comment and scope it tight.

**DON'T**
```rust
#![allow(warnings)]
#![allow(clippy::all)]
```

**DO**
```rust
#[allow(clippy::cast_ptr_alignment)]  // bridge to C; tested below
fn into_raw(ptr: *const u8) -> *const u32 { /* ... */ }
```

## Common AI-slop combinations

```rust
// "Defensive slop" — three bugs, one fn
fn load_user(id: &str) -> User {
    let id = id.parse::<u64>().unwrap();              // rust-unwrap-in-prod
    let row = db.query(id).unwrap();                  // rust-unwrap-in-prod
    match row.role.as_str() {
        "admin" => User { role: Role::Admin, .. },
        "user"  => User { role: Role::User, .. },
        _ => unreachable!(),                          // rust-panic-on-input
    }
}
```

Three rules tripped. Rewrite returning `Result<User, LoadError>` with `?` and proper variant matching.

## Pre-emit verification checklist

- [ ] No `.unwrap()` / `.expect()` in non-test code (use `?` or `Result`)
- [ ] No `panic!` / `unreachable!` / `todo!` reachable from input
- [ ] Every `unsafe` block has a `// SAFETY:` comment
- [ ] No `transmute` where a safe cast works
- [ ] No `.clone()` where a borrow works
- [ ] No `as` between integer types where `try_into()` would work
- [ ] No `f32`/`f64` `==` comparison without epsilon
- [ ] No explicit lifetimes where elision works
- [ ] No blocking calls inside `async fn`
- [ ] No `block_on` inside `async fn`
- [ ] Public structs derive `Debug` (and others as appropriate)
- [ ] Library errors are typed enums (`thiserror`), not `String`
- [ ] No `Box<dyn Trait>` where generics work
- [ ] No `String`/`&String` parameters where `&str` works
- [ ] No `#[allow(warnings)]` at module/crate scope

## Related skills

- `/aidoctor:scan` — language-agnostic lint check
- `/aidoctor:simplify` — three-angle review of changed code
- `/aidoctor:audit` — six-dimensional whole-project review
- `python-rules`, `react-rules`, `js-rules`, `go-rules` — sibling rule packs
