package config

import (
	"encoding/json"
	"fmt"
	"os"
)

// Config holds application configuration loaded from a JSON file.
type Config struct {
	Host    string            `json:"host"`
	Port    int               `json:"port"`
	Options map[string]string `json:"options,omitempty"`
}

// LoadConfig reads the JSON file at path, parses it, and returns the Config.
// All errors are wrapped with context using fmt.Errorf and %w so callers can
// inspect the underlying cause with errors.Is / errors.As.
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("LoadConfig: read %q: %w", path, err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("LoadConfig: parse %q: %w", path, err)
	}

	return &cfg, nil
}
