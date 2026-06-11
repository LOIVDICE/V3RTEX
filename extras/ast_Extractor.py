"""
AST Extractor
This script will extract the nodes from the AST that are relevant to the extraction rules.

Input: The AST of a file
Output: A list of nodes that are relevant to the extraction rules
"""

from extraction_Rules import PythonRules, JavaScriptRules, TypeScriptRules
from ast_Parser import ast_parser
from pathlib import Path
import os

rules_map = {
    '.py': PythonRules(),
    '.js': JavaScriptRules(),
    '.jsx': JavaScriptRules(),
    '.ts': TypeScriptRules(),
    '.tsx': TypeScriptRules(),
}

def get_file_extension(file_path):
    # Step 1: Get the real file extension with the dot included, like ".py".
    return os.path.splitext(file_path)[1].lower()

def get_rules(file_extension):
    # Step 2: Pick the correct rule class for this file type.
    if file_extension not in rules_map:
        raise ValueError(f"Unsupported file extension: {file_extension}")

    return rules_map[file_extension].get_rules()

def get_direct_rules(file_extension):
    # Step 3: Get only the rules that are safe to match directly.
    if file_extension not in rules_map:
        raise ValueError(f"Unsupported file extension: {file_extension}")

    return rules_map[file_extension].get_direct_rules()

def build_node_type_index(rules):
    # Step 4: Flip the rules so we can quickly ask: "what category uses this node type?"
    node_type_index = {}

    for category, node_types in rules.items():
        for node_type in node_types:
            if node_type not in node_type_index:
                node_type_index[node_type] = []

            node_type_index[node_type].append(category)

    return node_type_index

def get_node_text(node, source_code):
    # Step 5: Pull the exact source code text covered by this AST node.
    if node is None:
        return None

    node_bytes = source_code[node.start_byte:node.end_byte]
    return node_bytes.decode("utf-8", errors="replace")

def find_first_child_by_type(node, node_type):
    # Step 6: Find a direct child with a specific Tree-sitter node type.
    for child in node.children:
        if child.type == node_type:
            return child

    return None

def find_children_by_type(node, node_type):
    # Step 7: Find direct children with a specific Tree-sitter node type.
    return [
        child
        for child in node.children
        if child.type == node_type
    ]

def find_descendants_by_type(node, node_types):
    # Step 8: Find nested children with any of the requested node types.
    matches = []

    if node.type in node_types:
        matches.append(node)

    for child in node.children:
        matches.extend(find_descendants_by_type(child, node_types))

    return matches

def is_inside_node_type(ancestors, node_type):
    # Step 9: Check parent context without needing a long chain of if statements.
    return any(ancestor.type == node_type for ancestor in ancestors)

def get_node_name(node, source_code):
    # Step 10: Read the declared name of functions/classes when Tree-sitter exposes it.
    name_node = node.child_by_field_name("name")
    return get_node_text(name_node, source_code)

def get_decorator_texts(ancestors, source_code, node=None):
    # Step 11: Decorated functions/classes are wrapped in decorated_definition nodes.
    for ancestor in reversed(ancestors):
        if ancestor.type == "decorated_definition":
            if node is not None and node not in ancestor.children:
                continue

            return [
                get_node_text(decorator, source_code)
                for decorator in find_children_by_type(ancestor, "decorator")
            ]

    return []

def get_assigned_name(ancestors, source_code):
    # Step 12: Anonymous functions can be named by the variable they are assigned to.
    for ancestor in reversed(ancestors):
        left_node = ancestor.child_by_field_name("left")
        name_node = ancestor.child_by_field_name("name")

        if left_node is not None:
            return get_node_text(left_node, source_code)

        if name_node is not None and ancestor.type in {"variable_declarator", "pair"}:
            return get_node_text(name_node, source_code)

    return None

def get_generated_function_id(node, source_code, ancestors):
    # Step 13: Lambdas/anonymous functions need stable IDs so graph nodes stay unique.
    assigned_name = get_assigned_name(ancestors, source_code)

    if assigned_name:
        return assigned_name

    return f"<anonymous>@line:{node.start_point[0] + 1}:column:{node.start_point[1]}"

def get_scope_path(ancestors, source_code):
    # Step 14: Build the path for nested functions/classes, like Outer.inner.helper.
    scope_node_types = {
        "class_definition",
        "class_declaration",
        "abstract_class_declaration",
        "function_definition",
        "async_function_definition",
        "function_declaration",
        "function_expression",
        "generator_function_declaration",
        "generator_function",
        "method_definition",
        "arrow_function",
        "lambda",
    }
    scope = []

    for ancestor in ancestors:
        if ancestor.type in scope_node_types:
            name = get_node_name(ancestor, source_code)

            if name is None and ancestor.type in {"lambda", "arrow_function", "function_expression"}:
                name = get_generated_function_id(ancestor, source_code, ancestors)

            if name:
                scope.append(name)

    return scope

