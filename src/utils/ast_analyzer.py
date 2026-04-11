"""
AST analysis utilities for extracting code structure from Python files.

This module provides functions to:
- Parse Python files and extract AST information
- Build call graphs and identify function/class definitions
- Extract type hints and signatures
- Map line numbers to function/class names
"""

import ast
import re
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class FunctionInfo:
    """Extracted information about a function."""
    name: str
    line_start: int
    line_end: int
    args: List[str]
    arg_types: Dict[str, str]  # arg_name -> type_hint
    return_type: str
    decorators: List[str]
    is_async: bool


@dataclass
class ClassInfo:
    """Extracted information about a class."""
    name: str
    line_start: int
    line_end: int
    base_classes: List[str]
    methods: List[FunctionInfo]
    decorators: List[str]


@dataclass
class CallInfo:
    """A function call from one function to another."""
    caller: str  # full path like "module.ClassName.method" or "module.function"
    callee: str  # same format
    line: int


class ASTAnalyzer(ast.NodeVisitor):
    """
    Visitor that extracts function/class definitions, signatures, and call graphs.
    """
    
    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.source_lines = source_code.splitlines()
        
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.calls: List[CallInfo] = []
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        
    def get_decorator_names(self, node) -> List[str]:
        """Extract decorator names from a function or class."""
        return [
            ast.unparse(dec).split("(")[0] if isinstance(dec, ast.Call) else ast.unparse(dec)
            for dec in node.decorator_list
        ]
    
    def get_arg_info(self, args: ast.arguments) -> Tuple[List[str], Dict[str, str]]:
        """
        Extract argument names and their type hints.
        
        Returns:
            (list of arg names, dict of arg_name -> type_hint)
        """
        arg_names = []
        arg_types = {}
        
        # Regular positional arguments
        for arg in args.args:
            arg_names.append(arg.arg)
            if arg.annotation:
                arg_types[arg.arg] = ast.unparse(arg.annotation)
        
        # *args
        if args.vararg:
            arg_names.append(f"*{args.vararg.arg}")
            if args.vararg.annotation:
                arg_types[args.vararg.arg] = ast.unparse(args.vararg.annotation)
        
        # Keyword-only arguments
        for arg in args.kwonlyargs:
            arg_names.append(arg.arg)
            if arg.annotation:
                arg_types[arg.arg] = ast.unparse(arg.annotation)
        
        # **kwargs
        if args.kwarg:
            arg_names.append(f"**{args.kwarg.arg}")
            if args.kwarg.annotation:
                arg_types[args.kwarg.arg] = ast.unparse(args.kwarg.annotation)
        
        return arg_names, arg_types
    
    def get_return_type(self, node: ast.FunctionDef) -> str:
        """Extract return type annotation."""
        if node.returns:
            return ast.unparse(node.returns)
        return ""
    
    def get_full_name(self, node_name: str) -> str:
        """Get full qualified name (class.method or just function)."""
        if self.current_class:
            return f"{self.current_class}.{node_name}"
        return node_name
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit a function definition."""
        arg_names, arg_types = self.get_arg_info(node.args)
        return_type = self.get_return_type(node)
        
        func_info = FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=arg_names,
            arg_types=arg_types,
            return_type=return_type,
            decorators=self.get_decorator_names(node),
            is_async=False,
        )
        
        full_name = self.get_full_name(node.name)
        self.functions[full_name] = func_info
        
        # Visit function body to find nested functions and calls
        old_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit an async function definition."""
        arg_names, arg_types = self.get_arg_info(node.args)
        return_type = self.get_return_type(node)
        
        func_info = FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=arg_names,
            arg_types=arg_types,
            return_type=return_type,
            decorators=self.get_decorator_names(node),
            is_async=True,
        )
        
        full_name = self.get_full_name(node.name)
        self.functions[full_name] = func_info
        
        old_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit a class definition."""
        base_classes = [ast.unparse(base) for base in node.bases]
        
        old_class = self.current_class
        self.current_class = node.name
        
        # Collect methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_names, arg_types = self.get_arg_info(item.args)
                return_type = self.get_return_type(item)
                is_async = isinstance(item, ast.AsyncFunctionDef)
                
                method_info = FunctionInfo(
                    name=item.name,
                    line_start=item.lineno,
                    line_end=item.end_lineno or item.lineno,
                    args=arg_names,
                    arg_types=arg_types,
                    return_type=return_type,
                    decorators=self.get_decorator_names(item),
                    is_async=is_async,
                )
                methods.append(method_info)
        
        class_info = ClassInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            base_classes=base_classes,
            methods=methods,
            decorators=self.get_decorator_names(node),
        )
        
        self.classes[node.name] = class_info
        
        # Visit body for nested classes and calls
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Call(self, node: ast.Call):
        """Visit a function call to build call graph."""
        if self.current_function:
            callee_name = self._extract_call_name(node.func)
            if callee_name:
                call_info = CallInfo(
                    caller=self.current_function,
                    callee=callee_name,
                    line=node.lineno,
                )
                self.calls.append(call_info)
        
        self.generic_visit(node)
    
    def _extract_call_name(self, node: ast.expr) -> Optional[str]:
        """Extract the name being called from various call expressions."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Example: obj.method -> "method", or Class.method -> "Class.method"
            value = self._extract_call_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        return None
    
    def analyze(self) -> Dict[str, Any]:
        """
        Parse the source code and extract all information.
        
        Returns:
            Dict with keys:
            - 'functions': {name: FunctionInfo dict}
            - 'classes': {name: ClassInfo dict}
            - 'calls': [CallInfo dict list]
            - 'line_to_function': {line_num: function_name}
        """
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError as e:
            return {
                'functions': {},
                'classes': {},
                'calls': [],
                'line_to_function': {},
                'parse_error': str(e),
            }
        
        # Build line-to-function mapping
        line_to_function = {}
        for func_name, func_info in self.functions.items():
            for line in range(func_info.line_start, func_info.line_end + 1):
                line_to_function[line] = func_name
        
        # Also map class definitions
        line_to_function.update({
            line: f"class:{class_name}"
            for class_name, class_info in self.classes.items()
            for line in range(class_info.line_start, class_info.line_end + 1)
        })
        
        return {
            'functions': {k: asdict(v) for k, v in self.functions.items()},
            'classes': {k: asdict(v) for k, v in self.classes.items()},
            'calls': [asdict(c) for c in self.calls],
            'line_to_function': line_to_function,
        }


