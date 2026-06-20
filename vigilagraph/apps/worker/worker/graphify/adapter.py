"""GraphifyAdapter — invokes the external graphify CLI via subprocess.

Graphify (https://pypi.org/project/graphifyy/) is installed as an external
CLI tool via `uv tool install graphifyy` and is NOT a Python project dependency.
All interaction happens through subprocess calls.

Enhanced with asyncio.create_subprocess_exec, dataclass input/output,
graph.json parsing, and version detection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GRAPHIFY_CMD = "graphify"


@dataclass
class GraphifyInput:
    """Input parameters for a Graphify run."""
    input_path: str | Path
    output_dir: str | Path
    extra_args: list[str] = field(default_factory=list)
    timeout: int = 600  # 10 minutes default


@dataclass
class GraphifyOutput:
    """Structured output from a Graphify run."""
    returncode: int
    stdout: str = ""
    stderr: str = ""
    json_data: dict | None = None
    error_message: str | None = None
    timed_out: bool = False


class GraphifyAdapter:
    """Wraps the graphify CLI for knowledge-graph extraction.

    Supports both synchronous (``subprocess.run``) and asynchronous
    (``asyncio.create_subprocess_exec``) execution.
    """

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

    async def get_version(self) -> str | None:
        """Return the installed graphify version string, or ``None``."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._command, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode("utf-8").strip()
        except (FileNotFoundError, OSError):
            pass
        return None

    async def run_async(self, params: GraphifyInput) -> GraphifyOutput:
        """Execute graphify asynchronously using ``asyncio.create_subprocess_exec``.

        This is the preferred method for production use (Celery worker).
        """
        if not self.is_available():
            return GraphifyOutput(
                returncode=-1,
                error_message="graphify CLI is not installed. Install it with: uv tool install graphifyy",
            )

        cmd = [
            self._command,
            str(params.input_path),
            "--output-dir", str(params.output_dir),
        ]
        if params.extra_args:
            cmd.extend(params.extra_args)

        logger.info("Running graphify (async): %s", " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=params.timeout,
            )

            stdout_text = stdout.decode("utf-8") if stdout else ""
            stderr_text = stderr.decode("utf-8") if stderr else ""

            if proc.returncode != 0:
                logger.error(
                    "graphify failed (exit=%d): stderr=%s",
                    proc.returncode, stderr_text[:500],
                )
                return GraphifyOutput(
                    returncode=proc.returncode or -1,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    error_message=stderr_text[:2000],
                )

            json_data = self.parse_graph_json(stdout_text)
            return GraphifyOutput(
                returncode=0,
                stdout=stdout_text,
                stderr=stderr_text,
                json_data=json_data,
            )

        except asyncio.TimeoutError:
            if proc:
                proc.kill()
                await proc.wait()
            logger.error("graphify timed out after %d seconds", params.timeout)
            return GraphifyOutput(
                returncode=-1,
                error_message=f"Graphify timed out after {params.timeout} seconds",
                timed_out=True,
            )

    def run_sync(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        *,
        timeout: int = 300,
        extra_args: list[str] | None = None,
    ) -> dict:
        """Execute graphify on *input_path* and write results to *output_dir*.

        Synchronous wrapper using ``subprocess.run``. Kept for backward
        compatibility; prefer ``run_async`` for new code.

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

        import subprocess

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
                result.returncode, result.stderr,
            )
            raise RuntimeError(
                f"graphify exited with code {result.returncode}: {result.stderr}"
            )

        return self.parse_graph_json(result.stdout) or {"raw_output": result.stdout.strip()}

    @staticmethod
    def parse_graph_json(output: str) -> dict | None:
        """Try to parse stdout as JSON; return ``None`` on failure."""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            logger.warning("graphify output is not valid JSON")
            return None
