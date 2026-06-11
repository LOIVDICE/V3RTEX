"""
Extraction Rules
This script defines what rules to extract from the AST.
Arranged by file type/language
Constructed as clases to avoid duplication and to make it easy to add new rules.

Input: None
Output: A list of classes, each containing a list of rules
"""

class BaseRules:
    def __init__(self):
        # Initialize with empty lists for all wanted categories
        self.rules = {
            "imports": [],
            "exports": [],
            "classes": [],
            "functions": [],
            "methods": [],
            "parameters": [],
            "return_types": [],
            "base_classes": [],
            "variables": [],
            "function_calls": [],
            "comments": [],
            "docstrings": [],
            "jsx_elements": [],
            "types": [],
            "interfaces": [],
            "decorators": [],
            "generators": [],
            "entry_points": [],
            "async_functions": [],
            "tests": [],
            "dunder_methods": [],
            "properties": [],
            "react_components": [],
            "hooks": [],
            "arrow_functions": [],
            "dynamic_imports": [],
            "require_imports": [],
            "conditional_imports": [],
            "try_blocks": [],
            "conditionals": [],
            "loops": [],
            "loop_controls": [],
            "syntax_errors": [],
            "module_metadata": [],
        }
        # These categories can be matched directly while walking the tree.
        # Other categories, like parameters/docstrings/return_types, need context
        # and are extracted from inside functions/classes/imports later.
        self.direct_extract_categories = [
            "imports",
            "exports",
            "classes",
            "functions",
            "methods",
            "variables",
            "function_calls",
            "comments",
            "jsx_elements",
            "types",
            "interfaces",
            "decorators",
            "generators",
            "try_blocks",
            "conditionals",
            "loops",
            "loop_controls",
            "syntax_errors",
            "module_metadata",
        ]

    def get_rules(self):
        return self.rules

    def get_direct_rules(self):
        return {
            category: self.rules[category]
            for category in self.direct_extract_categories
        }


class PythonRules(BaseRules):
    def __init__(self):
        super().__init__()
        self.rules.update({
            "imports": [
                "import_statement",        # import os
                "import_from_statement",   # from x import y
                "future_import_statement", # from __future__ import annotations
            ],
            "classes": ["class_definition"],
            "functions": [
                "function_definition",       # def foo():
                "async_function_definition", # async def foo(): — DIFFERENT NODE TYPE
                "lambda",                    # lambda x: x + 1
            ],
            "methods": [
                # Same node types as functions.
                # Distinction is made at extraction time by checking parent node.
                # If parent.type == "class_definition" → it is a method.
                "function_definition",
                "async_function_definition",
            ],
            "parameters": [
                "parameters",
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
                "list_splat_pattern",
                "dictionary_splat_pattern",
            ],
            "return_types": [
                # Return annotation is read from the function_definition return_type field.
                # The child node can vary, so extraction should use the field name.
                "type",
                "identifier",
                "subscript",
            ],
            "base_classes": [
                # Class bases are read from the class_definition superclasses field.
                "argument_list",
                "identifier",
                "attribute",
            ],
            "variables": [
                "assignment",            # x = 5
                "augmented_assignment",  # x += 1
                "annotated_assignment",  # x: int = 5  ← was missing
            ],
            "function_calls": ["call"],
            "comments": ["comment"],
            # NOTE: docstrings are NOT comment nodes.
            # They are string nodes as the first child of a function/class body.
            # Handle separately at extraction time.
            "docstrings": [
                "string",
                "string_content",
            ],
            "decorators": ["decorator"],
            "generators": [
                # Detected as yield_statement inside a function body.
                # Set is_generator = True on the parent function node.
                # Not a separate extraction category — a flag on the function.
                "yield_statement",
                "yield",
            ],
            "entry_points": [
                # Detect if __name__ == "__main__" and decorated API/CLI handlers.
                "if_statement",
                "comparison_operator",
                "decorated_definition",
                "decorator",
            ],
            "async_functions": ["async_function_definition"],
            "tests": [
                # Final test detection is by function name: test_*, *_test, spec_*.
                "function_definition",
                "async_function_definition",
            ],
            "dunder_methods": [
                # Final dunder detection is by method name: __init__, __str__, etc.
                "function_definition",
                "async_function_definition",
            ],
            "properties": [
                # Detect @property by reading decorator names.
                "decorator",
                "decorated_definition",
            ],
            "dynamic_imports": [
                # Detect importlib.import_module(...) and __import__(...) calls.
                "call",
            ],
            "conditional_imports": [
                "if_statement",
                "try_statement",
            ],
            "try_blocks": ["try_statement"],
            "conditionals": [
                "if_statement",
                "conditional_expression",
                "match_statement",
            ],
            "loops": [
                "for_statement",
                "while_statement",
            ],
            "loop_controls": [
                "break_statement",
                "continue_statement",
            ],
            "syntax_errors": ["ERROR"],
            "module_metadata": [
                # Line counts, encoding, and language are computed outside the AST.
                "module",
            ],
        })


