package slice

// AddDefault returns items with "default" appended.
//
// append may allocate a new backing array; its result MUST be assigned
// back (or returned) — otherwise the appended element is discarded
// (go-slice-append-aliasing).
func AddDefault(items []string) []string {
	return append(items, "default")
}
