"""
Gemini Interaction Logger
Logs all Gemini API requests and responses to a separate file with daily rotation.
Provides high readability with formatted output and metadata.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class GeminiLogger:
    """Logger for Gemini API interactions with daily rotation."""

    def __init__(self, log_dir: str = None):
        """
        Initialize Gemini logger.

        Args:
            log_dir: Directory for log files. Defaults to logs/gemini/
        """
        if log_dir is None:
            # Default to logs/gemini/ in project root
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / 'logs' / 'gemini'

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self) -> Path:
        """Get current log file path with date-based naming."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.log_dir / f'gemini_interactions_{today}.log'

    def _format_prompt(self, prompt: str, max_length: int = 500) -> str:
        """Format prompt for display, truncating if too long."""
        if len(prompt) <= max_length:
            return prompt
        return prompt[:max_length] + f"\n... [truncated, total length: {len(prompt)} chars]"

    def _format_response(self, response: Any) -> str:
        """Format response for display."""
        if isinstance(response, dict):
            return json.dumps(response, indent=2)
        elif isinstance(response, str):
            try:
                # Try to parse as JSON for pretty printing
                parsed = json.loads(response)
                return json.dumps(parsed, indent=2)
            except:
                return response
        return str(response)

    def log_interaction(
        self,
        operation: str,
        prompt: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a Gemini API interaction.

        Args:
            operation: Type of operation (e.g., 'categorize_email', 'generate_summary')
            prompt: The prompt/request sent to Gemini
            response: The response received from Gemini
            metadata: Optional metadata (model_name, tokens, latency, etc.)
        """
        log_file = self._get_log_file_path()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # Build log entry
        separator = "=" * 100
        entry_parts = [
            f"\n{separator}",
            f"TIMESTAMP: {timestamp}",
            f"OPERATION: {operation}",
        ]

        # Add metadata if provided
        if metadata:
            entry_parts.append("METADATA:")
            for key, value in metadata.items():
                entry_parts.append(f"  - {key}: {value}")

        # Add prompt
        entry_parts.extend([
            f"\n{'REQUEST (Prompt):':-^100}",
            self._format_prompt(prompt),
        ])

        # Add response
        entry_parts.extend([
            f"\n{'RESPONSE:':-^100}",
            self._format_response(response),
        ])

        entry_parts.append(separator)

        # Write to file
        log_entry = "\n".join(entry_parts) + "\n"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            # Fail silently - don't break the main application
            print(f"Warning: Failed to write Gemini log: {e}")

    def get_log_entries(self, date: Optional[str] = None) -> list:
        """
        Get log entries for a specific date or today.

        Args:
            date: Date string in YYYY-MM-DD format. Defaults to today.

        Returns:
            List of log entry dictionaries
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        log_file = self.log_dir / f'gemini_interactions_{date}.log'

        if not log_file.exists():
            return []

        entries = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split by separator
            raw_entries = content.split("=" * 100)

            for raw_entry in raw_entries:
                if not raw_entry.strip():
                    continue

                entry = self._parse_log_entry(raw_entry)
                if entry:
                    entries.append(entry)

        except Exception as e:
            print(f"Error reading Gemini logs: {e}")

        return entries

    def _parse_log_entry(self, raw_entry: str) -> Optional[Dict[str, Any]]:
        """Parse a raw log entry into structured data."""
        try:
            lines = raw_entry.strip().split('\n')

            entry = {
                'timestamp': None,
                'operation': None,
                'metadata': {},
                'request': None,
                'response': None
            }

            current_section = None
            section_content = []

            for line in lines:
                if line.startswith('TIMESTAMP:'):
                    entry['timestamp'] = line.split('TIMESTAMP:', 1)[1].strip()
                elif line.startswith('OPERATION:'):
                    entry['operation'] = line.split('OPERATION:', 1)[1].strip()
                elif line.startswith('METADATA:'):
                    current_section = 'metadata'
                elif 'REQUEST (Prompt):' in line:
                    current_section = 'request'
                    section_content = []
                elif 'RESPONSE:' in line:
                    if current_section == 'request':
                        entry['request'] = '\n'.join(section_content).strip()
                    current_section = 'response'
                    section_content = []
                elif current_section == 'metadata' and line.strip().startswith('- '):
                    # Parse metadata line
                    metadata_line = line.strip()[2:]  # Remove "- "
                    if ':' in metadata_line:
                        key, value = metadata_line.split(':', 1)
                        entry['metadata'][key.strip()] = value.strip()
                elif current_section in ['request', 'response']:
                    section_content.append(line)

            # Save last section
            if current_section == 'response':
                entry['response'] = '\n'.join(section_content).strip()

            return entry if entry['timestamp'] else None

        except Exception as e:
            print(f"Error parsing log entry: {e}")
            return None

    def get_available_dates(self) -> list:
        """Get list of dates that have log files."""
        dates = []
        for log_file in self.log_dir.glob('gemini_interactions_*.log'):
            # Extract date from filename
            date_str = log_file.stem.replace('gemini_interactions_', '')
            dates.append(date_str)
        return sorted(dates, reverse=True)


# Global instance
_gemini_logger = None


def get_gemini_logger() -> GeminiLogger:
    """Get or create the global Gemini logger instance."""
    global _gemini_logger
    if _gemini_logger is None:
        _gemini_logger = GeminiLogger()
    return _gemini_logger
