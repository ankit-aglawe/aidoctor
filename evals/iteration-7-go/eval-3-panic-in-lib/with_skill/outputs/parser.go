package config

import (
	"encoding/json"
	"fmt"
)

// Config holds the parsed configuration values.
type Config struct {
	Name    string            `json:"name"`
	Version string            `json:"version"`
	Options map[string]string `json:"options,omitempty"`
}

// ParseConfig parses the given JSON-encoded bytes into a *Config.
// It returns a non-nil error wrapping the underlying failure on invalid input;
// library code never panics on caller-supplied data.
func ParseConfig(b []byte) (*Config, error) {
	if len(b) == 0 {
		return nil, fmt.Errorf("parse config: empty input")
	}

	var c Config
	if err := json.Unmarshal(b, &c); err != nil {
		return nil, fmt.Errorf("parse config: unmarshal: %w", err)
	}

	return &c, nil
}
