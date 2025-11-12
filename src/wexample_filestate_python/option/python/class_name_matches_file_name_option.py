from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from wexample_config.config_option.abstract_config_option import AbstractConfigOption
from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.option.mixin.option_mixin import OptionMixin
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class ClassNameMatchesFileNameOption(OptionMixin, AbstractConfigOption):
    @staticmethod
    def _expected_class_name_from_path(path: Path) -> str | None:
        stem = path.stem
        if not stem or stem == "__init__":
            return None

        cleaned = stem.replace("-", "_")
        parts = [part for part in cleaned.split("_") if part]
        if not parts:
            return None

        def normalize(part: str) -> str:
            head, tail = part[:1], part[1:]
            return head.upper() + tail.lower()

        return "".join(normalize(part) for part in parts)

    def create_required_operation(
        self, target: TargetFileOrDirectoryType, scopes: set[Scope]
    ) -> AbstractOperation | None:
        del scopes  # unused

        if not self._class_name_matches_file_name(target=target):
            # TODO
            print(f" CORRECT {target.get_path()}")

        return None

    def get_description(self) -> str:
        return "File name should be a pascal-case version of the class name"

    def _class_name_matches_file_name(self, target: TargetFileOrDirectoryType) -> bool:
        expected_name = self._expected_class_name_from_path(path=target.get_path())

        if expected_name is None:
            return False

        source = target.get_local_file().read()
        try:
            module = ast.parse(source)
        except SyntaxError:
            return False

        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == expected_name:
                return True
        return False
