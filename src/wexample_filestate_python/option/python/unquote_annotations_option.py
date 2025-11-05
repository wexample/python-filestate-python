from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class

from .abstract_python_file_content_option import AbstractPythonFileContentOption

if TYPE_CHECKING:
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


@base_class
class UnquoteAnnotationsOption(AbstractPythonFileContentOption):
    def get_description(self) -> str:
        return "Unquote type annotations (arguments, returns, variables) using LibCST."

    def _apply_content_change(self, target: TargetFileOrDirectoryType) -> str:
        """Remove quotes around type annotations by turning stringized annotations back into expressions."""
        import json

        import libcst as cst

        src = target.get_local_file().read()

        class _Unquoter(cst.CSTTransformer):
            @staticmethod
            def _unquote_expr(s: cst.SimpleString) -> cst.BaseExpression | None:
                try:
                    code = json.loads(s.value)
                except Exception:
                    return None
                try:
                    return cst.parse_expression(code)
                except Exception:
                    return None

            @staticmethod
            def _process_annotation(
                ann: cst.Annotation | None,
            ) -> cst.Annotation | None:
                if ann is None:
                    return None
                node = ann.annotation
                if isinstance(node, cst.SimpleString):
                    expr = _Unquoter._unquote_expr(node)
                    if expr is not None:
                        return cst.Annotation(annotation=expr)
                return ann

            def leave_Param(
                self, original_node: cst.Param, updated_node: cst.Param
            ) -> cst.Param:
                return updated_node.with_changes(
                    annotation=self._process_annotation(updated_node.annotation)
                )

            def leave_FunctionDef(
                self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
            ) -> cst.FunctionDef:
                return updated_node.with_changes(
                    returns=self._process_annotation(updated_node.returns)
                )

            def leave_AnnAssign(
                self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
            ) -> cst.AnnAssign:
                return updated_node.with_changes(
                    annotation=self._process_annotation(updated_node.annotation)
                )

            def leave_TypeAlias(
                self, original_node: cst.TypeAlias, updated_node: cst.TypeAlias
            ) -> cst.TypeAlias:
                # Python 3.12 'type X = ...' syntax
                ann = updated_node.annotation
                if isinstance(ann, cst.SimpleString):
                    expr = self._unquote_expr(ann)
                    if expr is not None:
                        return updated_node.with_changes(annotation=expr)
                return updated_node

        module = cst.parse_module(src)
        new_mod = module.visit(_Unquoter())
        return new_mod.code
