// Package counter provides a thread-safe integer counter.
//
// Counter embeds a sync.Mutex, which means it must never be copied.
// All methods use pointer receivers (rule: go-mutex-by-value) so that
// callers operate on the same underlying mutex and state. Constructing
// a Counter returns *Counter for the same reason.
package counter

import "sync"

// Counter is a goroutine-safe integer counter.
//
// The zero value is ready to use, but prefer NewCounter for clarity.
// Counter must not be copied after first use; pass it by pointer.
type Counter struct {
	mu sync.Mutex
	n  int64
}

// NewCounter returns a new zero-valued Counter.
// It returns a pointer because Counter contains a sync.Mutex and must
// not be copied.
func NewCounter() *Counter {
	return &Counter{}
}

// Inc increments the counter by 1.
// Pointer receiver: a value receiver would copy the embedded Mutex.
func (c *Counter) Inc() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n++
}

// Add adds delta to the counter.
// Pointer receiver: required because Counter holds a sync.Mutex.
func (c *Counter) Add(delta int64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n += delta
}

// Value returns the current counter value.
// Note: this is NOT GetValue — Go getters drop the Get prefix
// (rule: go-getter-prefix). Pointer receiver because Counter holds
// a sync.Mutex.
func (c *Counter) Value() int64 {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.n
}

// Reset sets the counter back to zero.
// Pointer receiver: required because Counter holds a sync.Mutex.
func (c *Counter) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n = 0
}
