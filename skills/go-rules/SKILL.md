---
name: go-rules
version: 1.0.0
description: |
  Go coding standards for AI-generated code. Use whenever writing, editing,
  or reviewing Go — services, CLIs, libraries. Triggers on .go files.
  Covers error discipline (no ignored errors, wrap with %w, no panic in libs),
  goroutine + channel safety (no leaks, no value-copied mutexes), context
  propagation, and Go idioms AI agents reflexively get wrong.
triggers:
  - writing go
  - writing golang
  - editing go
  - .go file
  - go service
  - go library
benefits-from: [scan, simplify, audit]
---

# go-rules

Rules tuned for AI-generated Go. AI agents reflexively discard errors with `_`, return bare `err` without context, embed mutexes by value, leak goroutines, drop `context.Context` from function signatures, and port Java/C# conventions (`GetX`, `XService` in package `x`). This skill catches them BEFORE you emit the code.

## When to use

Every Go file you generate, edit, or refactor — service code, library code, CLI tools. **No exceptions for "simple" tools or "throwaway" scripts.** Ignored errors and goroutine leaks leak through all three.

## Iron Law

```
NO GO EMITTED WITHOUT THE 5-POINT PRE-FLIGHT PASSING
```

If any check is unclear, resolve it **before** generating code. **Spirit over letter** — paraphrasing is the same violation.

## Read this BEFORE you type a single line of Go

A 30-second pre-flight that prevents most violations:

1. **Errors**: every function call returning `error` must have the error checked. `_ = f()` is forbidden except on documented-infallible operations. Return errors wrapped with `fmt.Errorf("op: %w", err)` for context.
2. **No panic in library code**: library functions return `error`. `panic` is reserved for `main`/`init` or invariant violations the compiler can't enforce.
3. **Goroutines**: every `go func()` needs a termination path. Accept `ctx context.Context` and select on `ctx.Done()`, or accept a `done chan struct{}`.
4. **Mutexes**: `sync.Mutex` lives in structs with pointer receivers, never value receivers. Value receivers copy the mutex.
5. **Context**: every function that does I/O takes `ctx context.Context` as its first parameter and propagates it. Never `context.Background()` mid-call-chain.

If all five are clear, continue. If any is unclear, resolve it before generating code.

## Anti-rationalization

| Thought | Reality |
|---|---|
| "I'll discard this error with `_`, it can't fail" | It can. Wrap with `%w` and propagate. |
| "Bare `return err` is fine, the caller can figure it out" | The stack trace is gone. Wrap with `fmt.Errorf("op: %w", err)`. |
| "I'll `panic` in this library function, the caller can recover" | Every caller now needs `defer recover()`. Return `error`. |
| "The goroutine will exit when the channel closes" | If nothing closes it, the goroutine leaks. Accept `ctx`. |
| "Comparing `err.Error() == "not found"` is fine" | The string changes upstream and your check silently breaks. Use `errors.Is`. |
| "I'll use `time.Now()` directly in the business logic" | Tests become timezone-dependent and flaky. Inject a clock. |
| "Different words so the rule doesn't apply" | Spirit over letter. Same violation. |

## When a rule genuinely can't be followed

- **`_` on infallible ops** (`bytes.Buffer.Write`, `strings.Builder.WriteString`) is fine — they document that they never return an error.
- **`panic` in `main` / `init`** is acceptable as the error-reporting mechanism for fatal startup failure.
- **`time.Now()` directly** is fine in startup logging and one-shot CLI commands — but not in code that has tests.

If you're reaching for `_` more than twice per function, rewrite.

## The rules

### Error Handling

#### `go-error-ignored` (error) — Error return value discarded with `_` or not checked

The single most common Go AI-slop pattern. Every non-nil error must be checked, handled, or wrapped.

**DON'T**
```go
data, _ := os.ReadFile(path)
json.Unmarshal(data, &cfg)  // err discarded
defer f.Close()             // error from Close lost
```

