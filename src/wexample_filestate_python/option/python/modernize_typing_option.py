from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, ClassVar

from wexample_filestate.option.mixin.with_batch_option_mixin import (
    WithBatchOptionMixin,
)
from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from pathlib import Path

    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class ModernizeTypingOption(WithBatchOptionMixin, AbstractPythonFileContentOption):
    """Modernize Python syntax via Ruff's UP rules.

    Replaces the previous pyupgrade-based implementation, which depended on
    pyupgrade's private `_fix_plugins` / `Settings` (unstable across version
    bumps). Ruff is a public, idempotent, Rust-fast equivalent — and is the
    direction the wider ecosystem has converged on.

    Composes with sibling options (RemoveUnusedOption, SortImportsOption,
    FormatOption); those tools keep their scope here. They can be folded into
    Ruff later if we decide to consolidate.
    """

    # Target Python version for Ruff's UP rules. Sets the highest version
    # Ruff is allowed to emit; rectifications never produce syntax newer
    # than this.
    _target_version: ClassVar[str] = "py312"

    def get_description(self) -> str:
        return "Modernize Python syntax (PEP 585/604, …) using Ruff's UP rules."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        cache = self._get_or_build_batch_cache(target)
        path_key = str(target.get_path())
        if path_key in cache:
            return cache[path_key]
        return target.read_text()

    def _run_batch_on_paths(
        self,
        reference_target: TargetFileOrDirectoryType,
        paths: list[Path],
    ) -> None:
        # Invoke Ruff via `python -m ruff` so we always use the binary from
        # the same env as the running Python — no PATH-activation dependency.
        # `--fix-only` makes Ruff exit 0 even when unfixable findings remain:
        # this option's job is to *apply* UP fixes, not to report on lint
        # findings (that would belong to a dedicated lint rule).
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select=UP",
            "--fix",
            "--fix-only",
            f"--target-version={self._target_version}",
            "--no-cache",
            *[str(p) for p in paths],
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"ruff (modernize_typing) exited with code {result.returncode}\n"
                f"stderr: {result.stderr.strip()}\n"
                f"stdout: {result.stdout.strip()}"
            )
