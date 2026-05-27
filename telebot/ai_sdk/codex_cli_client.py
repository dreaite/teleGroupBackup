import asyncio
import contextlib
import logging
import shlex
import tempfile
from pathlib import Path

from .base import AIProvider
from .prompts import DEFAULT_SUMMARY_PROMPT


class CodexCLIClient(AIProvider):
    """AI provider that delegates summary generation to the local Codex CLI."""

    def __init__(
        self,
        command: str | list[str] = "codex",
        model: str | None = None,
        profile: str | None = None,
        working_dir: str | None = None,
        timeout_seconds: int = 900,
        sandbox: str = "read-only",
        approval_policy: str | None = None,
        ephemeral: bool = True,
        skip_git_repo_check: bool = True,
        extra_args: list[str] | str | None = None,
    ):
        self.command = self._parse_command(command)
        self.model = model
        self.profile = profile
        self.working_dir = Path(working_dir).expanduser() if working_dir else None
        self.timeout_seconds = max(1, int(timeout_seconds or 900))
        self.sandbox = sandbox
        self.approval_policy = approval_policy
        self.ephemeral = bool(ephemeral)
        self.skip_git_repo_check = bool(skip_git_repo_check)
        self.extra_args = self._parse_extra_args(extra_args)
        self.logger = logging.getLogger(__name__)

    async def generate_summary(self, content: str, prompt: str | None = None) -> str:
        """Run `codex exec` once and return its final response as the summary."""
        if not content.strip():
            return ""

        output_path = self._create_output_path()
        proc = None
        try:
            args = self._build_args(output_path)
            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=str(self.working_dir) if self.working_dir else None,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(self._build_prompt(content, prompt).encode("utf-8")),
                timeout=self.timeout_seconds,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                self.logger.error(
                    "Codex CLI summary failed with code %s. stderr=%s stdout=%s",
                    proc.returncode,
                    stderr,
                    stdout,
                )
                detail = self._trim_error(stderr or stdout)
                return f"Error generating summary: Codex CLI exited with code {proc.returncode}: {detail}"

            if stderr:
                self.logger.debug("Codex CLI summary stderr: %s", stderr)

            summary = self._read_output(output_path) or stdout
            if not summary.strip():
                return "Error generating summary: Codex CLI returned empty output"

            return summary.strip()
        except FileNotFoundError:
            command = " ".join(self.command)
            self.logger.error("Codex CLI command not found: %s", command)
            return f"Error generating summary: Codex CLI command not found: {command}"
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                await self._kill_process(proc)
            return f"Error generating summary: Codex CLI timed out after {self.timeout_seconds} seconds"
        except asyncio.CancelledError:
            if proc and proc.returncode is None:
                await self._kill_process(proc)
            raise
        except Exception as e:
            self.logger.error("Codex CLI summary failed: %s", e, exc_info=True)
            return f"Error generating summary: {e}"
        finally:
            with contextlib.suppress(OSError):
                Path(output_path).unlink()

    def _build_args(self, output_path: str) -> list[str]:
        args = [*self.command, "exec"]

        if self.model:
            args.extend(["--model", self.model])
        if self.profile:
            args.extend(["--profile", self.profile])
        if self.sandbox:
            args.extend(["--sandbox", self.sandbox])
        if self.approval_policy:
            args.extend(["--ask-for-approval", self.approval_policy])
        if self.skip_git_repo_check:
            args.append("--skip-git-repo-check")
        if self.ephemeral:
            args.append("--ephemeral")

        args.extend(self.extra_args)
        args.extend(["--output-last-message", output_path, "-"])
        return args

    def _build_prompt(self, content: str, prompt: str | None) -> str:
        system_prompt = prompt if prompt else DEFAULT_SUMMARY_PROMPT
        return (
            f"{system_prompt}\n\n"
            "You are running inside Codex CLI as a non-interactive summarizer. "
            "Do not inspect local files, run commands, or modify anything. "
            "Use only the Telegram chat log inside <telegram_chat_log>.\n"
            "Return only the final summary text, with no preface, no code fences, and no status updates.\n\n"
            "<telegram_chat_log>\n"
            f"{content}\n"
            "</telegram_chat_log>"
        )

    def _create_output_path(self) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="codex_summary_",
            suffix=".txt",
            delete=False,
        ) as fp:
            return fp.name

    def _read_output(self, output_path: str) -> str:
        with contextlib.suppress(OSError, UnicodeDecodeError):
            return Path(output_path).read_text(encoding="utf-8").strip()
        return ""

    def _parse_command(self, command: str | list[str]) -> list[str]:
        if isinstance(command, list):
            parsed = [str(part) for part in command if str(part)]
        else:
            parsed = shlex.split(str(command))

        return parsed or ["codex"]

    def _parse_extra_args(self, extra_args: list[str] | str | None) -> list[str]:
        if extra_args is None:
            return []
        if isinstance(extra_args, str):
            return shlex.split(extra_args)
        return [str(arg) for arg in extra_args if str(arg)]

    def _trim_error(self, text: str, limit: int = 1000) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "...[truncated]"

    async def _kill_process(self, proc: asyncio.subprocess.Process) -> None:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()