**DO**
```go
data, err := os.ReadFile(path)
if err != nil {
    return fmt.Errorf("read config: %w", err)
}
if err := json.Unmarshal(data, &cfg); err != nil {
    return fmt.Errorf("parse config: %w", err)
}
defer func() {
    if cerr := f.Close(); cerr != nil && err == nil {
        err = cerr
    }
}()
```

#### `go-error-not-wrapped` (warning) — Error returned bare without `%w` context

`return err` from deep in a call chain produces traces with no context. Wrap with `fmt.Errorf("op: %w", err)`.

**DON'T**
```go
func loadUser(id int) (*User, error) {
    row, err := db.Query("...", id)
    if err != nil {
        return nil, err  // no context
    }
    ...
}
```

**DO**
```go
func loadUser(id int) (*User, error) {
    row, err := db.Query("...", id)
    if err != nil {
        return nil, fmt.Errorf("loadUser(%d): %w", id, err)
    }
    ...
}
```

#### `go-error-string-comparison` (error) — Comparing errors by `.Error()` string

Breaks when the upstream error string changes. Use `errors.Is` for sentinels, `errors.As` for typed.

**DON'T**
```go
if err.Error() == "record not found" {
    return nil
}
```

**DO**
```go
if errors.Is(err, sql.ErrNoRows) { return nil }
```

#### `go-panic-in-library` (error) — `panic()` in library code instead of returning an error

Library functions return `error`. `panic` forces every caller into `defer recover()`.

**DON'T**
```go
func ParseConfig(b []byte) *Config {
    var c Config
    if err := json.Unmarshal(b, &c); err != nil {
        panic(err)
    }
    return &c
}
```

**DO**
```go
func ParseConfig(b []byte) (*Config, error) {
    var c Config
    if err := json.Unmarshal(b, &c); err != nil {
        return nil, fmt.Errorf("parse config: %w", err)
    }
    return &c, nil
}
```

### Concurrency

#### `go-goroutine-leak` (error) — `go func()` with no termination path

Every goroutine needs an explicit shutdown signal. Accept `ctx` and `select` on `ctx.Done()`.

**DON'T**
```go
func startWorker(jobs <-chan Job) {
    go func() {
        for j := range jobs {  // never exits if jobs is never closed
            process(j)
        }
    }()
}
```

**DO**
```go
func startWorker(ctx context.Context, jobs <-chan Job) {
    go func() {
        for {
            select {
            case <-ctx.Done():
                return
            case j, ok := <-jobs:
                if !ok { return }
                process(j)
            }
        }
    }()
}
```

#### `go-loop-var-capture` (error) — Closure captures loop variable by reference

Pre-Go 1.22: all goroutines see the same final value. Even on 1.22+, explicit rebind communicates intent.

**DON'T**
```go
for _, item := range items {
    go func() {
        process(item)  // all goroutines see the last item
    }()
}
```

**DO**
```go
for _, item := range items {
    item := item  // explicit rebind
    go func() { process(item) }()
}
// or:
for _, item := range items {
    go func(item Item) { process(item) }(item)
}
```

#### `go-mutex-by-value` (error) — `sync.Mutex` copied by value

Mutex must be passed by pointer; structs containing it are non-copyable.

**DON'T**
```go
type Counter struct {
    mu sync.Mutex
    n  int
}
func (c Counter) Inc() {  // value receiver copies the mutex
    c.mu.Lock()
    c.n++
    c.mu.Unlock()
}
```

**DO**
```go
func (c *Counter) Inc() {  // pointer receiver
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```

#### `go-channel-unbuffered-send` (warning) — Send on unbuffered channel without guaranteed receiver

If no goroutine is ranging on `ch`, the send blocks forever — goroutine leak. Buffer the channel or wrap in `select` with `ctx.Done()`.