def get_qualified_name(name, ancestors, source_code):
    # Step 15: Use scope context to avoid merging unrelated functions with the same name.
    scope = get_scope_path(ancestors, source_code)

    if not name:
        return ".".join(scope) if scope else None

    return ".".join(scope + [name])

def get_type_annotations(node, source_code):
    # Step 16: Keep type annotations as strings; parsing them deeply can come later.
    annotation_node_types = {
        "type",
        "type_annotation",
        "typed_parameter",
        "typed_default_parameter",
        "return_type",
    }
    annotations = []

    for annotation in find_descendants_by_type(node, annotation_node_types):
        text = get_node_text(annotation, source_code)

        if text and text not in annotations:
            annotations.append(text)

    return annotations

def get_signature_type_annotations(parameters_node, return_type_node, source_code):
    # Step 17: Function annotations should come from the signature, not nested body nodes.
    annotations = []

    for node in (parameters_node, return_type_node):
        if node is None:
            continue

        for annotation in find_descendants_by_type(node, {
            "type",
            "type_annotation",
            "typed_parameter",
            "typed_default_parameter",
            "return_type",
        }):
            text = get_node_text(annotation, source_code)

            if text and text not in annotations:
                annotations.append(text)

    return annotations

def get_docstring(node, source_code):
    # Step 18: A Python docstring is the first string expression inside a body/block.
    body_node = node.child_by_field_name("body")

    if body_node is None:
        body_node = find_first_child_by_type(node, "block")

    if body_node is None or not body_node.children:
        return None

    first_statement = body_node.children[0]

    if first_statement.type == "expression_statement":
        string_node = find_first_child_by_type(first_statement, "string")
        return get_node_text(string_node, source_code)

    if first_statement.type == "string":
        return get_node_text(first_statement, source_code)

    return None

def is_inside_interpolated_string(ancestors):
    # Step 19: Calls inside f-strings/template strings still count as real calls.
    interpolation_node_types = {
        "interpolation",
        "template_substitution",
    }
    string_node_types = {
        "string",
        "template_string",
    }

    return (
        any(ancestor.type in interpolation_node_types for ancestor in ancestors)
        or any(ancestor.type in string_node_types for ancestor in ancestors)
    )

def get_nearest_scope_type(ancestors):
    # Step 20: The nearest enclosing class/function decides if a def is a method.
    scope_node_types = {
        "class_definition",
        "class_declaration",
        "abstract_class_declaration",
        "function_definition",
        "async_function_definition",
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
        "lambda",
    }

    for ancestor in reversed(ancestors):
        if ancestor.type in scope_node_types:
            return ancestor.type

    return None

def build_node_record(node, category, source_code):
    # Step 21: Convert a Tree-sitter node into a simple dictionary we can use later.
    return {
        "category": category,
        "node_type": node.type,
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
        "start_column": node.start_point[1],
        "end_column": node.end_point[1],
        "text": get_node_text(node, source_code),
    }

def extract_function(node, category, source_code, ancestors=None):
    # Step 22: Extract function-level details from inside the function node.
    if ancestors is None:
        ancestors = []

    name_node = node.child_by_field_name("name")
    parameters_node = node.child_by_field_name("parameters")
    return_type_node = node.child_by_field_name("return_type")
    name = get_node_text(name_node, source_code)
    is_anonymous = name is None

    if is_anonymous:
        name = get_generated_function_id(node, source_code, ancestors)

    record = build_node_record(node, category, source_code)
    record.update({
        "name": name,
        "qualified_name": get_qualified_name(name, ancestors, source_code),
        "parameters": get_node_text(parameters_node, source_code),
        "return_type": get_node_text(return_type_node, source_code),
        "type_annotations": get_signature_type_annotations(parameters_node, return_type_node, source_code),
        "decorators": get_decorator_texts(ancestors, source_code, node),
        "docstring": get_docstring(node, source_code),
        "is_anonymous": is_anonymous,
        "is_lambda": node.type == "lambda",
        "is_arrow_function": node.type == "arrow_function",
        "is_async": node.type == "async_function_definition" or "async" in get_node_text(node, source_code).splitlines()[0],
    })
    return record

def extract_class(node, category, source_code, ancestors=None):
    # Step 23: Extract class-level details from inside the class node.
    if ancestors is None:
        ancestors = []

    name_node = node.child_by_field_name("name")
    superclasses_node = node.child_by_field_name("superclasses")
    heritage_node = find_first_child_by_type(node, "class_heritage")
    name = get_node_text(name_node, source_code)

    record = build_node_record(node, category, source_code)
    record.update({
        "name": name,
        "qualified_name": get_qualified_name(name, ancestors, source_code),
        "base_classes": get_node_text(superclasses_node or heritage_node, source_code),
        "decorators": get_decorator_texts(ancestors, source_code, node),
        "docstring": get_docstring(node, source_code),
    })
    return record

def extract_call(node, category, source_code, ancestors=None):
    # Step 24: Extract the callee part of a call expression.
    if ancestors is None:
        ancestors = []

    function_node = node.child_by_field_name("function")

    record = build_node_record(node, category, source_code)
    record.update({
        "callee_name": get_node_text(function_node, source_code),
        "is_inside_interpolated_string": is_inside_interpolated_string(ancestors),
    })
    return record

