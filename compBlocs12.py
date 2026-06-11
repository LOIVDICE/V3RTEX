"""
This script is use dto create every component in the project
This script contains the class definitions and building blocs which will be used all through 
Following OOP principles.

Objects : Directory, File, Node
"""

class Directory:
    def __init__(
        self, 
        path: str, #the path of the directory example: "src/main/java/com/example"
        name: str, #the name of the directory example: "com/example"
        relative_path: str, #the relative path of the directory example: "src/main/java/com/example"
        files: list = [], #the files in the directory example: [File(path="src/main/java/com/example/Main.java", name="Main.java", relative_path="src/main/java/com/example/Main.java", language="java", size=1000, last_modified=1717334400.0, hash="1234567890", line_count=100, encoding="utf-8", is_empty=False, is_large=False, has_syntax_errors=False, warnings=["Warning: File is too large"], nodes=[Node(category="function", node_type="function", name="main", start_line=1, end_line=10, start_column=1, end_column=10, text="public static void main(String[] args) { System.out.println("Hello, World!"); }")])]
    ):
        self.path = path
        self.name = name
        self.relative_path = relative_path
        self.files = files
        self.id = self.create_directory_id()

    def create_directory_id(self):
        return f"{self.relative_path}.{self.name}"

    def __str__(self):
        return f"{self.path} - {self.name} - {self.relative_path}"

    def __repr__(self):
        rel_path = self.relative_path.replace("\\", ".").replace("//", ".")
        path = self.path.replace("\\", ".").replace("//", ".")
        return f"Directory(path={path!r}, name={self.name!r}, relative_path={rel_path!r})"


class File:
    def __init__(
        self,
        path: str, #the path of the file example: "src/main/java/com/example/Main.java"
        name: str, #the name of the file example: "Main.java"
        relative_path: str, #the relative path of the file example: "src/main/java/com/example/Main.java"
        language: str, #the language of the file example: "java"
        size: int, #the size of the file example: 1000
        last_modified: float, #the last modified date of the file example: 1717334400.0
        hash: str, #the hash of the file example: "1234567890"
        line_count: int = 0, #the number of lines in the file example: 100
        encoding: str = "utf-8", #the encoding of the file example: "utf-8"
        is_empty: bool = False, #whether the file is empty example: False
        is_large: bool = False, #whether the file is large example: False
        has_syntax_errors: bool = False, #whether the file has syntax errors example: False
        warnings: list = None, #the warnings of the file example: ["Warning: File is too large"]
        nodes: list = None, #the nodes of the file example: [Node(category="function", node_type="function", name="main", start_line=1, end_line=10, start_column=1, end_column=10, text="public static void main(String[] args) { System.out.println("Hello, World!"); }")]
    ):
        self.path = path
        self.relative_path = relative_path
        self.language = language
        self.name = name
        self.size = size
        self.last_modified = last_modified
        self.hash = hash
        self.line_count = line_count
        self.encoding = encoding
        self.is_empty = True if size == 0 else False
        self.is_large = True if size > 1_000_000 else False
        self.has_syntax_errors = False
        self.warnings = warnings or []
        self.nodes = nodes or []
        self.id = self.create_file_id()

    def create_file_id(self):
        rel_path = self.relative_path.replace("\\", ".").replace("//", ".")
        return f"{rel_path}.{self.name}.{self.language}"

    def __repr__(self):
        return (
            f"File(id={self.id!r}, name={self.name!r}, "
            f"language={self.language!r}, path={self.relative_path!r}, "
            f"lines={self.line_count}, empty={self.is_empty}, "
            f"large={self.is_large}, errors={self.has_syntax_errors})"
        )

    def __str__(self):
        return f"File({self.relative_path})"


class Node:
    def __init__(
        self,
        file_rel_path: str, #the relative path of the file example: "src/main/java/com/example/Main.java"
        category: str, #the category of the node example: "function", "class", "variable", "import", "etc."
        node_type: str, 
        start_line: int, #the start line of the node example: 1
        end_line: int, #the end line of the node example: 10
        start_column: int, #the start column of the node example: 1
        end_column: int, #the end column of the node example: 10
        text: str, #the text of the node example: "public class Main { public static void main(String[] args) { System.out.println("Hello, World!"); } }"
        name: str = None, #the name of the node example: "Main"
        qualified_name: str = None, #the qualified name of the node example: "com.example.Main"
        parent: 'Node' = None, #the parent of the node example: "com.example.Main"
        metadata: dict = None, #the metadata of the node example: { "parameters": ["String[] args"], "return_type": "void", "docstring": "Main function", "is_async": false, "is_anonymous": false }
    ):
        self.file_rel_path = file_rel_path
        self.category = category
        self.node_type = node_type
        self.start_line = start_line
        self.end_line = end_line
        self.start_column = start_column
        self.end_column = end_column
        self.text = text
        self.name = name
        self.qualified_name = qualified_name
        self.parent = parent
        self.children = []
        self.metadata = metadata or {}
        self.id = self.generate_node_id()

    def generate_node_id(self):
        return f"{self.file_rel_path}.{self.node_type}.{self.name}.{self.start_line}"

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "node_type": self.node_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_column": self.start_column,
            "end_column": self.end_column,
            "text": self.text,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "parent_id": self.parent.id if self.parent else None,
            "children_ids": [child.id for child in self.children],
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"Node(category={self.category}, node_type={self.node_type}, name={self.name}, start_line={self.start_line}, end_line={self.end_line})"