**DON'T**
```go
func fanOut(in []int) <-chan int {
    out := make(chan int)  // unbuffered
    for _, v := range in {
        go func(v int) { out <- compute(v) }(v)
    }
    return out
}
```

**DO**
```go
func fanOut(ctx context.Context, in []int) <-chan int {
    out := make(chan int, len(in))
    for _, v := range in {
        go func(v int) {
            select {
            case out <- compute(v):
            case <-ctx.Done():
            }
        }(v)
    }
    return out
}
```

#### `go-context-not-propagated` (error) — Function does I/O without accepting `context.Context`

Every function that does I/O accepts `ctx context.Context` as its first parameter. Never `context.Background()` mid-chain.

**DON'T**
```go
func fetchUser(id int) (*User, error) {
    resp, err := http.Get(fmt.Sprintf("/users/%d", id))  // no ctx
    ...
}
```

**DO**
```go
func fetchUser(ctx context.Context, id int) (*User, error) {
    req, _ := http.NewRequestWithContext(ctx, "GET", fmt.Sprintf("/users/%d", id), nil)
    resp, err := http.DefaultClient.Do(req)
    ...
}
```

### Idioms

#### `go-interface-pointer-return` (warning) — Returning `interface{}` or `any` from a public function

Forces every caller to type-assert. Return concrete types from constructors.

**DON'T**
```go
func NewClient(cfg Config) any {
    return &httpClient{cfg: cfg}
}
```

**DO**
```go
func NewClient(cfg Config) *HTTPClient {
    return &HTTPClient{cfg: cfg}
}
```

#### `go-stuttering-name` (warning) — Type or function name stutters the package name

`http.HTTPClient`, `user.UserService`, `cache.CacheEntry` — drop the package prefix.

**DON'T**
```go
package user
type UserService struct { ... }
func NewUserService() *UserService { ... }
```

**DO**
```go
package user
type Service struct { ... }
func NewService() *Service { ... }
```

#### `go-getter-prefix` (warning) — Getter method prefixed with `Get`

Getters are `Foo()`, not `GetFoo()`. Setters keep `Set`.

**DON'T**
```go
func (u *User) GetName() string { return u.name }
```

**DO**
```go
func (u *User) Name() string { return u.name }
```

#### `go-empty-interface-any` (warning) — `interface{}` used instead of `any`

Since Go 1.18, `any` is the canonical alias.

**DON'T**
```go
var registry map[string]interface{}
```

**DO**
```go
var registry map[string]any
```

#### `go-init-abuse` (warning) — `init()` function doing non-trivial work

Runs at import, can't fail gracefully, untestable. Move setup into an exported `NewX` / `Setup` function called from `main`.

**DON'T**
```go
var db *sql.DB
func init() {
    var err error
    db, err = sql.Open("postgres", os.Getenv("DSN"))
    if err != nil { log.Fatal(err) }
}
```

**DO**
```go
func NewDB(ctx context.Context, dsn string) (*sql.DB, error) {
    db, err := sql.Open("postgres", dsn)
    if err != nil { return nil, fmt.Errorf("open db: %w", err) }
    return db, db.PingContext(ctx)
}
```

### Performance

#### `go-slice-append-aliasing` (error) — `append` result discarded, or shared-slice aliasing

`append(s, x)` without assignment is discarded. Shared slices with cap may mutate caller's slice.

**DON'T**
```go
func addDefault(items []string) []string {
    append(items, "default")  // discarded
    return items
}
```

**DO**
```go
func addDefault(items []string) []string {
    return append(items, "default")
}
```

#### `go-string-concat-loop` (warning) — String built with `+=` in a loop

O(N²). Use `strings.Builder`.

**DON'T**
```go
out := ""
for _, row := range rows {
    out += row.Name + "\n"
}
```

**DO**
```go
var b strings.Builder
for _, row := range rows {
    b.WriteString(row.Name)
    b.WriteByte('\n')
}
out := b.String()
```

