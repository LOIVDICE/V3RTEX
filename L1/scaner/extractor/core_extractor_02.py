"""
Object-Oriented AST Extractor
This version instantiates Node objects from objects.py, separating common 
structural properties from node-specific metadata.
"""

import os
from pathlib import Path
from .ast_Parser import ASTParser
from .extraction_Rules import PythonRules, JavaScriptRules, TypeScriptRules
from compBlocs12 import Node

class ObjectASTExtractor:
    """
    A service that traverses a file and produces a collection of Node objects.
    """

    _RULES_MAP = {
        '.py': PythonRules(),
        '.js': JavaScriptRules(),
        '.jsx': JavaScriptRules(),
        '.ts': TypeScriptRules(),
        '.tsx': TypeScriptRules(),
    }

    def __init__(self, file_path, relative_path):
        self.file_path = file_path
        self.relative_path = relative_path
        self.extension = os.path.splitext(file_path)[1].lower()
        
        # 1. Resource Initialization
        self.parser = ASTParser()
        self.tree = self.parser.parse_file(file_path)
        self.source_code = Path(file_path).read_bytes()

        # 2. Ruleset Configuration
        if self.extension not in self._RULES_MAP:
            raise ValueError(f"Unsupported extension: {self.extension}")
        
        self.rule_engine = self._RULES_MAP[self.extension]
        self.node_type_index = self._build_node_type_index(self.rule_engine.get_direct_rules())
        
        # 3. State Management
        self.extracted_nodes = [] # Flat list of all extracted Node objects
        
        # Internal mapping for specific extraction logic
        self._extractors = {
            "imports":        self._extract_import_data,
            "exports":        self._extract_export_data,
            "functions":      self._extract_function_data,
            "methods":        self._extract_function_data,
            "classes":        self._extract_class_data,
            "function_calls": self._extract_call_data,
            "variables":      self._extract_variable_data,
        }

    def _build_node_type_index(self, direct_rules):
        index = {}
        for category, node_types in direct_rules.items():
            for n_type in node_types:
                index.setdefault(n_type, []).append(category)
        return index

    def run(self):
        """Executes the extraction and returns the list of Node objects."""
        self._walk(self.tree.root_node, [], None)
        return self.extracted_nodes

    def _walk(self, ts_node, ts_ancestors, last_created_node):
        """
        ts_node: The current tree-sitter node.
        ts_ancestors: The path of tree-sitter nodes from root.
        last_created_node: The nearest ancestor that was converted to a Node object.
        """
        current_node_obj = last_created_node

        if ts_node.is_named and ts_node.type in self.node_type_index:
            for category in self.node_type_index[ts_node.type]:
                # Create the Node object
                node_obj = self._create_node_object(ts_node, category, ts_ancestors, last_created_node)
                
                if node_obj:
                    self.extracted_nodes.append(node_obj)
                    if last_created_node:
                        last_created_node.add_child(node_obj)
                    current_node_obj = node_obj # Update scope for children

        # Continue Traversal
        new_ts_ancestors = ts_ancestors + [ts_node]
        for child in ts_node.children:
            self._walk(child, new_ts_ancestors, current_node_obj)

    def _create_node_object(self, ts_node, category, ts_ancestors, parent_obj):
        """Instantiates a Node object with common props and metadata."""
        
        # 1. Extract Common Props & Metadata using specialized logic
        extractor = self._extractors.get(category)
        name = None
        qualified_name = None
        metadata = {}

        if extractor:
            name, qualified_name, metadata = extractor(ts_node, ts_ancestors)
        else:
            # Default fallback for simple nodes
            name = self._get_node_text(ts_node.child_by_field_name("name"))

        # 2. Return the formal Node instance
        return Node(
            file_rel_path=self.relative_path,
            category=category,
            node_type=ts_node.type,
            start_line=ts_node.start_point[0] + 1,
            end_line=ts_node.end_point[0] + 1,
            start_column=ts_node.start_point[1],
            end_column=ts_node.end_point[1],
            text=self._get_node_text(ts_node),
            name=name,
            qualified_name=qualified_name,
            parent=parent_obj,
            metadata=metadata
        )

    # --- Specialized Logic ---

    def _extract_import_data(self, node, ancestors):
        if self.extension == ".py":
            return self._extract_python_import(node, ancestors)
        return self._extract_js_import(node, ancestors)

    def _extract_python_import(self, node, ancestors):
        if node.type == "import_statement":
            # import os  |  import numpy as np
            module, alias = None, None
            for child in node.named_children:
                if child.type == "dotted_name":
                    module = self._get_node_text(child)
                elif child.type == "aliased_import":
                    module = self._get_node_text(child.child_by_field_name("name"))
                    alias  = self._get_node_text(child.child_by_field_name("alias"))
                break  # one import per statement (handles the common case)
            name = alias or module
            return name, name, {
                "module":         module,
                "symbols":        [],
                "alias":          alias,
                "is_reexport":    False,
                "is_relative":    False,
                "is_star":        False,
                "is_conditional": self._is_conditional(ancestors),
                "is_dynamic":     False,
            }

        # import_from_statement  |  future_import_statement
        # from models.user import User, UserRole
        # from . import auth
        module_str  = self._get_node_text(node.child_by_field_name("module_name")) or ""
        is_conditional = self._is_conditional(ancestors)

        symbols, is_star, past_import = [], False, False
        for child in node.children:
            if child.type == "import":          # unnamed keyword node
                past_import = True
                continue
            if not past_import:
                continue
            if child.type == "wildcard_import":
                is_star = True
            elif child.type == "dotted_name":
                sym = self._get_node_text(child)
                if sym:
                    symbols.append(sym)
            elif child.type == "aliased_import":
                sym = self._get_node_text(child.child_by_field_name("name"))
                if sym:
                    symbols.append(sym)

        # A module-level import inside __init__.py is a re-export by convention —
        # the file owns nothing, it only passes symbols through to consumers.
        is_reexport = (
            os.path.basename(self.file_path) == "__init__.py"
            and not is_conditional
        )

        name = symbols[0] if symbols else (module_str or None)
        return name, name, {
            "module":         module_str,
            "symbols":        symbols,
            "alias":          None,
            "is_reexport":    is_reexport,
            "is_relative":    module_str.startswith("."),
            "is_star":        is_star,
            "is_conditional": is_conditional,
            "is_dynamic":     False,
        }

    def _extract_js_import(self, node, ancestors):
        # Module specifier: the string literal after 'from'
        source      = node.child_by_field_name("source")
        raw         = self._get_node_text(source) if source else None
        module_spec = raw.strip("'\"") if raw else None

        default_import, namespace_import = None, None
        named_imports = []
        node_text     = self._get_node_text(node) or ""
        is_type_only  = "type" in node_text.split()[:3]  # import type { ... }

        for child in node.children:
            if child.type != "import_clause":
                continue
            for clause_child in child.children:
                if clause_child.type == "identifier":
                    default_import = self._get_node_text(clause_child)
                elif clause_child.type == "named_imports":
                    for spec in clause_child.children:
                        if spec.type == "import_specifier":
                            nm = self._get_node_text(spec.child_by_field_name("name"))
                            al = self._get_node_text(spec.child_by_field_name("alias"))
                            if nm:
                                named_imports.append({"name": nm, "alias": al})
                elif clause_child.type == "namespace_import":
                    for nc in clause_child.children:
                        if nc.type == "identifier":
                            namespace_import = self._get_node_text(nc)
                            break
            break  # only one import_clause per statement

        return module_spec, module_spec, {
            "module_specifier": module_spec,
            "named_imports":    named_imports,
            "default_import":   default_import,
            "namespace_import": namespace_import,
            "is_star":          namespace_import is not None,
            "is_reexport":      False,
            "is_type_only":     is_type_only,
            "is_require":       False,
            "is_dynamic":       False,
            "is_conditional":   self._is_conditional(ancestors),
        }

    def _extract_export_data(self, node, ancestors):
        source = node.child_by_field_name("source")

        if not source:
            # Regular export: export function foo() / export class Bar / export default
            # Not a re-export — the file owns what it exports.
            name = self._get_node_text(node.child_by_field_name("declaration"))
            return name, name, {"is_reexport": False}

        # Re-export: export { x } from "./module"  |  export * from "./module"
        # The file does not own these symbols — it only passes them through.
        raw            = self._get_node_text(source)
        module_spec    = raw.strip("'\"") if raw else None
        named_imports  = []
        is_star        = False
        node_text      = self._get_node_text(node) or ""
        is_type_only   = "type" in node_text.split()[:3]

        for child in node.children:
            if child.type == "export_clause":
                for spec in child.children:
                    if spec.type == "export_specifier":
                        nm = self._get_node_text(spec.child_by_field_name("name"))
                        al = self._get_node_text(spec.child_by_field_name("alias"))
                        if nm:
                            named_imports.append({"name": nm, "alias": al})
            elif not child.is_named and self._get_node_text(child) == "*":
                is_star = True

        return module_spec, module_spec, {
            "module_specifier": module_spec,
            "named_imports":    named_imports,
            "is_star":          is_star,
            "is_reexport":      True,
            "is_type_only":     is_type_only,
            "is_conditional":   self._is_conditional(ancestors),
        }

    def _extract_function_data(self, node, ancestors):
        name_node = node.child_by_field_name("name")
        name = self._get_node_text(name_node)
        
        is_anon = name is None
        if is_anon:
            name = self._generate_anon_id(node, ancestors)

        qualified_name = self._get_qualified_name(name, ancestors)
        
        metadata = {
            "parameters": self._get_node_text(node.child_by_field_name("parameters")),
            "return_type": self._get_node_text(node.child_by_field_name("return_type")),
            "docstring": self._get_docstring(node),
            "is_async": "async" in (self._get_node_text(node) or "").splitlines()[0],
            "is_anonymous": is_anon
        }
        return name, qualified_name, metadata

    def _extract_class_data(self, node, ancestors):
        name = self._get_node_text(node.child_by_field_name("name"))
        qualified_name = self._get_qualified_name(name, ancestors)
        
        metadata = {
            "base_classes": self._get_node_text(node.child_by_field_name("superclasses")),
            "docstring": self._get_docstring(node)
        }
        return name, qualified_name, metadata

    def _extract_call_data(self, node, ancestors):
        name = self._get_node_text(node.child_by_field_name("function"))
        metadata = {
            "is_interpolated": any(a.type in {"interpolation", "template_string"} for a in ancestors)
        }
        return name, None, metadata

    def _extract_variable_data(self, node, ancestors):
        if self.extension == ".py":
            # Python assignment: left field holds the target name
            name = self._get_node_text(node.child_by_field_name("left"))
        else:
            # JS/TS lexical_declaration: const X = ...
            # Structure: lexical_declaration → variable_declarator → name field
            declarator = next(
                (c for c in node.named_children if c.type == "variable_declarator"),
                None,
            )
            name = self._get_node_text(declarator.child_by_field_name("name")) if declarator else None

        # A variable is module-level when it is not nested inside a function or class.
        # Python scope types contain "definition" (function_definition, class_definition).
        # JS/TS scope types contain "function" or "method" (function_declaration,
        # arrow_function, method_definition, function_expression).
        is_module_level = not any(
            "definition" in a.type or "function" in a.type or "method" in a.type
            for a in ancestors
        )
        metadata = {
            "is_module_level": is_module_level
        }
        return name, None, metadata

    # --- Helpers ---

    def _get_node_text(self, node):
        if not node: return None
        return self.source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _get_qualified_name(self, name, ancestors):
        scope_types = {"class_definition", "function_definition", "method_definition"}
        path = []
        for a in ancestors:
            if a.type in scope_types:
                a_name = self._get_node_text(a.child_by_field_name("name")) or "<anon>"
                path.append(a_name)
        return ".".join(path + [name]) if name else ".".join(path)

    def _get_docstring(self, node):
        body = node.child_by_field_name("body")
        if not body or not body.children: return None
        first = body.children[0]
        if first.type == "expression_statement":
            # Tree-sitter specific: look for string literal child
            for c in first.children:
                if c.type == "string": return self._get_node_text(c)
        return None

    def _generate_anon_id(self, node, ancestors):
        return f"anon_{node.start_point[0]+1}_{node.start_point[1]}"

    def _is_conditional(self, ancestors) -> bool:
        return any(
            a.type in {"if_statement", "try_statement", "conditional_expression"}
            for a in ancestors
        )