class CallEdge:
    """
    A single directed edge in the call graph.

    edge_type  : "CALLS" when the callee is a function/method/class
                 "USES"  when the callee is a module-level variable/constant
    resolution : "LOCAL"    — callee defined in the same file
                 "IMPORTED" — callee traced through the SymbolMap
                 "UNRESOLVED" — could not be resolved to a definition
    hops       : import chain from SymbolMap (empty for LOCAL)
    """

    def __init__(
        self,
        caller_node_id:    str,
        callee_node_id:    str | None,   # None when the call could not be resolved
        call_site_node_id: str,
        edge_type:         str,
        resolution:        str,
        hops:              list = None,
    ):
        self.caller_node_id    = caller_node_id
        self.callee_node_id    = callee_node_id
        self.call_site_node_id = call_site_node_id
        self.edge_type         = edge_type
        self.resolution        = resolution
        self.hops              = hops or []

    def __repr__(self):
        return (
            f"CallEdge({self.edge_type} {self.resolution}: "
            f"{self.caller_node_id!r} → {self.callee_node_id!r})"
        )


class CallGraph:
    """
    The output of CallResolver.
    Stores every CALLS / USES edge in the project and exposes
    bidirectional lookup by caller or callee node id.
    """

    def __init__(self):
        self._edges:     list = []
        self._by_caller: dict = {}   # caller_node_id → [CallEdge, ...]
        self._by_callee: dict = {}   # callee_node_id → [CallEdge, ...]
        self._seen:      set  = set()  # (caller_id, callee_id, call_site_id)

    def add(self, edge: CallEdge) -> None:
        key = (edge.caller_node_id, edge.callee_node_id, edge.call_site_node_id)
        if key in self._seen:
            return
        self._seen.add(key)
        self._edges.append(edge)
        self._by_caller.setdefault(edge.caller_node_id, []).append(edge)
        self._by_callee.setdefault(edge.callee_node_id, []).append(edge)

    def get_callers(self, node_id: str) -> list:
        """Return all edges where node_id is the callee — who calls this?"""
        return self._by_callee.get(node_id, [])

    def get_callees(self, node_id: str) -> list:
        """Return all edges where node_id is the caller — what does this call?"""
        return self._by_caller.get(node_id, [])

    def all_edges(self) -> list:
        return list(self._edges)

    def __len__(self) -> int:
        return len(self._edges)

    def __repr__(self) -> str:
        return f"CallGraph({len(self._edges)} edges)"


class SymbolMap:
    """
    The output of the SymbolResolver.
    Stores confirmed import-to-definition connections and exposes
    them through named accessors instead of raw key manipulation.

    Entries are keyed internally as  "<import_node_id>::<symbol_name>"
    but callers never need to know or construct that string.
    """

    def __init__(self):
        # Each entry stores {"node_id": str, "hops": [str, ...]}
        self._entries: dict = {}      # "import_node_id::symbol" → entry
        self._by_import: dict = {}    # import_node_id → {symbol: entry}

    def add(
        self,
        import_node_id:  str,
        symbol_name:     str,
        target_node_id:  str | None,       # None for EXTERNAL / UNRESOLVED
        hops:            list = None,
        external_module: str | None = None, # raw module string when target is external
    ) -> None:
        entry = {
            "node_id":         target_node_id,
            "hops":            hops or [],
            "external_module": external_module,
        }
        self._entries[f"{import_node_id}::{symbol_name}"] = entry
        self._by_import.setdefault(import_node_id, {})[symbol_name] = entry

    def get_target(self, import_node_id: str, symbol_name: str):
        """Return the target node ID for one specific symbol, or None."""
        entry = self._by_import.get(import_node_id, {}).get(symbol_name)
        return entry["node_id"] if entry else None

    def get_symbols(self, import_node_id: str) -> dict:
        """Return all  { symbol_name: target_node_id }  pairs for one import node."""
        return {
            sym: entry["node_id"]
            for sym, entry in self._by_import.get(import_node_id, {}).items()
        }

    def get_lineage(self, import_node_id: str, symbol_name: str) -> dict:
        """
        Return the full trace for one symbol:
            { "node_id": str, "hops": [door_file, ..., origin_file] }
        Returns None when the symbol was not resolved.
        """
        return self._by_import.get(import_node_id, {}).get(symbol_name)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"SymbolMap({len(self._entries)} entries)"