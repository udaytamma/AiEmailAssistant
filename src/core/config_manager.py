"""
Configuration Manager for Email Assistant
Handles loading and managing configuration settings with error handling and logging.
"""

import json
import os
import traceback
from pathlib import Path
from typing import Any, Optional

# Import logging utilities using relative path since we're in src/core
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger_utils import setup_logger, log_exception
from utils.metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """Manages application configuration from config.json with error handling."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            # Use config/config.json in project root
            config_dir = Path(__file__).parent.parent.parent / 'config'
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / 'config.json'

        self.config_file = str(config_file)
        self.config = self.load_config()
        logger.info(f"ConfigManager initialized with file: {self.config_file}")

    def load_config(self) -> dict:
        """
        Load configuration from JSON file.

        Returns:
            dict: Configuration dictionary

        Note:
            Falls back to default configuration if file is missing or invalid.
        """
        metrics = get_metrics_tracker()

        try:
            if not os.path.exists(self.config_file):
                logger.warning(f"Configuration file '{self.config_file}' not found. Creating with defaults.")
                config = self.get_default_config()
                self._save_config(config)
                return config

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            logger.info(f"Successfully loaded configuration from {self.config_file}")
            return config

        except json.JSONDecodeError as e:
            error_msg = f"Error parsing configuration file: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            print(f"⚠️  {error_msg}. Using defaults.")
            return self.get_default_config()

        except PermissionError as e:
            error_msg = f"Permission denied reading configuration file: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "PermissionError", error_msg, traceback.format_exc())
            print(f"⚠️  {error_msg}. Using defaults.")
            return self.get_default_config()

        except Exception as e:
            log_exception(logger, e, "Unexpected error loading configuration")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            print(f"⚠️  Unexpected error loading configuration: {e}. Using defaults.")
            return self.get_default_config()

    def get_default_config(self) -> dict:
        """
        Return default configuration if config file is missing.

        Returns:
            dict: Default configuration dictionary
        """
        logger.debug("Returning default configuration")
        return {
            "api_settings": {
                "gemini_model": "gemini-2.5-flash-lite",
                "requests_per_minute": 30,
                "max_retries": 3,
                "timeout_seconds": 30
            },
            "gmail_settings": {
                "max_emails_to_fetch": 10,
                "search_query": "is:unread newer_than:1d",
                "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
            },
            "cache_settings": {
                "enabled": True,
                "max_cached_emails": 30,
                "cache_file": "data/cache/email_cache.json",
                "cache_expiry_hours": 24
            },
            "digest_settings": {
                "newsletter_summary_length": 3,
                "category_summary_max_points": 5,
                "email_body_max_chars": 3000
            },
            "display_settings": {
                "snippet_length": 150,
                "truncate_subject_length": 50
            }
        }

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.

        Args:
            section: Configuration section name
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        try:
            value = self.config[section][key]
            logger.debug(f"Config get: {section}.{key} = {value}")
            return value
        except KeyError:
            logger.debug(f"Config key not found: {section}.{key}, using default: {default}")
            return default
        except Exception as e:
            logger.warning(f"Error getting config value {section}.{key}: {e}")
            return default

    def update(self, section: str, key: str, value: Any) -> None:
        """
        Update a configuration value.

        Args:
            section: Configuration section name
            key: Configuration key
            value: New value
        """
        try:
            if section not in self.config:
                self.config[section] = {}
                logger.debug(f"Created new config section: {section}")

            self.config[section][key] = value
            logger.info(f"Updated config: {section}.{key} = {value}")

        except Exception as e:
            log_exception(logger, e, f"Error updating config {section}.{key}")
            metrics = get_metrics_tracker()
            metrics.record_error(__name__, type(e).__name__, f"Config update failed: {e}")

    def _save_config(self, config: dict) -> None:
        """Internal method to save configuration."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            logger.debug(f"Configuration saved to {self.config_file}")

        except Exception as e:
            log_exception(logger, e, "Error saving configuration")

    def save(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            bool: True if successful, False otherwise
        """
        metrics = get_metrics_tracker()

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            logger.info(f"Configuration saved to {self.config_file}")
            print(f"✅ Configuration saved to {self.config_file}")
            return True

        except PermissionError as e:
            error_msg = f"Permission denied saving configuration: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "PermissionError", error_msg)
            print(f"⚠️  {error_msg}")
            return False

        except Exception as e:
            log_exception(logger, e, "Error saving configuration")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            print(f"⚠️  Error saving configuration: {e}")
            return False

    def display(self) -> None:
        """Display current configuration."""
        try:
            logger.debug("Displaying configuration")
            print("\n" + "=" * 80)
            print("CURRENT CONFIGURATION")
            print("=" * 80 + "\n")
            print(json.dumps(self.config, indent=2))
            print("\n" + "=" * 80)

        except Exception as e:
            logger.error(f"Error displaying configuration: {e}")
            print(f"⚠️  Error displaying configuration: {e}")


# Example usage
if __name__ == '__main__':
    config = ConfigManager()
    config.display()
