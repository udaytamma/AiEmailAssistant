"""
Configuration Manager for Email Assistant
Handles loading and managing configuration settings
"""

import json
import os

class ConfigManager:
    """Manages application configuration from config.json"""

    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Configuration file '{self.config_file}' not found. Using defaults.")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing configuration file: {e}. Using defaults.")
            return self.get_default_config()

    def get_default_config(self):
        """Return default configuration if config file is missing"""
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
                "cache_file": "email_cache.json",
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

    def get(self, section, key, default=None):
        """Get a specific configuration value"""
        try:
            return self.config[section][key]
        except KeyError:
            return default

    def update(self, section, key, value):
        """Update a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"⚠️  Error saving configuration: {e}")

    def display(self):
        """Display current configuration"""
        print("\n" + "=" * 80)
        print("CURRENT CONFIGURATION")
        print("=" * 80 + "\n")
        print(json.dumps(self.config, indent=2))
        print("\n" + "=" * 80)

# Example usage
if __name__ == '__main__':
    config = ConfigManager()
    config.display()
