import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages the bot's configuration, with support for hot-reloading."""

    def __init__(self, path: str | Path):
        """
        Initializes the ConfigManager.

        Args:
            path: The path to the configuration JSON file.
        """
        self.path = Path(path)
        self._config_data: Dict[str, Any] = {}
        self._last_mtime: Optional[float] = None
        self.logger = logging.getLogger(__name__)
        self._load()

    def _load(self) -> None:
        """Loads or reloads configuration from the JSON file."""
        self.logger.info("Attempting to load configuration from %s", self.path)
        try:
            with self.path.open("r", encoding="utf-8") as f:
                self._config_data = json.load(f)
            self._last_mtime = self.path.stat().st_mtime
            self.logger.info("Configuration loaded successfully from %s", self.path)
        except FileNotFoundError:
            self.logger.critical("Configuration file not found at %s.", self.path)
            raise
        except json.JSONDecodeError as e:
            self.logger.critical("Failed to parse JSON from %s: %s", self.path, e)
            raise

    def _check_for_updates(self) -> None:
        """Checks if the configuration file has been modified and reloads it if so."""
        try:
            mtime = self.path.stat().st_mtime
            if self._last_mtime is None or mtime > self._last_mtime:
                self.logger.info("Change detected in '%s'. Reloading configuration.", self.path)
                self._load()
        except FileNotFoundError:
            self.logger.warning("Configuration file '%s' was not found during a scheduled check.", self.path)
        except Exception as e:
            self.logger.error("An error occurred during configuration reload: %s", e, exc_info=True)

    async def start_hot_reload_loop(self, interval_seconds: int = 5) -> None:
        """Starts a background task to periodically check for config changes."""
        self.logger.info("Starting configuration hot-reload loop (check interval: %ss).", interval_seconds)
        while True:
            await asyncio.sleep(interval_seconds)
            self._check_for_updates()

    def __getitem__(self, key: str) -> Any:
        """Allows dictionary-style access to config values (e.g., config['key'])."""
        return self._config_data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Allows safe dictionary-style .get() access to config values (e.g., config.get('key', 'default'))."""
        return self._config_data.get(key, default)

    def __contains__(self, item: str) -> bool:
        """Allows the `in` operator to check for key existence (e.g., 'key' in config)."""
        return item in self._config_data

    def get_all_config(self) -> Dict[str, Any]:
        """Returns a copy of the entire configuration dictionary."""
        return self._config_data.copy()