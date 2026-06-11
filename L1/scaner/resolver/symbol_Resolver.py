"""
symbol_Resolver.py

The Linker of the V3RTEX engine.
Takes every import node found by the AST extractor and traces it to the real
file and node it references inside the project.

Input  : List[File]  (with .nodes populated by the AST extractor)
Output : SymbolMap   Dict[str, str]
           key   → "<import_node_id>::<symbol_name>"
           value → target_node_id

Imports that cannot be resolved to a project file (numpy, react, fastapi …)
are marked EXTERNAL in node.metadata and silently skipped.

Supported languages : Python · JavaScript · TypeScript · JSX · TSX
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from compBlocs12 import File, Node, SymbolMap


# ─────────────────────────────────────────────────────────────────────────────
# Language-specific path resolvers
# ─────────────────────────────────────────────────────────────────────────────

class PathResolver(ABC):
    """
    Converts an import string to the project-relative file path it targets.
    Returns None when the import is external or genuinely unresolvable.

    Design rationale: Python and JS/TS have fundamentally different import
    semantics (dot-notation vs. slash paths, relative anchoring, alias systems).
    An ABC with one concrete class per language keeps each resolver cohesive,
    independently understandable, and easy to extend for new languages.
    """

    @abstractmethod
    def resolve(
        self,
        module_str: str,
        source_rel_path: str,
        project_files: Dict[str, File],
    ) -> Optional[str]:
        """Return a key present in project_files, or None."""
        pass

    # ── shared probing helpers ────────────────────────────────────────────

    def _probe(
        self,
        base: str,
        extensions: List[str],
        project_files: Dict[str, File],
    ) -> Optional[str]:
        """Try each extension appended to base; return first match."""
        for ext in extensions:
            candidate = base + ext
            if candidate in project_files:
                return candidate
        return None

    def _probe_index(
        self,
        directory: str,
        extensions: List[str],
        index_names: List[str],
        project_files: Dict[str, File],
    ) -> Optional[str]:
        """Try index file names inside a directory (e.g. __init__.py, index.ts)."""
        for name in index_names:
            for ext in extensions:
                candidate = f"{directory}/{name}{ext}"
                if candidate in project_files:
                    return candidate
        return None


class PythonPathResolver(PathResolver):
    """
    Resolves Python import module strings to project-relative paths.

    Official Python import system rules (PEP 328, importlib documentation):

    Absolute imports
        'services.auth'        →  services/auth.py
                               or services/auth/__init__.py

    Relative imports  (dot prefix encodes how many package levels to go up)
        '.'                    →  <source_package>/__init__.py
        '.auth'                →  <source_package>/auth.py
        '..'                   →  <parent_package>/__init__.py
        '..models'             →  <parent_package>/models.py

    Dot-to-slash mapping:
        1 leading dot  → stay in the source file's own directory (level 0 up)
        2 leading dots → go up 1 level from source file's directory
        N leading dots → go up N-1 levels
    """

    _EXT   = ['.py']
    _INIT  = '__init__'

    def resolve(
        self,
        module_str: str,
        source_rel_path: str,
        project_files: Dict[str, File],
    ) -> Optional[str]:
        if not module_str:
            return None

        dot_count   = len(module_str) - len(module_str.lstrip('.'))
        module_body = module_str.lstrip('.')

        if dot_count:
            base_dir = self._relative_base(source_rel_path, dot_count)
            if base_dir is None:
                return None
            path = (
                f"{base_dir}/{module_body.replace('.', '/')}"
                if module_body else base_dir
            )
        else:
            path = module_str.replace('.', '/')

        path = path.strip('/')

        # Try direct .py file, then package __init__.py
        return (
            self._probe(path, self._EXT, project_files)
            or self._probe_index(path, self._EXT, [self._INIT], project_files)
        )

    def _relative_base(self, source_rel_path: str, dot_count: int) -> Optional[str]:
        """
        Compute the package directory that dot_count dots reference.

            source = services/auth/routes.py
            1 dot  → services/auth   (the file's own package)
            2 dots → services        (one level up)
            3 dots → ""              (project root)
        """
        parts      = source_rel_path.replace('\\', '/').split('/')
        dir_parts  = parts[:-1]        # strip filename
        levels_up  = dot_count - 1     # 1 dot = no move, 2 dots = 1 level up

        if levels_up > len(dir_parts):
            return None

        remaining = dir_parts[:-levels_up] if levels_up else dir_parts
        return '/'.join(remaining)


class JSPathResolver(PathResolver):
    """
    Resolves JS / TS module specifiers to project-relative paths.

    Official Node.js + TypeScript module resolution rules:

    Relative specifiers  (start with  .  or  ..)
        './utils'          →  <source_dir>/utils.ts  (or .tsx/.js/.jsx)
        '../models/user'   →  <source_parent>/models/user.ts
        './Button.tsx'     →  <source_dir>/Button.tsx  (explicit extension)

    Bare specifiers  (no leading . or /)
        'react', 'lodash'  →  EXTERNAL (node_modules); always None here

    Path aliases  (tsconfig paths / webpack aliases, supplied by caller)
        '@/components/Button'  →  src/components/Button.ts  (given "@/": "src/")

    Extension probing order  (TypeScript-first for TS-heavy projects):
        .ts → .tsx → .js → .jsx

    Directory imports:
        './components'  →  ./components/index.ts  (or .tsx/.js/.jsx)
        './lib'         →  ./lib/package.json → main field  (fallback)
    """

    _EXTS    = ['.ts', '.tsx', '.js', '.jsx']
    _INDEX   = ['index']
    _KNOWN   = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

    def __init__(self, aliases: Dict[str, str], project_root: str):
        self._aliases      = aliases
        self._project_root = project_root
        self._pkg_cache: Dict[str, Optional[str]] = {}

    def resolve(
        self,
        module_str: str,
        source_rel_path: str,
        project_files: Dict[str, File],
    ) -> Optional[str]:
        if not module_str:
            return None

        resolved, aliased = self._apply_aliases(module_str)

        # Bare specifier with no alias match → external package (node_modules)
        if not aliased and not resolved.startswith('.') and not resolved.startswith('/'):
            return None

        source_dir = '/'.join(source_rel_path.replace('\\', '/').split('/')[:-1])

        if resolved.startswith('.') and not aliased:
            # Relative to the importing file's directory
            path = os.path.normpath(
                os.path.join(source_dir, resolved)
            ).replace('\\', '/')
        else:
            # Root-relative: alias result or absolute-style specifier
            path = resolved.lstrip('/')

        # Specifier already carries a known extension (e.g. './foo.ts')
        _, ext = os.path.splitext(path)
        if ext in self._KNOWN:
            if path in project_files:
                return path
            path = path[: -len(ext)]  # strip and probe without extension

        return (
            self._probe(path, self._EXTS, project_files)
            or self._probe_index(path, self._EXTS, self._INDEX, project_files)
            or self._try_package_main(path, project_files)
        )

    def _apply_aliases(self, module_str: str) -> tuple:
        """Returns (resolved_str, was_aliased)."""
        for alias, replacement in self._aliases.items():
            if module_str.startswith(alias):
                return replacement + module_str[len(alias):], True
        return module_str, False

    def _try_package_main(
        self, directory: str, project_files: Dict[str, File]
    ) -> Optional[str]:
        """
        Read package.json 'main' or 'module' field for directory-style imports.
        Result is cached to avoid repeated disk reads on large projects.
        """
        if directory in self._pkg_cache:
            cached = self._pkg_cache[directory]
            return cached if cached in project_files else None

        pkg_json = os.path.join(
            self._project_root,
            directory.replace('/', os.sep),
            'package.json',
        )
        result: Optional[str] = None
        if os.path.isfile(pkg_json):
            try:
                with open(pkg_json, encoding='utf-8') as f:
                    data   = json.load(f)
                    main   = data.get('main') or data.get('module')
                    if main:
                        result = os.path.normpath(
                            os.path.join(directory, main)
                        ).replace('\\', '/')
            except (OSError, json.JSONDecodeError, ValueError):
                pass

        self._pkg_cache[directory] = result
        return result if result and result in project_files else None


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class SymbolResolver:
    """
    The Linker of V3RTEX.

    Iterates every import node in every file, delegates path resolution to the
    appropriate language resolver, looks up each imported symbol in the target
    file's node list, and builds the SymbolMap.

    Each import node's metadata is updated in place:
        resolution        = 'INTERNAL' | 'EXTERNAL' | 'UNRESOLVED'
        target_file_path  = <relative path>   (INTERNAL only)
        module            = <raw module str>  (EXTERNAL only, for reference)

    No exception is ever raised for an unresolved import; it is simply flagged.
    """

    _PYTHON_EXTS = {'.py'}

    def __init__(
        self,
        files: List[File],
        aliases: Dict[str, str] = None,
        project_root: str = '',
    ):
        """
        :param files:        All File objects produced by the AST extractor.
        :param aliases:      Path alias map,  e.g.  {"@/": "src/", "~": "src/"}.
        :param project_root: Absolute path to the project root directory.
                             Used only for package.json lookups in JS/TS projects.
        """
        self._files = {
            f.relative_path.replace('\\', '/'): f for f in files
        }
        self._python_resolver = PythonPathResolver()
        self._js_resolver     = JSPathResolver(aliases or {}, project_root)

        # Built once; queried O(1) per symbol lookup.
        # Maps  rel_path  →  { symbol_name: node_id }
        # for all importable top-level definitions in the project.
        self._file_symbols: Dict[str, Dict[str, str]] = self._index_by_file(files)

    # ── public API ────────────────────────────────────────────────────────

    def produce_symbol_map(self) -> Dict[str, str]:
        """
        Resolve all imports across every file in the project.

        Returns
        -------
        SymbolMap
            Queryable via  .get_target(import_node_id, symbol_name)
                       and .get_symbols(import_node_id)
        """
        symbol_map = SymbolMap()

        for rel_path, file_obj in self._files.items():
            for node in file_obj.nodes:
                if node.category == 'imports':
                    self._resolve_one(node, rel_path, symbol_map)

        return symbol_map

    # ── internal resolution logic ─────────────────────────────────────────

    def _resolve_one(
        self,
        imp_node: Node,
        source_rel_path: str,
        symbol_map: Dict[str, str],
    ) -> None:
        module_str = self._module_str(imp_node)

        if not module_str:
            imp_node.metadata['resolution'] = 'UNRESOLVED'
            symbol_map.add(imp_node.id, imp_node.name or '', None)
            return

        resolver    = self._resolver_for(source_rel_path)
        target_path = resolver.resolve(module_str, source_rel_path, self._files)

        if not target_path:
            imp_node.metadata['resolution'] = 'EXTERNAL'
            imp_node.metadata['module']     = module_str
            # Emit unresolvable entries so the DB captures every import
            for sym_name in self._symbols(imp_node) or [module_str]:
                symbol_map.add(imp_node.id, sym_name, None, external_module=module_str)
            return

        imp_node.metadata['resolution']       = 'INTERNAL'
        imp_node.metadata['target_file_path'] = target_path

        is_star = (
            imp_node.metadata.get('is_star')
            or imp_node.metadata.get('namespace_import')
        )
        symbols = self._symbols(imp_node)

        if is_star or not symbols:
            # Star import or bare 'import module': link all definitions in the target
            for name, node_id in self._file_symbols.get(target_path, {}).items():
                symbol_map.add(imp_node.id, name, node_id)
            return

        for sym_name in symbols:
            node_id = self._file_symbols.get(target_path, {}).get(sym_name)
            if node_id:
                symbol_map.add(imp_node.id, sym_name, node_id)
            else:
                # Python edge case: 'from . import auth' where 'auth' is a submodule
                sub_id = self._try_as_submodule(sym_name, target_path)
                if sub_id:
                    symbol_map.add(imp_node.id, sym_name, sub_id)
                else:
                    # Follow re-export chain through barrel files
                    trace = self._trace_origin(sym_name, target_path)
                    if trace:
                        symbol_map.add(imp_node.id, sym_name, trace["node_id"], trace["hops"])
                    else:
                        # Symbol exists in source but cannot be traced to a definition
                        symbol_map.add(imp_node.id, sym_name, None)

    def _try_as_submodule(self, sym_name: str, target_path: str) -> Optional[str]:
        """
        Handles the Python pattern  'from . import auth'  where 'auth' is not a
        name defined in __init__.py but is itself a sibling module file.

        Only attempted when the resolved target is a package __init__.py.
        """
        if not target_path.endswith('/__init__.py'):
            return None

        package_dir = target_path[: -len('/__init__.py')]
        candidate   = f"{package_dir}/{sym_name}.py"
        if candidate in self._files:
            return self._files[candidate].id

        # Also try it as a sub-package
        sub_init = f"{package_dir}/{sym_name}/__init__.py"
        if sub_init in self._files:
            return self._files[sub_init].id

        return None

    def _trace_origin(
        self,
        symbol_name: str,
        current_path: str,
        visited: set = None,
        hops: list = None,
    ) -> Optional[dict]:
        """
        Follow re-export chains from current_path until the file that actually
        defines symbol_name is found.

        Returns:
            {
                "node_id": str,           the defining node's ID
                "origin":  str,           the file that owns the definition
                "hops":    [str, ...],    full path from first door to origin
            }
        or None if the symbol cannot be traced to any definition.
        """
        if visited is None:
            visited = set()
        if hops is None:
            hops = []

        if current_path in visited:
            return None                   # cycle guard

        visited = visited | {current_path}
        hops    = hops + [current_path]

        file_obj = self._files.get(current_path)
        if not file_obj:
            return None

        for node in file_obj.nodes:
            # Only consider nodes explicitly flagged as re-exports
            if not node.metadata.get("is_reexport"):
                continue
            if node.category not in ("imports", "exports"):
                continue

            symbols = self._symbols(node)
            is_star = node.metadata.get("is_star")

            if symbol_name not in symbols and not is_star:
                continue                  # this re-export does not pass our symbol

            # Resolve the source file this re-export points to
            module_str  = self._module_str(node)
            if not module_str:
                continue

            resolver    = self._resolver_for(current_path)
            source_path = resolver.resolve(module_str, current_path, self._files)
            if not source_path:
                continue

            # Check if the symbol is directly defined in the source file
            node_id = self._file_symbols.get(source_path, {}).get(symbol_name)
            if node_id:
                return {
                    "node_id": node_id,
                    "origin":  source_path,
                    "hops":    hops + [source_path],
                }

            # Source file may itself be a barrel — recurse
            result = self._trace_origin(symbol_name, source_path, visited, hops)
            if result:
                return result

        return None

    # ── metadata accessors ────────────────────────────────────────────────

    def _module_str(self, imp_node: Node) -> Optional[str]:
        """
        Read the module/specifier string from node metadata.

        Python metadata key : 'module'           e.g.  'services.auth'
        JS/TS metadata key  : 'module_specifier' e.g.  './services/auth'
        Fallback            : imp_node.name       (what the extractor stored as name)
        """
        meta = imp_node.metadata
        return meta.get('module') or meta.get('module_specifier') or imp_node.name

    def _symbols(self, imp_node: Node) -> List[str]:
        """
        Return the list of symbol names being imported.

        Python : metadata['symbols']       = ['verify_token', 'create_user']
        JS/TS  : metadata['named_imports'] = [{'name': 'x', 'alias': 'y'}]
                 metadata['default_import']= 'Component'
        """
        meta   = imp_node.metadata
        result = []

        if 'symbols' in meta:
            return [s for s in meta['symbols'] if s]

        for item in meta.get('named_imports', []):
            result.append(item['name'] if isinstance(item, dict) else item)

        default = meta.get('default_import')
        if default:
            result.append(default)

        return result

    # ── one-time indexes ──────────────────────────────────────────────────

    def _resolver_for(self, rel_path: str) -> PathResolver:
        ext = os.path.splitext(rel_path)[1].lower()
        return (
            self._python_resolver if ext in self._PYTHON_EXTS
            else self._js_resolver
        )

    def _index_by_file(self, files: List[File]) -> Dict[str, Dict[str, str]]:
        """
        Build a per-file name → node_id lookup for every importable definition.

        Only top-level-ish definitions (functions, classes, variables, types,
        interfaces) are indexed — not call sites, comments, or raw imports.
        This matches what a consumer of the project can actually import.
        """
        importable = {'functions', 'classes', 'variables', 'types', 'interfaces'}
        index: Dict[str, Dict[str, str]] = {}

        for f in files:
            rel   = f.relative_path.replace('\\', '/')
            names: Dict[str, str] = {}
            for node in f.nodes:
                if node.category in importable and node.name:
                    if node.category == 'variables' and not node.metadata.get('is_module_level'):
                        continue
                    names[node.name] = node.id
            index[rel] = names

        return index

    def print_symbol_map(self, symbol_map: SymbolMap) -> None:
        """
        Print every resolved import → definition link, one line per reference.

        Each import source is printed once as a header, with the symbols it
        pulls in listed beneath it — so a multi-symbol import never repeats its
        own location:

            <source_file>:<line>
                <symbol>  →  <target_file>:<line>  (<type> <name>)

        IDs that can't be resolved back to a Node/File (rare edge cases) fall
        back to printing the raw id so nothing is silently dropped.
        """
        node_index = {
            node.id: node
            for f in self._files.values()
            for node in f.nodes
        }
        file_index = {f.id: f for f in self._files.values()}

        if len(symbol_map) == 0:
            print("  (empty)")
            return

        for import_id, symbols in symbol_map._by_import.items():
            src = node_index.get(import_id)
            src_loc = f"{src.file_rel_path}:{src.start_line}" if src else import_id
            print(f"  {src_loc}")

            for symbol_name, target_id in symbols.items():
                target = node_index.get(target_id)
                if target:
                    tgt_loc = (
                        f"{target.file_rel_path}:{target.start_line} "
                        f"({target.node_type} {target.name})"
                    )
                elif target_id in file_index:
                    tgt_loc = f"{file_index[target_id].relative_path}:1 (module)"
                else:
                    tgt_loc = target_id

                print(f"      {symbol_name}  ->  {tgt_loc}")
    