class JavaScriptRules(BaseRules):
    def __init__(self):
        super().__init__()
        self.rules.update({
            "imports": [
                "import_statement",         # import x from 'y'
                # NOTE: CommonJS require() is a call_expression with callee "require"
                # Handle it as a special case inside function_calls extraction,
                # not as a separate import node type.
            ],
            "exports": [
                "export_statement",         # export function foo() / export default
                # export_declaration does NOT exist in tree-sitter-javascript
            ],
            "classes": [
                "class_declaration",        # class Foo {}
                "class",                    # const Foo = class {}
            ],
            "functions": [
                "function_declaration",           # function foo() {}
                "function_expression",            # const foo = function() {}  ← was missing
                "arrow_function",                 # const foo = () => {}
                "generator_function_declaration", # function* foo() {}  ← was missing
                "generator_function",             # const foo = function*() {}
            ],
            "methods": [
                "method_definition",          # class methods
                # public_field_definition is a class field, not necessarily a method
                # Only flag as method if it contains a function_expression or arrow_function
            ],
            "parameters": [
                "formal_parameters",
                "identifier",
                "assignment_pattern",
                "rest_pattern",
                "object_pattern",
                "array_pattern",
            ],
            "base_classes": [
                "class_heritage",
                "identifier",
                "member_expression",
            ],
            "variables": [
                "lexical_declaration",     # const x / let x
                "variable_declaration",    # var x
            ],
            "function_calls": ["call_expression"],
            "comments": ["comment"],
            "jsx_elements": [
                "jsx_element",              # <div>...</div>
                "jsx_self_closing_element", # <img />
                "jsx_fragment",             # <></>
            ],
            "generators": ["yield_expression"],
            "entry_points": [
                # Detect framework handlers, event handlers, and main/module entry logic.
                "call_expression",
                "if_statement",
                "export_statement",
            ],
            "async_functions": [
                # Async is a modifier on these nodes, checked during extraction.
                "function_declaration",
                "function_expression",
                "arrow_function",
                "method_definition",
            ],
            "tests": [
                # Detect test(), it(), describe(), and function names matching test patterns.
                "call_expression",
                "function_declaration",
                "function_expression",
                "arrow_function",
            ],
            "properties": [
                "public_field_definition",
                "method_definition",
            ],
            "react_components": [
                # Final detection also checks capitalized name and JSX return/body.
                "function_declaration",
                "function_expression",
                "arrow_function",
                "jsx_element",
                "jsx_self_closing_element",
                "jsx_fragment",
            ],
            "hooks": [
                # Final hook detection is by name: useSomething.
                "function_declaration",
                "function_expression",
                "arrow_function",
                "call_expression",
            ],
            "arrow_functions": ["arrow_function"],
            "dynamic_imports": [
                # Detect import("./module") as a call_expression.
                "call_expression",
            ],
            "require_imports": [
                # Detect const x = require("./module") as a call_expression.
                "call_expression",
            ],
            "conditional_imports": [
                "if_statement",
                "try_statement",
                "conditional_expression",
            ],
            "try_blocks": ["try_statement"],
            "conditionals": [
                "if_statement",
                "ternary_expression",
                "switch_statement",
            ],
            "loops": [
                "for_statement",
                "for_in_statement",
                "for_of_statement",
                "while_statement",
                "do_statement",
            ],
            "loop_controls": [
                "break_statement",
                "continue_statement",
            ],
            "syntax_errors": ["ERROR"],
            "module_metadata": [
                # Line counts, encoding, and language are computed outside the AST.
                "program",
            ],
        })


class TypeScriptRules(JavaScriptRules):
    def __init__(self):
        super().__init__()
        self.rules.update({
            "types": [
                "type_alias_declaration",  # type UserId = string
                "enum_declaration",        # enum Direction { Up, Down }
            ],
            "interfaces": [
                "interface_declaration",   # interface User { name: string }
            ],
            "decorators": ["decorator"],
        })
        self.rules["classes"].append("abstract_class_declaration")  # abstract class Animal {}
        self.rules["parameters"].extend([
            "required_parameter",
            "optional_parameter",
        ])
        self.rules["return_types"].extend([
            "type_annotation",
        ])