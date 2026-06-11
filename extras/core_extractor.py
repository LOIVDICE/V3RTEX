"""
Core AST Extractor (Service Class Redesign)
This class encapsulates the state and logic for extracting meaningful data from 
source code ASTs across multiple languages.
"""

import os
from pathlib import Path
from ast_Parser import ASTParser
from extraction_Rules import PythonRules, JavaScriptRules, TypeScriptRules

class ASTExtractor:
    """
    A service-oriented extractor that processes a file's AST based on language-specific rules.
    """

    _RULES_MAP = {
        '.py': PythonRules(),
        '.js': JavaScriptRules(),
        '.jsx': JavaScriptRules(),
        '.ts': TypeScriptRules(),
        '.tsx': TypeScriptRules(),
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.extension = os.path.splitext(file_path)[1].lower()
        
        # 1. Initialize Parser and Source
        self.parser = ASTParser()
        self.tree = self.parser.parse_file(file_path)
        self.source_code = Path(file_path).read_bytes()

        # 2. Configure Rules
        if self.extension not in self._RULES_MAP:
            raise ValueError(f"Unsupported file extension: {self.extension}")
        
        self.rule_engine = self._RULES_MAP[self.extension]
        self.node_type_index = self._build_node_type_index(self.rule_engine.get_direct_rules())
        
        # 3. Initialize Results State
        self.extracted_data = {
            category: [] for category in self.rule_engine.get_rules()
        }

        # Map categories to their specific extraction methods
        self._category_methods = {
            "functions": self._extract_function,
            "methods": self._extract_function,
            "classes": self._extract_class,
            "function_calls": self._extract_call,
            "variables": self._extract_variable,
            "conditionals": self._extract_control_flow,
            "loops": self._extract_control_flow,
            "loop_controls": self._extract_control_flow,
            "try_blocks": self._extract_control_flow,
            "module_metadata": self._extract_module_metadata,
        }

        # Map categories to their specific filter methods
        self._category_filters = {
            "functions": self._should_extract_function,
            "methods": self._should_extract_method,
            "variables": self._should_extract_variable,
        }

    # --- Configuration Helpers ---

    def _build_node_type_index(self, direct_rules):
        index = {}
        for category, node_types in direct_rules.items():
            for n_type in node_types:
                index.setdefault(n_type, []).append(category)
        return index

    # --- Core Extraction Loop ---

    def run(self):
        """Starts the extraction process and returns the results."""
        self._walk(self.tree.root_node, [])
        return self.extracted_data

    def _walk(self, node, ancestors):
        if node.is_named and node.type in self.node_type_index:
            for category in self.node_type_index[node.type]:
                if self._should_extract(node, category, ancestors):
                    record = self._extract_node(node, category, ancestors)
                    self.extracted_data[category].append(record)

        # Recurse
        next_ancestors = ancestors + [node]
        for child in node.children:
            self._walk(child, next_ancestors)

    # --- Logic: Filters ---

    def _should_extract(self, node, category, ancestors):
        filter_func = self._category_filters.get(category)
        return filter_func(node, ancestors) if filter_func else True

    def _should_extract_function(self, node, ancestors):
        return self._get_nearest_scope_type(ancestors) not in {
            "class_definition", "class_declaration", "abstract_class_declaration"
        }

    def _should_extract_method(self, node, ancestors):
        return node.type == "method_definition" or self._get_nearest_scope_type(ancestors) in {
            "class_definition", "class_declaration", "abstract_class_declaration"
        }

    def _should_extract_variable(self, node, ancestors):
        blocked = {
            "function_definition", "async_function_definition", "function_declaration",
            "function_expression", "arrow_function", "method_definition", "class_definition"
        }
        return not any(a.type in blocked for a in ancestors)

    # --- Logic: Extraction Methods ---

    def _extract_node(self, node, category, ancestors):
        extractor = self._category_methods.get(category)
        if extractor:
            return extractor(node, category, ancestors)
        return self._build_base_record(node, category)

    def _extract_function(self, node, category, ancestors):
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        ret_node = node.child_by_field_name("return_type")
        
        name = self._get_node_text(name_node)
        is_anon = name is None

        if is_anon:
            name = self._generate_anonymous_id(node, ancestors)

        record = self._build_base_record(node, category)
        record.update({
            "name": name,
            "qualified_name": self._get_qualified_name(name, ancestors),
            "parameters": self._get_node_text(params_node),
            "return_type": self._get_node_text(ret_node),
            "type_annotations": self._get_signature_annotations(params_node, ret_node),
            "decorators": self._get_decorators(ancestors, node),
            "docstring": self._get_docstring(node),
            "is_anonymous": is_anon,
            "is_async": "async" in (self._get_node_text(node) or "").splitlines()[0],
        })
        return record

    def _extract_class(self, node, category, ancestors):
        name = self._get_node_text(node.child_by_field_name("name"))
        super_node = node.child_by_field_name("superclasses") or \
                     self._find_child_by_type(node, "class_heritage")

        record = self._build_base_record(node, category)
        record.update({
            "name": name,
            "qualified_name": self._get_qualified_name(name, ancestors),
            "base_classes": self._get_node_text(super_node),
            "decorators": self._get_decorators(ancestors, node),
            "docstring": self._get_docstring(node),
        })
        return record

    def _extract_call(self, node, category, ancestors):
        record = self._build_base_record(node, category)
        record.update({
            "callee_name": self._get_node_text(node.child_by_field_name("function")),
            "is_inside_interpolated_string": self._is_interpolated(ancestors),
        })
        return record

    def _extract_variable(self, node, category, ancestors):
        record = self._build_base_record(node, category)
        record.update({
            "name": self._get_node_text(node.child_by_field_name("left")),
            "type_annotations": self._get_descendant_annotations(node),
        })
        return record

    def _extract_control_flow(self, node, category, ancestors):
        loop_types = {"for_statement", "while_statement", "do_statement"}
        func_types = {"function_definition", "method_definition", "arrow_function"}
        
        record = self._build_base_record(node, category)
        record.update({
            "is_nested": any(a.type in loop_types for a in ancestors),
            "is_inside_function": any(a.type in func_types for a in ancestors),
        })
        return record

    def _extract_module_metadata(self, node, category, ancestors):
        record = self._build_base_record(node, category)
        text = self.source_code.decode("utf-8", errors="replace")
        record.update({
            "total_line_count": len(text.splitlines()),
            "has_syntax_errors": "ERROR" in (self._get_node_text(node) or ""),
        })
        return record

    # --- Utility Helpers (The "Service" layer) ---

    def _build_base_record(self, node, category):
        return {
            "category": category,
            "node_type": node.type,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "text": self._get_node_text(node),
        }

    def _get_node_text(self, node):
        if not node: return None
        return self.source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _get_qualified_name(self, name, ancestors):
        scope_types = {"class_definition", "function_definition", "method_definition", "lambda"}
        path = []
        for a in ancestors:
            if a.type in scope_types:
                a_name = self._get_node_text(a.child_by_field_name("name")) or "<anon>"
                path.append(a_name)
        
        if not name: return ".".join(path) if path else None
        return ".".join(path + [name])

    def _get_docstring(self, node):
        body = node.child_by_field_name("body") or self._find_child_by_type(node, "block")
        if not body or not body.children: return None
        
        first = body.children[0]
        if first.type == "expression_statement":
            str_node = self._find_child_by_type(first, "string")
            return self._get_node_text(str_node)
        return self._get_node_text(first) if first.type == "string" else None

    def _get_decorators(self, ancestors, node):
        for a in reversed(ancestors):
            if a.type == "decorated_definition":
                return [self._get_node_text(c) for c in a.children if c.type == "decorator"]
        return []

    def _get_signature_annotations(self, params, ret):
        ann_types = {"type", "type_annotation", "return_type"}
        results = []
        for n in [params, ret]:
            if n:
                results.extend([self._get_node_text(d) for d in self._find_descendants(n, ann_types)])
        return list(set(filter(None, results)))

    def _get_descendant_annotations(self, node):
        ann_types = {"type", "type_annotation"}
        return [self._get_node_text(d) for d in self._find_descendants(node, ann_types)]

    def _generate_anonymous_id(self, node, ancestors):
        # Look for assignment name
        for a in reversed(ancestors):
            left = a.child_by_field_name("left") or a.child_by_field_name("name")
            if left: return self._get_node_text(left)
        return f"<anon>@{node.start_point[0] + 1}:{node.start_point[1]}"

    def _get_nearest_scope_type(self, ancestors):
        scope_types = {"class_definition", "function_definition", "method_definition"}
        for a in reversed(ancestors):
            if a.type in scope_types: return a.type
        return None

    def _find_child_by_type(self, node, n_type):
        for c in node.children:
            if c.type == n_type: return c
        return None

    def _find_descendants(self, node, types):
        matches = [node] if node.type in types else []
        for c in node.children:
            matches.extend(self._find_descendants(c, types))
        return matches

    def _is_interpolated(self, ancestors):
        interp = {"interpolation", "template_substitution", "template_string"}
        return any(a.type in interp for a in ancestors)


if __name__ == "__main__":
    # Example Usage:
    # extractor = ASTExtractor("path/to/file.py")
    # data = extractor.run()
    # print(data['functions'])
    pass