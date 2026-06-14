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

        from wexample_filestate_python.utils.cst_cache import (
            get_python_source_and_module,
        )

        src, module = get_python_source_and_module(target)

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
                new_ann = self._process_annotation(updated_node.annotation)
                if new_ann is updated_node.annotation:
                    return updated_node
                return updated_node.with_changes(annotation=new_ann)

            def leave_FunctionDef(
                self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
            ) -> cst.FunctionDef:
                new_ret = self._process_annotation(updated_node.returns)
                if new_ret is updated_node.returns:
                    return updated_node
                return updated_node.with_changes(returns=new_ret)

            def leave_AnnAssign(
                self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
            ) -> cst.AnnAssign:
                new_ann = self._process_annotation(updated_node.annotation)
                if new_ann is updated_node.annotation:
                    return updated_node
                return updated_node.with_changes(annotation=new_ann)

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

        new_mod = module.visit(_Unquoter())
        return new_mod.code
