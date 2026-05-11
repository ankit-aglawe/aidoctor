package parser

import (
	"encoding/json"
)

// Config represents the parsed configuration.
type Config struct {
	Name    string                 `json:"name"`
	Version string                 `json:"version"`
	Options map[string]interface{} `json:"options"`
}

// ParseConfig parses the given bytes into a *Config.
// It panics on parse error; callers may use defer/recover to handle failures.
func ParseConfig(b []byte) *Config {
	var c Config
	if err := json.Unmarshal(b, &c); err != nil {
		panic(err)
	}
	return &c
}
