"""
call_Resolver.py

Stage 4 of the V3RTEX engine — the Call Graph builder.

Takes every function_calls node found by the AST extractor (Stage 2) and
resolves it to the actual function / method / variable definition it references.
Uses the SymbolMap from Stage 3 to trace imported names to their origins.

Input  : List[File]  (with .nodes populated by the AST extractor)
         SymbolMap   (produced by SymbolResolver)
Output : CallGraph   (defined in compBlocs12.py)

Side-effect: every function_calls node gets three metadata fields written back:
    resolved_target  : str | None   — target node id
    enclosing_fn     : str | None   — enclosing function/method node id
    resolution       : str          — LOCAL | IMPORTED | UNRESOLVED

Supported languages : Python · JavaScript · TypeScript · JSX · TSX
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from compBlocs12 import File, Node, SymbolMap, CallEdge, CallGraph


class CallResolver:
    """
    Stage 4: resolves function_calls nodes to their definitions and emits
    CALLS / USES edges into a CallGraph.

    Design mirrors SymbolResolver:
        __init__          — store inputs, build indexes once
        produce_call_graph — public entry point; returns CallGraph
        _resolve_file     — per-file loop over all function_calls nodes
        _resolve_call     — per-call core logic
        helpers           — _find_enclosing_fn, _parse_call_name, _resolve_target, etc.
    """

    # Categories that can appear as a callee (be the target of a call)
    _DEFINABLE = {"functions", "methods", "classes", "variables"}

    # Known built-in names that are never in the project — always EXTERNAL
    _BUILTINS: set = {
        # Python built-ins
        "print", "len", "range", "enumerate", "zip", "map", "filter",
        "sorted", "reversed", "list", "dict", "set", "tuple", "str",
        "int", "float", "bool", "bytes", "type", "isinstance", "issubclass",
        "hasattr", "getattr", "setattr", "delattr", "callable", "iter",
        "next", "any", "all", "sum", "min", "max", "abs", "round", "pow",
        "divmod", "hex", "oct", "bin", "ord", "chr", "repr", "hash", "id",
        "dir", "vars", "globals", "locals", "super", "open", "input",
        "format", "object", "property", "classmethod", "staticmethod",
        # JS / TS built-ins
        "console", "setTimeout", "setInterval", "clearTimeout",
        "clearInterval", "Promise", "JSON", "Math", "Date", "Array",
        "Object", "String", "Number", "Boolean", "parseInt", "parseFloat",
        "isNaN", "isFinite", "encodeURIComponent", "decodeURIComponent",
        "fetch", "require", "Error", "Symbol", "Map", "Set", "WeakMap",
        "WeakSet", "Proxy", "Reflect",
    }

    def __init__(self, files: List[File], symbol_map: SymbolMap):
        """
        :param files:       All File objects with .nodes populated (Stage 2 output).
        :param symbol_map:  SymbolMap produced by SymbolResolver (Stage 3 output).
        """
        self._files = {
            f.relative_path.replace("\\", "/"): f for f in files
        }
        self._symbol_map = symbol_map

        # Built once at init; queried O(1) per call-site lookup
        self._fn_index:   Dict[Tuple[str, str], str] = {}   # (rel_path, name) → node_id
        self._node_index: Dict[str, Node]            = {}   # node_id → Node

        self._build_fn_index()

    # ── public API ────────────────────────────────────────────────────────

    def produce_call_graph(self) -> CallGraph:
        """
        Resolve all call sites across every file in the project.

        Returns a CallGraph containing every CALLS / USES edge that could be
        resolved. Unresolvable call sites are skipped (metadata still written).
        """
        call_graph = CallGraph()

        for file in self._files.values():
            self._resolve_file(file, call_graph)

        return call_graph

    # ── index builders ────────────────────────────────────────────────────

    def _build_fn_index(self) -> None:
        """
        Build two project-wide indexes in a single pass over all nodes:

        _fn_index   : (file_rel_path, name)           → node_id
                      (file_rel_path, qualified_name)  → node_id
            Used to look up local definitions and definitions in imported files.

        _node_index : node_id → Node
            Used to retrieve a Node from its id during edge creation and reporting.
        """
        for file in self._files.values():
            rel = file.relative_path.replace("\\", "/")
            for node in file.nodes:
                # Index every node for reverse lookups
                self._node_index[node.id] = node

                # Only index definable categories as call targets
                if node.category in self._DEFINABLE and node.name:
                    self._fn_index[(rel, node.name)] = node.id
                    if node.qualified_name and node.qualified_name != node.name:
                        self._fn_index[(rel, node.qualified_name)] = node.id

    def _build_import_aliases(self, file: File) -> Dict[str, dict]:
        """
        Build the per-file alias map for every INTERNAL import in this file.

        Returns  { call_site_name: entry }  where entry is one of:

            Direct symbol import
                { "type": "direct",
                  "node_id": str,        ← resolved definition node id
                  "hops": [str, ...] }   ← import chain from SymbolMap

            Namespace / bare-module import  (import * as ns  /  import mod as alias)
                { "type": "namespace",
                  "node_id": None,
                  "origin_file": str,    ← the target file to search for methods
                  "hops": [str, ...] }

        The key is always the name that appears at call sites:
            the alias if one is present, the original name otherwise.
        """
        aliases: Dict[str, dict] = {}

        for node in file.nodes:
            if node.category != "imports":
                continue
            if node.metadata.get("resolution") != "INTERNAL":
                continue

            target_path = node.metadata.get("target_file_path", "")
            meta        = node.metadata

            # ── namespace import: import * as ns  (JS/TS) ────────────────
            is_namespace = (
                meta.get("namespace_import")
                or (
                    meta.get("is_star")
                    and not meta.get("named_imports")
                    and not meta.get("symbols")
                )
            )
            if is_namespace:
                ns_name = (
                    meta.get("namespace_alias")
                    or self._extract_namespace_alias(node.text)
                    or node.name
                )
                if ns_name:
                    aliases[ns_name] = {
                        "type":        "namespace",
                        "node_id":     None,
                        "origin_file": target_path,
                        "hops":        [target_path],
                    }
                continue

            # ── Python bare import with alias: import services.auth as svc ──
            # No individual symbols → whole module is the target; treat as namespace
            python_symbols = [s for s in meta.get("symbols", []) if s]
            has_js_symbols = (
                bool(meta.get("named_imports"))
                or bool(meta.get("default_import"))
            )
            if not python_symbols and not has_js_symbols:
                alias = meta.get("alias") or node.name
                if alias:
                    aliases[alias] = {
                        "type":        "namespace",
                        "node_id":     None,
                        "origin_file": target_path,
                        "hops":        [target_path],
                    }
                continue

            # ── named imports with optional aliases ───────────────────────
            for original, call_site_name in self._symbols_with_aliases(node):
                node_id = self._symbol_map.get_target(node.id, original)
                if node_id:
                    lineage = self._symbol_map.get_lineage(node.id, original)
                    hops    = lineage.get("hops", []) if lineage else []
                    aliases[call_site_name] = {
                        "type":    "direct",
                        "node_id": node_id,
                        "hops":    hops,
                    }

        return aliases

    def _build_external_names(self, file: File) -> set:
        """
        Collect every name that was imported externally in this file.
        These are the receiver names (e.g. "hashlib", "secrets", "datetime")
        that came from stdlib or third-party packages.

        When a call's receiver matches one of these names, it is tagged
        EXTERNAL rather than UNRESOLVED.
        """
        external: set = set()

        for node in file.nodes:
            if node.category != "imports":
                continue
            if node.metadata.get("resolution") != "EXTERNAL":
                continue

            meta = node.metadata

            # Python bare import: import hashlib  → receiver name = "hashlib"
            # Python alias:       import numpy as np → receiver name = "np"
            alias = meta.get("alias")
            if alias:
                external.add(alias)
            elif meta.get("module"):
                # Use the top-level package name as the receiver
                external.add(meta["module"].split(".")[0])

            # Python from-import: from datetime import datetime, timedelta
            for sym in meta.get("symbols", []):
                if sym:
                    external.add(sym)

            # JS/TS named imports
            for item in meta.get("named_imports", []):
                name = item.get("alias") or item.get("name") if isinstance(item, dict) else item
                if name:
                    external.add(name)

            # JS/TS default import
            default = meta.get("default_import")
            if default:
                external.add(default)

            # JS/TS namespace import: import * as ns
            ns = (
                meta.get("namespace_alias")
                or self._extract_namespace_alias(node.text)
                or node.name
            )
            if ns and meta.get("namespace_import"):
                external.add(ns)

        return external

    # ── per-file resolution ───────────────────────────────────────────────

    def _resolve_file(self, file: File, call_graph: CallGraph) -> None:
        """
        Resolve every function_calls node in one file and add edges
        to the call_graph.

        scope_cache stores the local scope dict for each enclosing function so
        it is built once per function rather than once per call inside it.
        seen deduplicates (caller_id, callee_id, site_line) to prevent the same
        call expression producing multiple edges.
        """
        import_aliases  = self._build_import_aliases(file)
        external_names  = self._build_external_names(file)
        seen:        set              = set()
        scope_cache: Dict[str, dict] = {}   # fn_node_id → local_scope

        for node in file.nodes:
            if node.category == "function_calls":
                self._resolve_call(node, file, import_aliases, external_names, call_graph, seen, scope_cache)

    def _resolve_call(
        self,
        call_node:      Node,
        file:           File,
        import_aliases: Dict[str, dict],
        external_names: set,
        call_graph:     CallGraph,
        seen:           set,
        scope_cache:    Dict[str, dict],
    ) -> None:
        """
        Resolve one function_calls node end-to-end:

        1. Find the enclosing function / method (the caller)
        2. Get or build the local scope for that function (cached)
        3. Parse the raw call name into (receivers_chain, method)
        4. Look up the definition node (the callee)
        5. Write resolution metadata back onto call_node
        6. Add a CallEdge to the call_graph
        """
        # 1. Enclosing function — module-level calls have no caller to link from
        enclosing = self._find_enclosing_fn(call_node)
        if enclosing is None:
            call_node.metadata["enclosing_fn"]    = None
            call_node.metadata["resolved_target"] = None
            call_node.metadata["resolution"]      = "UNRESOLVED"
            return

        # 2. Build local scope once per enclosing function, then cache it
        if enclosing.id not in scope_cache:
            scope_cache[enclosing.id] = self._build_local_scope(
                enclosing, import_aliases
            )
        local_scope = scope_cache[enclosing.id]

        # 3. Parse call name — returns full receiver chain + method
        receivers, method = self._parse_call_name(call_node.name or "")
        if not method:
            call_node.metadata["enclosing_fn"]    = enclosing.id
            call_node.metadata["resolved_target"] = None
            call_node.metadata["resolution"]      = "UNRESOLVED"
            return

        # 4. Resolve target
        rel = file.relative_path.replace("\\", "/")

        # Special case: dynamic import("./path") — language keyword used as a call
        if not receivers and method == "import":
            target_id, resolution, hops = self._resolve_dynamic_import(call_node, file)
        else:
            target_id, resolution, hops = self._resolve_target(
                receivers, method, rel, import_aliases, local_scope, external_names
            )

        # 5. Write back metadata
        call_node.metadata["enclosing_fn"]    = enclosing.id
        call_node.metadata["resolved_target"] = target_id
        call_node.metadata["resolution"]      = resolution

        # 6. Emit edge always — resolved or not
        dedup_key = (enclosing.id, target_id, call_node.start_line)
        if dedup_key in seen:
            return
        seen.add(dedup_key)

        target_node = self._node_index.get(target_id) if target_id else None
        edge_type   = (
            "USES"
            if target_node and target_node.category == "variables"
            else "CALLS"
        )
        call_graph.add(CallEdge(
            caller_node_id    = enclosing.id,
            callee_node_id    = target_id,       # None when UNRESOLVED
            call_site_node_id = call_node.id,
            edge_type         = edge_type,
            resolution        = resolution,
            hops              = hops,
        ))

    # ── helpers ───────────────────────────────────────────────────────────

    def _find_enclosing_fn(self, node: Node) -> Optional[Node]:
        """
        Walk node.parent upward until a functions or methods node is found.
        Returns that node, or None if the call is at module level.
        """
        current = node.parent
        while current is not None:
            if current.category in ("functions", "methods"):
                return current
            current = current.parent
        return None

    def _parse_call_name(self, raw: str) -> Tuple[List[str], str]:
        """
        Parse a raw call-name string into (receiver_chain, method).

        The receiver chain is the list of names before the final method name.
        An empty list means a simple call with no receiver.

        Examples:
            "foo"                  → ([],              "foo")
            "obj.method"           → (["obj"],         "method")
            "self.get_by_email"    → (["self"],        "get_by_email")
            "self.auth.revoke_all" → (["self","auth"], "revoke_all")
            "foo(bar)"             → ([],              "foo")
        """
        name = raw.split("(")[0].strip()

        # Strip await keyword — "await foo" → "foo", "await obj.method" → "obj.method"
        if name.startswith("await "):
            name = name[6:].strip()

        if not name:
            return ([], "")

        parts = [p.strip() for p in name.split(".")]
        if len(parts) == 1:
            return ([], parts[0])

        return (parts[:-1], parts[-1])

    def _resolve_target(
        self,
        receivers:      List[str],
        method:         str,
        file_rel_path:  str,
        import_aliases: Dict[str, dict],
        local_scope:    Dict[str, Node],
        external_names: set,
    ) -> Tuple[Optional[str], str, List[str]]:
        """
        Look up the definition node for a call.
        Returns (target_node_id | None, resolution, hops).

        Simple call  foo()  — resolution order:
            1. Local definition in this file (_fn_index)
            2. Directly imported symbol (import_aliases)

        Member call  obj.method()  — resolution order:
            1. Import aliases  (existing: namespace / direct imports)
            2. Local scope     (new: self, local instances, self.attr chains)
        """
        if not receivers:
            # ── simple call: foo() ────────────────────────────────────────
            node_id = self._fn_index.get((file_rel_path, method))
            if node_id:
                return (node_id, "LOCAL", [])

            entry = import_aliases.get(method)
            if entry and entry["type"] == "direct" and entry["node_id"]:
                return (entry["node_id"], "IMPORTED", entry.get("hops", []))

            if method in self._BUILTINS or method in external_names:
                return (None, "EXTERNAL", [])

            return (None, "UNRESOLVED", [])

        else:
            # ── member call: obj.method() ─────────────────────────────────

            # 1. Try import aliases (single-receiver only — e.g. mod.func())
            if len(receivers) == 1:
                entry = import_aliases.get(receivers[0])
                if entry:
                    if entry["type"] == "namespace":
                        origin  = entry.get("origin_file", "")
                        node_id = self._fn_index.get((origin, method))
                        if node_id:
                            return (node_id, "IMPORTED", entry.get("hops", []))
                    elif entry["type"] == "direct":
                        origin_file = self._get_node_file(entry["node_id"])
                        if origin_file:
                            node_id = self._fn_index.get((origin_file, method))
                            if node_id:
                                return (node_id, "IMPORTED", entry.get("hops", []))

            # 2. Fall back to local scope (self, local instances, self.attr chains)
            target_class = self._resolve_receiver_chain(
                receivers, local_scope, import_aliases, file_rel_path
            )
            if target_class:
                rel     = target_class.file_rel_path.replace("\\", "/")
                node_id = self._fn_index.get((rel, method))
                if node_id:
                    resolution = "LOCAL" if rel == file_rel_path else "IMPORTED"
                    return (node_id, resolution, [])

            first = receivers[0] if receivers else method
            if first in self._BUILTINS or first in external_names:
                return (None, "EXTERNAL", [])

            return (None, "UNRESOLVED", [])

    def _symbols_with_aliases(self, imp_node: Node) -> List[Tuple[str, str]]:
        """
        Return [(symbol_map_key, call_site_name), ...] for every symbol
        in this import node.

        symbol_map_key  = original name used as key inside the SymbolMap
        call_site_name  = the name that appears in the source code
                          (the alias if one was declared, original name otherwise)
        """
        meta   = imp_node.metadata
        result = []

        # ── Python: metadata["symbols"] = ["foo", "bar"] ─────────────────
        if "symbols" in meta:
            symbols = [s for s in meta.get("symbols", []) if s]
            alias   = meta.get("alias")

            # Single-symbol import with alias: from x import foo as f
            if len(symbols) == 1 and alias:
                result.append((symbols[0], alias))
            else:
                for s in symbols:
                    result.append((s, s))
            return result

        # ── JS/TS: named imports with optional aliases ─────────────────────
        # metadata["named_imports"] = [{"name": "foo", "alias": "f"}, ...]
        for item in meta.get("named_imports", []):
            if isinstance(item, dict):
                original  = item.get("name", "")
                call_site = item.get("alias") or original
                if original:
                    result.append((original, call_site))
            else:
                result.append((item, item))

        # ── JS/TS: default import ─────────────────────────────────────────
        # metadata["default_import"] = "MyClass"
        # Both SymbolMap key and call-site name are the same (the local binding name)
        default = meta.get("default_import")
        if default:
            result.append((default, default))

        return result

    def _build_local_scope(
        self,
        fn_node:        Node,
        import_aliases: Dict[str, dict],
    ) -> Dict[str, Node]:
        """
        Build a { name: class_node } map for one function before resolving its calls.

        Entries produced:
            "self"        → the enclosing class Node
            "self.auth"   → the AuthService Node  (from __init__: self.auth = AuthService(...))
            "p"           → the Paginator Node     (from: p = Paginator(...))
        """
        scope: Dict[str, Node] = {}
        rel = fn_node.file_rel_path.replace("\\", "/")

        # ── self → enclosing class ────────────────────────────────────────
        class_node = self._find_enclosing_class(fn_node)
        if class_node:
            scope["self"] = class_node

            # ── self.attr from __init__ ───────────────────────────────────
            init_node = next(
                (c for c in class_node.children if c.name == "__init__"),
                None
            )
            if init_node:
                param_types = self._parse_param_types(init_node)

                for var in init_node.children:
                    if var.category != "variables":
                        continue
                    if not var.name or not var.name.startswith("self."):
                        continue

                    attr = var.name[len("self."):]

                    # Case A: self.attr = SomeClass(...)
                    cls = self._extract_constructor_type(var.text, import_aliases, rel)
                    if cls:
                        scope[f"self.{attr}"] = cls
                        continue

                    # Case B: self.attr = param  where param has a type annotation
                    rhs = var.text.split("=", 1)[1].strip() if "=" in var.text else ""
                    rhs_name = rhs.split("(")[0].strip()
                    type_name = param_types.get(rhs_name)
                    if type_name:
                        cls = self._lookup_class_by_name(type_name, import_aliases, rel)
                        if cls:
                            scope[f"self.{attr}"] = cls

        # ── local variables: p = SomeClass(...) ──────────────────────────
        for var in fn_node.children:
            if var.category != "variables":
                continue
            if not var.name or var.name.startswith("self."):
                continue
            cls = self._extract_constructor_type(var.text, import_aliases, rel)
            if cls:
                scope[var.name] = cls

        return scope

    def _find_enclosing_class(self, node: Node) -> Optional[Node]:
        """
        Walk node.parent upward until a classes node is found.
        Returns that node, or None if the function is not inside a class.
        """
        current = node.parent
        while current is not None:
            if current.category == "classes":
                return current
            current = current.parent
        return None

    def _parse_param_types(self, fn_node: Node) -> Dict[str, str]:
        """
        Parse the parameter annotation string from fn_node.metadata["parameters"]
        into  { param_name: type_name }.

        Input : "self, auth_service: AuthService, db: Database = None"
        Output: {"auth_service": "AuthService", "db": "Database"}
        """
        raw    = fn_node.metadata.get("parameters", "")
        result = {}
        for part in raw.split(","):
            part = part.strip().lstrip("*")   # handle *args / **kwargs
            if ":" in part:
                name, type_str = part.split(":", 1)
                name      = name.strip()
                type_name = type_str.split("=")[0].strip()  # drop default value
                if name and name not in ("self", "cls") and type_name:
                    result[name] = type_name
        return result

    def _extract_constructor_type(
        self,
        var_text:       str,
        import_aliases: Dict[str, dict],
        file_rel_path:  str,
    ) -> Optional[Node]:
        """
        From an assignment text like  "p = Paginator(page=page, size=size)"
        extract the constructor name ("Paginator") and return its class Node.
        Returns None if the right-hand side is not a constructor call.
        """
        if "=" not in var_text or "(" not in var_text:
            return None
        rhs         = var_text.split("=", 1)[1].strip()
        constructor = rhs.split("(")[0].strip()
        if not constructor:
            return None
        return self._lookup_class_by_name(constructor, import_aliases, file_rel_path)

    def _lookup_class_by_name(
        self,
        name:           str,
        import_aliases: Dict[str, dict],
        file_rel_path:  str,
    ) -> Optional[Node]:
        """
        Find a class or function node by name.
        Checks import aliases first, then the local file.
        """
        entry = import_aliases.get(name)
        if entry and entry["type"] == "direct":
            return self._node_index.get(entry["node_id"])

        node_id = self._fn_index.get((file_rel_path, name))
        if node_id:
            return self._node_index.get(node_id)

        return None

    def _resolve_receiver_chain(
        self,
        receivers:      List[str],
        local_scope:    Dict[str, Node],
        import_aliases: Dict[str, dict],
        file_rel_path:  str,
    ) -> Optional[Node]:
        """
        Walk the receiver chain and return the final class Node.

        ["self"]         → UserService node      (from scope["self"])
        ["self","auth"]  → AuthService node      (from scope["self.auth"])
        ["p"]            → Paginator node        (from scope["p"])
        """
        first = receivers[0]

        # Resolve the first name
        if first == "self":
            current = local_scope.get("self")
        else:
            current = local_scope.get(first)
            if not current:
                # Also try import aliases for the first name
                entry = import_aliases.get(first)
                if entry and entry["type"] == "direct":
                    current = self._node_index.get(entry["node_id"])

        if not current:
            return None

        # Walk the remaining names in the chain (e.g. "auth" in ["self","auth"])
        for attr in receivers[1:]:
            current = local_scope.get(f"self.{attr}")
            if not current:
                return None

        return current

    def _extract_namespace_alias(self, text: str) -> Optional[str]:
        """
        From  'import * as userApi from "..."'  extract  'userApi'.
        Used when the extractor does not store a namespace_alias metadata field.
        """
        m = re.search(r'\*\s+as\s+(\w+)', text or "")
        return m.group(1) if m else None

    def _resolve_dynamic_import(
        self,
        call_node: Node,
        file:      File,
    ) -> Tuple[Optional[str], str, List[str]]:
        """
        Resolve a dynamic  import("./path")  call to its target file.

        Extracts the string literal from the call text, resolves it as a
        JS module path relative to the current file, and returns the node id
        of the primary export of the target file.
        """
        m = re.search(r'import\s*\(\s*["\']([^"\']+)["\']', call_node.text or "")
        if not m:
            return (None, "UNRESOLVED", [])

        path_str   = m.group(1)
        source_rel = file.relative_path.replace("\\", "/")
        source_dir = "/".join(source_rel.split("/")[:-1])

        # Build the resolved path
        if path_str.startswith("."):
            resolved = os.path.normpath(
                os.path.join(source_dir, path_str)
            ).replace("\\", "/")
        else:
            return (None, "EXTERNAL", [])   # bare specifier → external package

        # Probe extensions then index files
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            candidate = resolved + ext
            if candidate in self._files:
                target_id = self._find_file_default(candidate)
                if target_id:
                    return (target_id, "IMPORTED", [candidate])

        for ext in (".ts", ".tsx", ".js", ".jsx"):
            candidate = f"{resolved}/index{ext}"
            if candidate in self._files:
                target_id = self._find_file_default(candidate)
                if target_id:
                    return (target_id, "IMPORTED", [candidate])

        return (None, "UNRESOLVED", [])

    def _find_file_default(self, rel_path: str) -> Optional[str]:
        """
        Return the node id of the primary export in a file.

        Prefers a function or class whose name matches the filename stem
        (the React component convention), then falls back to the first
        function or class found in the file.
        """
        file = self._files.get(rel_path)
        if not file:
            return None

        # Derive expected name: "DashboardPage.tsx" → "DashboardPage"
        stem = rel_path.split("/")[-1].split(".")[0]

        node_id = self._fn_index.get((rel_path, stem))
        if node_id:
            return node_id

        # Fallback: first function or class in the file
        for node in file.nodes:
            if node.category in ("functions", "classes") and node.name:
                return node.id

        return None

    def _get_node_file(self, node_id: str) -> Optional[str]:
        """
        Return the file_rel_path for a node given its id.
        Uses the _node_index built at init.
        """
        node = self._node_index.get(node_id)
        return node.file_rel_path.replace("\\", "/") if node else None

    # ── reporting ─────────────────────────────────────────────────────────

    def print_call_graph(self, call_graph: CallGraph) -> None:
        """
        Print the call graph grouped by caller, mirroring the SymbolResolver
        print format where each import source is printed once as a header
        with its resolved symbols listed beneath.

        Format:
            caller_name  (file:line)
                [RESOLUTION]  callee_name  ->  callee_file:line  (node_type name)
                [RESOLUTION]  callee_name  ->  callee_file:line  (node_type name)
        """
        if len(call_graph) == 0:
            print("  (empty)")
            return

        counts: Dict[str, int] = {"LOCAL": 0, "IMPORTED": 0, "EXTERNAL": 0, "UNRESOLVED": 0}

        for caller_id, edges in call_graph._by_caller.items():
            caller = self._node_index.get(caller_id)
            caller_name = (caller.qualified_name or caller.name) if caller else caller_id
            caller_loc  = f"{caller.file_rel_path}:{caller.start_line}" if caller else "?"
            print(f"  {caller_name}  ({caller_loc})")

            for edge in edges:
                callee = self._node_index.get(edge.callee_node_id)
                site   = self._node_index.get(edge.call_site_node_id)

                callee_name = (callee.qualified_name or callee.name) if callee else (edge.callee_node_id or "UNRESOLVED")
                callee_loc  = (
                    f"{callee.file_rel_path}:{callee.start_line}"
                    f"  ({callee.node_type}  {callee.name})"
                    if callee else "—"
                )
                site_line = f"line {site.start_line}" if site else "?"

                counts[edge.resolution] = counts.get(edge.resolution, 0) + 1
                print(
                    f"      [{edge.resolution}]  "
                    f"{edge.edge_type}  "
                    f"{callee_name}  ->  {callee_loc}"
                    f"  @{site_line}"
                )

        total = len(call_graph)
        print(
            f"\n  TOTAL : {total}  |  "
            f"LOCAL : {counts['LOCAL']}  |  "
            f"IMPORTED : {counts['IMPORTED']}  |  "
            f"EXTERNAL : {counts.get('EXTERNAL', 0)}  |  "
            f"UNRESOLVED : {counts.get('UNRESOLVED', 0)}"
        )

    def print_sorted_graph(self, call_graph: CallGraph) -> None:
        """
        Print the call graph grouped by caller, mirroring the SymbolResolver
        print format where each import source is printed once as a header
        with its resolved symbols listed beneath.

        Format:
            caller_name  (file:line)
                [RESOLUTION]  callee_name  ->  callee_file:line  (node_type name)
                [RESOLUTION]  callee_name  ->  callee_file:line  (node_type name)

        Structure :
            Local : 
            ...
            Imported :
            ...
            Unresolved :
            ...
        """
        if len(call_graph) == 0:
            print("  (empty)")
            return

        local_groups: Dict[str, List[CallEdge]] = {}
        imported_groups: Dict[str, List[CallEdge]] = {}
        unresolved_groups: Dict[str, List[CallEdge]] = {}

        for caller_id, edges in call_graph._by_caller.items():
            for edge in edges:
                if edge.resolution == "LOCAL":
                    local_groups.setdefault(caller_id, []).append(edge)
                elif edge.resolution == "IMPORTED":
                    imported_groups.setdefault(caller_id, []).append(edge)
                else:
                    unresolved_groups.setdefault(caller_id, []).append(edge)

        categories = [
            ("Local", local_groups),
            ("Imported", imported_groups),
            ("Unresolved", unresolved_groups),
        ]

        for cat_name, cat_data in categories:
            print(f"  {cat_name} :")
            if not cat_data:
                continue

            sorted_callers = []
            for caller_id, edges in cat_data.items():
                caller = self._node_index.get(caller_id)
                caller_name = (caller.qualified_name or caller.name) if caller else caller_id
                caller_loc  = f"{caller.file_rel_path}:{caller.start_line}" if caller else "?"
                sorted_callers.append((caller_name, caller_loc, edges))

            # Sort callers by caller_name, then caller_loc
            sorted_callers.sort(key=lambda x: (x[0], x[1]))

            for caller_name, caller_loc, edges in sorted_callers:
                print(f"    {caller_name}  ({caller_loc})")

                sorted_edges = []
                for edge in edges:
                    callee = self._node_index.get(edge.callee_node_id)
                    site   = self._node_index.get(edge.call_site_node_id)

                    callee_name = (callee.qualified_name or callee.name) if callee else edge.callee_node_id
                    callee_loc  = (
                        f"{callee.file_rel_path}:{callee.start_line}"
                        f"  ({callee.node_type}  {callee.name})"
                        if callee else edge.callee_node_id
                    )
                    site_line = site.start_line if site else 0
                    sorted_edges.append((site_line, callee_name, callee_loc, edge))

                # Sort edges by call site line number, then callee name
                sorted_edges.sort(key=lambda x: (x[0], x[1]))

                for _, callee_name, callee_loc, edge in sorted_edges:
                    print(
                        f"        [{edge.resolution}]  "
                        f"{callee_name}  ->  {callee_loc}"
                    )
