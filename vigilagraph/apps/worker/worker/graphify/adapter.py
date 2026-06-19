"""GraphifyAdapter — invokes the external graphify CLI via subprocess.

Graphify (https://pypi.org/project/graphifyy/) is installed as an external
CLI tool via `uv tool install graphifyy` and is NOT a Python project dependency.
All interaction happens through subprocess calls.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_GRAPHIFY_CMD = "graphify"


class GraphifyAdapter:
    """Wraps the graphify CLI for knowledge-graph extraction."""

    def __init__(self, command: str = DEFAULT_GRAPHIFY_CMD) -> None:
        self._command = self._resolve_command(command)

    @staticmethod
    def _resolve_command(command: str) -> str:
        """Return the full path to the command, or the command name if found in PATH."""
        resolved = shutil.which(command)
        if resolved is None:
            logger.warning("graphify CLI not found in PATH; using '%s' as-is", command)
            return command
        return resolved

    def is_available(self) -> bool:
        """Check whether the graphify CLI is installed and reachable."""
        return shutil.which(self._command) is not None

    def run(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        *,
        timeout: int = 300,
        extra_args: list[str] | None = None,
    ) -> dict:
        """Execute graphify on *input_path* and write results to *output_dir*.

        Args:
            input_path: File or directory to analyse.
            output_dir: Directory where graphify will write its output.
            timeout: Subprocess timeout in seconds (default 300).
            extra_args: Additional CLI flags to pass through.

        Returns:
            Parsed JSON output from graphify.

        Raises:
            FileNotFoundError: If graphify is not installed.
            subprocess.TimeoutExpired: If the command exceeds *timeout*.
            ValueError: If the output cannot be parsed as JSON.
        """
        if not self.is_available():
            msg = (
                "graphify CLI is not installed. "
                "Install it with: uv tool install graphifyy"
            )
            raise FileNotFoundError(msg)

        cmd = [
            self._command,
            str(input_path),
            "--output-dir", str(output_dir),
        ]
        if extra_args:
            cmd.extend(extra_args)

        logger.info("Running graphify: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(
                "graphify failed (exit=%d): stderr=%s",
                result.returncode,
                result.stderr,
            )
            raise RuntimeError(
                f"graphify exited with code {result.returncode}: {result.stderr}"
            )

        # Try to parse stdout as JSON; fall back to returning raw output.
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("graphify output is not JSON; returning raw text")
            return {"raw_output": result.stdout.strip()}
