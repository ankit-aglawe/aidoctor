use std::sync::Mutex;

pub struct Counter {
    value: Mutex<u64>,
}

impl Counter {
    pub fn new() -> Self {
        Counter {
            value: Mutex::new(0),
        }
    }

    pub fn increment(&self) {
        let mut guard = self.value.lock().unwrap();
        *guard += 1;
    }

    pub fn value(&self) -> u64 {
        *self.value.lock().unwrap()
    }
}

impl Default for Counter {
    fn default() -> Self {
        Self::new()
    }
}