#### `go-make-without-capacity` (warning) — `make([]T, 0)` / `make(map)` when final size is known

Pre-allocate to avoid 2-4× wasted allocations on hot paths.

**DON'T**
```go
results := []Result{}
for _, item := range items {
    results = append(results, transform(item))
}
```

**DO**
```go
results := make([]Result, 0, len(items))
for _, item := range items {
    results = append(results, transform(item))
}
```

### AI-slop specific

#### `go-stub-comment` (error) — `// TODO: implement` or placeholder shipping as silent no-op

AI assistants leave `// TODO: implement this`, `// fill in the logic` then ship the empty function. Either implement, or `panic("unimplemented: <reason>")` so the failure is visible at runtime.

**DON'T**
```go
func ChargeCard(amount int) error {
    // TODO: implement
    return nil  // ships as silent success
}
```

**DO**
```go
func ChargeCard(amount int) error {
    panic("ChargeCard: pending PSP integration (GH-456)")
}
```

#### `go-hardcoded-secret` (error) — API key / token / password literal in source

Anything matching `apiKey`, `token`, `password`, `secret` with `sk-...`, `AKIA...`, `eyJ...` strings must come from `os.Getenv` or a secret manager.

**DON'T**
```go
const apiKey = "sk-proj-9f8e7d6c5b4a3210ABCD"
```

**DO**
```go
apiKey := os.Getenv("OPENAI_API_KEY")
if apiKey == "" {
    return errors.New("OPENAI_API_KEY not set")
}
```

#### `go-time-now-in-test` (warning) — `time.Now()` directly in tested code paths

Makes tests timezone-dependent and flaky. Inject a clock.

**DON'T**
```go
func (s *Session) Expired() bool {
    return time.Now().After(s.expiresAt)
}
```

**DO**
```go
type Clock func() time.Time
func (s *Session) Expired(now Clock) bool {
    return now().After(s.expiresAt)
}
```

## Common AI-slop combinations

```go
// "Defensive slop" — three bugs, one function
func loadUserConfig(path string) *Config {
    data, _ := os.ReadFile(path)            // go-error-ignored
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        panic(err)                          // go-panic-in-library
    }
    return &cfg
}
```

Three rules tripped. Rewrite returning `(*Config, error)` with `%w`-wrapped errors at each step.

## Pre-emit verification checklist

- [ ] No errors discarded with `_` (except documented infallible ops)
- [ ] Every error returned is wrapped with `fmt.Errorf("op: %w", err)`
- [ ] No `panic()` in library code (use `error` returns)
- [ ] No `err.Error() == ...` comparison (use `errors.Is` / `errors.As`)
- [ ] Every goroutine has a termination path (ctx, done channel)
- [ ] No loop var captured by reference in closure (rebind or pass as arg)
- [ ] Mutexes use pointer receivers
- [ ] No unbuffered channel send without guaranteed receiver or `select`
- [ ] Every I/O function takes `ctx context.Context`
- [ ] No `interface{}` / `any` returns from public functions
- [ ] No package-stuttering names (`http.HTTPClient`)
- [ ] No `GetX()` getter naming
- [ ] `any` instead of `interface{}` in new code
- [ ] No non-trivial work in `init()`
- [ ] `append` results assigned back
- [ ] No `+=` string building in loops (use `strings.Builder`)
- [ ] `make` slices/maps with capacity when size is known
- [ ] No `// TODO: implement` stubs returning nil
- [ ] No hardcoded secrets
- [ ] `time.Now()` injected via clock parameter for testable code

## Related skills

- `/aidoctor:scan` — language-agnostic lint check
- `/aidoctor:simplify` — three-angle review of changed code
- `/aidoctor:audit` — six-dimensional whole-project review
- `python-rules`, `react-rules`, `js-rules`, `rust-rules` — sibling rule packs
