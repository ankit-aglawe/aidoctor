//! Thread-safe counter built on `std::sync::Mutex`.
//!
//! Poisoning policy: `Mutex::lock()` returns `Err(PoisonError)` when another
//! thread panicked while holding the guard. For a simple integer counter the
//! "in-flight" state is always consistent — there is no partially-updated
//! invariant to worry about — so we recover the inner guard via
//! `unwrap_or_else(|e| e.into_inner())` instead of cascading the panic across
//! every caller (which is what `.lock().unwrap()` would do).
//!
//! See rust-rules: `rust-mutex-poison-ignored`.

use std::sync::Mutex;

/// A thread-safe monotonically increasing counter.
#[derive(Debug, Default)]
pub struct Counter {
    inner: Mutex<u64>,
}

impl Counter {
    /// Create a new counter starting at 0.
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(0),
        }
    }

    /// Increment the counter by 1, returning the new value.
    ///
    /// Recovers from a poisoned mutex: the counter's invariant (a single
    /// `u64`) cannot be left in a partial state, so reading through poison
    /// is safe.
    pub fn increment(&self) -> u64 {
        let mut guard = self
            .inner
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *guard = guard.saturating_add(1);
        *guard
    }

    /// Read the current value.
    pub fn value(&self) -> u64 {
        let guard = self
            .inner
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *guard
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn new_starts_at_zero() {
        let c = Counter::new();
        assert_eq!(c.value(), 0);
    }

    #[test]
    fn increment_returns_new_value() {
        let c = Counter::new();
        assert_eq!(c.increment(), 1);
        assert_eq!(c.increment(), 2);
        assert_eq!(c.value(), 2);
    }

    #[test]
    fn increment_is_thread_safe() {
        let c = Arc::new(Counter::new());
        let mut handles = Vec::with_capacity(8);
        for _ in 0..8 {
            let c = Arc::clone(&c); // Arc clone: refcount bump, not deep copy
            handles.push(thread::spawn(move || {
                for _ in 0..1000 {
                    c.increment();
                }
            }));
        }
        for h in handles {
            // .unwrap() is acceptable in tests per rust-rules guidance.
            h.join().unwrap();
        }
        assert_eq!(c.value(), 8 * 1000);
    }

    #[test]
    fn recovers_from_poisoned_mutex() {
        let c = Arc::new(Counter::new());
        let c_panic = Arc::clone(&c);
        let _ = thread::spawn(move || {
            let _guard = c_panic
                .inner
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            panic!("intentional poison");
        })
        .join();

        // Mutex is now poisoned, but Counter still works.
        assert_eq!(c.increment(), 1);
        assert_eq!(c.value(), 1);
    }
}
