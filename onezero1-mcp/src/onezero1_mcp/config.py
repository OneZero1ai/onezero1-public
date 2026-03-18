"""Configuration for OneZero1 MCP Server."""

import json
import os
from pathlib import Path

API_URL = os.environ.get("ONEZERO1_API_URL", "https://api.onezero1.ai")

# API key can come from env var or persisted config
API_KEY = os.environ.get("ONEZERO1_API_KEY", "")

# Config file for persisting API key across sessions
CONFIG_DIR = Path(os.environ.get("ONEZERO1_CONFIG_DIR", os.path.expanduser("~/.onezero1")))
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load persisted config from ~/.onezero1/config.json."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config: dict) -> None:
    """Save config to ~/.onezero1/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str:
    """Get API key from env var or persisted config."""
    if API_KEY:
        return API_KEY
    config = load_config()
    return config.get("api_key", "")


def get_agent_id() -> str:
    """Get agent ID from persisted config."""
    config = load_config()
    return config.get("agent_id", "")
