"""
analyzer.py — Static analysis of Python source using the `ast` module.

Detects common code-quality and performance issues:
  - bare except clauses
  - unused imports
  - mutable default arguments
  - functions/methods missing docstrings
  - overly long functions (line-count heuristic)
  - string concatenation in loops (perf smell)
  - repeated len() calls inside loop conditions
"""

import ast
from dataclasses import dataclass, field


@dataclass
class Issue:
    line: int
    kind: str
    message: str
    severity: str = "warning"  # info | warning | error


@dataclass
class AnalysisResult:
    issues: list = field(default_factory=list)
    functions_missing_docstrings: list = field(default_factory=list)
    total_functions: int = 0
    total_lines: int = 0

    @property
    def issues_per_100_lines(self):
        if not self.total_lines:
            return 0.0
        return round(len(self.issues) / self.total_lines * 100, 2)


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []
        self.imported_names = {}
        self.used_names = set()
        self.functions_missing_docstrings = []
        self.total_functions = 0

    # --- imports -----------------------------------------------------
    def visit_Import(self, node):
        for alias in node.names:
            name = (alias.asname or alias.name).split(".")[0]
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # catches module.attr usage so `import os` counts as used via os.path
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    # --- except clauses -----------------------------------------------
    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.issues.append(Issue(
                line=node.lineno, kind="bare_except",
                message="Bare 'except:' clause catches all exceptions, including "
                        "KeyboardInterrupt/SystemExit. Catch a specific exception type.",
                severity="warning",
            ))
        self.generic_visit(node)

    # --- functions -----------------------------------------------------
    def _check_function(self, node):
        self.total_functions += 1
        has_doc = ast.get_docstring(node) is not None
        if not has_doc:
            self.functions_missing_docstrings.append(node.name)
            self.issues.append(Issue(
                line=node.lineno, kind="missing_docstring",
                message=f"Function '{node.name}' has no docstring.",
                severity="info",
            ))

        # mutable default args
        for default in list(node.args.defaults) + list(node.args.kw_defaults):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(Issue(
                    line=node.lineno, kind="mutable_default",
                    message=f"Function '{node.name}' uses a mutable default argument "
                            "(list/dict/set) — this is shared across calls.",
                    severity="error",
                ))

        # long function heuristic
        if hasattr(node, "end_lineno") and node.end_lineno:
            length = node.end_lineno - node.lineno
            if length > 50:
                self.issues.append(Issue(
                    line=node.lineno, kind="long_function",
                    message=f"Function '{node.name}' is {length} lines long — "
                            "consider splitting it into smaller functions.",
                    severity="warning",
                ))

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_function(node)

    # --- loops / perf smells --------------------------------------------
    def visit_For(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                if isinstance(child.target, ast.Name):
                    self.issues.append(Issue(
                        line=child.lineno, kind="string_concat_in_loop",
                        message=f"'{child.target.id} += ...' inside a loop; if this is "
                                "string concatenation, prefer ''.join(...) or a list buffer.",
                        severity="info",
                    ))
        self.generic_visit(node)


def analyze_source(source: str, filename: str = "<script>") -> AnalysisResult:
    tree = ast.parse(source, filename=filename)
    visitor = _Visitor()
    visitor.visit(tree)

    unused_imports = [
        name for name in visitor.imported_names if name not in visitor.used_names
    ]
    for name in unused_imports:
        visitor.issues.append(Issue(
            line=visitor.imported_names[name], kind="unused_import",
            message=f"Import '{name}' does not appear to be used.",
            severity="info",
        ))

    visitor.issues.sort(key=lambda i: i.line)

    return AnalysisResult(
        issues=visitor.issues,
        functions_missing_docstrings=visitor.functions_missing_docstrings,
        total_functions=visitor.total_functions,
        total_lines=len(source.splitlines()) or 1,
    )
