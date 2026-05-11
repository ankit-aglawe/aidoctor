package config

import (
	"encoding/json"
	"os"
)

type Config struct {
	Host     string         `json:"host"`
	Port     int            `json:"port"`
	Debug    bool           `json:"debug"`
	Settings map[string]any `json:"settings"`
}

func LoadConfig(path string) *Config {
	data, _ := os.ReadFile(path)

	cfg := &Config{}
	_ = json.Unmarshal(data, cfg)

	return cfg
}