def extract_variable(node, category, source_code, ancestors=None):
    # Step 25: Keep variable extraction broad for now, but mark module-level status.
    record = build_node_record(node, category, source_code)
    record.update({
        "name": get_node_text(node.child_by_field_name("left"), source_code),
        "type_annotations": get_type_annotations(node, source_code),
    })
    return record

def extract_module_metadata(node, category, source_code, ancestors=None):
    # Step 26: Store file/module-level information that can be computed from source.
    record = build_node_record(node, category, source_code)
    source_text = source_code.decode("utf-8", errors="replace")
    record.update({
        "total_line_count": len(source_text.splitlines()),
        "has_syntax_errors": "ERROR" in get_node_text(node, source_code),
    })
    return record

def extract_control_flow(node, category, source_code, ancestors=None):
    # Step 27: Store behavior/complexity nodes like loops and conditionals.
    if ancestors is None:
        ancestors = []

    loop_node_types = {
        "for_statement",
        "for_in_statement",
        "for_of_statement",
        "while_statement",
        "do_statement",
    }
    function_node_types = {
        "function_definition",
        "async_function_definition",
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
    }

    record = build_node_record(node, category, source_code)
    record.update({
        "is_nested": any(ancestor.type in loop_node_types for ancestor in ancestors),
        "is_inside_function": any(ancestor.type in function_node_types for ancestor in ancestors),
    })
    return record

def should_extract_function(node, ancestors):
    # Step 27: A def whose nearest scope is a class is a method; nested defs stay functions.
    return get_nearest_scope_type(ancestors) not in {
        "class_definition",
        "class_declaration",
        "abstract_class_declaration",
    }

def should_extract_method(node, ancestors):
    # Step 28: Python methods are function nodes whose nearest scope is a class.
    return node.type == "method_definition" or get_nearest_scope_type(ancestors) in {
        "class_definition",
        "class_declaration",
        "abstract_class_declaration",
    }

def should_extract_variable(node, ancestors):
    # Step 29: Only extract module-level variables for now, not local variables.
    blocked_contexts = {
        "function_definition",
        "async_function_definition",
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
        "class_definition",
        "class_declaration",
    }
    return not any(ancestor.type in blocked_contexts for ancestor in ancestors)

CATEGORY_EXTRACTORS = {
    # Step 18: This map replaces a long if/elif chain.
    "functions": extract_function,
    "methods": extract_function,
    "classes": extract_class,
    "function_calls": extract_call,
    "variables": extract_variable,
    "conditionals": extract_control_flow,
    "loops": extract_control_flow,
    "loop_controls": extract_control_flow,
    "try_blocks": extract_control_flow,
    "module_metadata": extract_module_metadata,
}

CATEGORY_FILTERS = {
    # Step 19: These filters remove common false positives using AST context.
    "functions": should_extract_function,
    "methods": should_extract_method,
    "variables": should_extract_variable,
}

def extract_node_by_category(node, category, source_code, ancestors):
    # Step 20: Use the extractor map, with a basic record as the fallback.
    extractor = CATEGORY_EXTRACTORS.get(category)

    if extractor is None:
        return build_node_record(node, category, source_code)

    return extractor(node, category, source_code, ancestors)

def should_extract_category(node, category, ancestors):
    # Step 21: Use the filter map, with True as the default for simple categories.
    category_filter = CATEGORY_FILTERS.get(category)

    if category_filter is None:
        return True

    return category_filter(node, ancestors)

def walk_tree(node, node_type_index, extracted_nodes, source_code, ancestors=None):
    # Step 22: Check whether the current node is one of the direct node types we care about.
    if ancestors is None:
        ancestors = []

    if node.is_named and node.type in node_type_index:
        for category in node_type_index[node.type]:
            if should_extract_category(node, category, ancestors):
                extracted_nodes[category].append(
                    extract_node_by_category(node, category, source_code, ancestors)
                )

    # Step 23: Repeat the same check for every child node.
    next_ancestors = ancestors + [node]

    for child in node.children:
        walk_tree(child, node_type_index, extracted_nodes, source_code, next_ancestors)

def ast_extractor(file_path):
    # Step 24: Detect the file type, parse it, and read the original source bytes.
    file_extension = get_file_extension(file_path)
    tree = ast_parser(file_path)
    source_code = Path(file_path).read_bytes()

    # Step 25: Load all rules for output keys, and direct rules for tree matching.
    rules = get_rules(file_extension)
    direct_rules = get_direct_rules(file_extension)

    # Step 26: Prepare an empty output list for every extraction category.
    extracted_nodes = {
        category: []
        for category in rules
    }

    # Step 27: Build the fast lookup table and walk the AST from the root.
    node_type_index = build_node_type_index(direct_rules)
    walk_tree(tree.root_node, node_type_index, extracted_nodes, source_code)

    # Step 28: Return the grouped raw extraction results.
    return extracted_nodes