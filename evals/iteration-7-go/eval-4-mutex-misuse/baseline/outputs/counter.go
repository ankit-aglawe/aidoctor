package counter

import "sync"

// Counter is a thread-safe counter.
type Counter struct {
	sync.Mutex
	count int
}

// Inc increments the counter.
func (c Counter) Inc() {
	c.Lock()
	defer c.Unlock()
	c.count++
}

// Value returns the current counter value.
func (c Counter) Value() int {
	c.Lock()
	defer c.Unlock()
	return c.count
}