def parse_diff(diff_str: str) -> Dict[str, List[Tuple[int, int]]]:
    """
    Parse a unified diff to extract file paths and changed line ranges.
    
    Returns:
        Dict mapping file_path -> list of (line_start, line_end) tuples
        for added/modified hunks.
    """
    files = defaultdict(list)
    
    current_file = None
    # Regex to match "@@" hunk headers: @@ -old_start,old_count +new_start,new_count @@
    hunk_pattern = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
    
    for line in diff_str.splitlines():
        # New file marker: +++ b/filename
        if line.startswith('+++'):
            current_file = line[6:]  # Remove '+++ b/'
        # Hunk header
        elif line.startswith('@@'):
            match = hunk_pattern.match(line)
            if match and current_file:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                end = start + count - 1 if count > 0 else start
                files[current_file].append((start, end))
    
    return dict(files)


def extract_changed_functions(
    source_code: str,
    diff_str: str,
    filename: str = "<unknown>",
) -> Dict[str, Any]:
    """
    Analyze code and diff to identify which functions/classes were changed.
    
    Returns:
        {
            'all_functions': {...},
            'all_classes': {...},
            'changed_functions': [names of functions/classes with changes],
            'changed_ranges': [(start, end) tuples],
            'all_calls': [call info],
            'parse_error': str or None,
        }
    """
    analyzer = ASTAnalyzer(source_code, filename)
    ast_info = analyzer.analyze()
    
    if 'parse_error' in ast_info:
        return {
            'all_functions': {},
            'all_classes': {},
            'changed_functions': [],
            'changed_ranges': [],
            'all_calls': [],
            'parse_error': ast_info['parse_error'],
        }
    
    # Parse diff to get changed line ranges
    changed_ranges = parse_diff(diff_str)
    
    # For the current file, identify which functions changed
    changed_functions = set()
    line_to_function = ast_info['line_to_function']
    
    for _, ranges in changed_ranges.items():
        for start, end in ranges:
            for line in range(start, end + 1):
                if line in line_to_function:
                    changed_functions.add(line_to_function[line])
    
    return {
        'all_functions': ast_info['functions'],
        'all_classes': ast_info['classes'],
        'changed_functions': list(changed_functions),
        'changed_ranges': [r for ranges in changed_ranges.values() for r in ranges],
        'all_calls': ast_info['calls'],
        'parse_error': None,
    }
