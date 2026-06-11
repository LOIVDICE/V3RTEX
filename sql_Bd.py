"""
sql_Bd.py

Database layer for V3RTEX.
Initializes the SQLite database and provides insert/query methods
for every data type produced by the pipeline.

Tables
------
    directories  — project folders          (file_Walker Stage 1)
    files        — source files             (file_Walker Stage 1)
    nodes        — all AST entities         (core_extractor Stage 2)
    symbol_edges — import resolution edges  (symbol_Resolver Stage 3)
    call_edges   — call graph edges         (call_Resolver Stage 4)
"""

import sqlite3
import json
from contextlib import contextmanager
from compBlocs12 import Directory, File, Node, SymbolMap, CallGraph


class DatabaseManager:
    """
    Manages the V3RTEX SQLite database.

    Usage:
        db = DatabaseManager("v3rtex.db")
        db.populate(files, symbol_map, call_graph)
    """

    def __init__(self, db_path: str = "v3rtex.db"):
        self.db_path = db_path
        self._init_db()

    # ── connection ────────────────────────────────────────────────────────

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            yield conn
        finally:
            conn.close()

    # ── schema ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create all tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            conn.executescript("""

                -- ── Stage 1: file discovery ──────────────────────────────

                CREATE TABLE IF NOT EXISTS directories (
                    id            TEXT PRIMARY KEY,
                    path          TEXT NOT NULL,
                    name          TEXT NOT NULL,
                    relative_path TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS files (
                    id                TEXT PRIMARY KEY,
                    directory_id      TEXT REFERENCES directories(id) ON DELETE SET NULL,
                    path              TEXT NOT NULL,
                    name              TEXT NOT NULL,
                    relative_path     TEXT NOT NULL,
                    language          TEXT NOT NULL,
                    size              INTEGER,
                    line_count        INTEGER,
                    encoding          TEXT,
                    hash              TEXT,
                    last_modified     REAL,
                    is_empty          INTEGER NOT NULL DEFAULT 0,
                    is_large          INTEGER NOT NULL DEFAULT 0,
                    has_syntax_errors INTEGER NOT NULL DEFAULT 0,
                    warnings          TEXT
                );

                -- ── Stage 2: AST extraction ───────────────────────────────

                CREATE TABLE IF NOT EXISTS nodes (
                    id             TEXT PRIMARY KEY,
                    file_id        TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    parent_id      TEXT REFERENCES nodes(id) ON DELETE SET NULL,
                    category       TEXT NOT NULL,
                    node_type      TEXT NOT NULL,
                    name           TEXT,
                    qualified_name TEXT,
                    start_line     INTEGER,
                    end_line       INTEGER,
                    start_column   INTEGER,
                    end_column     INTEGER,
                    text           TEXT,
                    metadata       TEXT
                );

                -- ── Stage 3: symbol resolution ────────────────────────────

                CREATE TABLE IF NOT EXISTS symbol_edges (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_node_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    symbol_name     TEXT NOT NULL,
                    target_node_id  TEXT REFERENCES nodes(id) ON DELETE SET NULL,
                    external_module TEXT,
                    resolution      TEXT NOT NULL,
                    hops            TEXT
                );

                -- ── Stage 4: call graph ───────────────────────────────────

                CREATE TABLE IF NOT EXISTS call_edges (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_node_id    TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    callee_node_id    TEXT REFERENCES nodes(id) ON DELETE SET NULL,
                    call_site_node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    edge_type         TEXT NOT NULL,
                    resolution        TEXT NOT NULL,
                    hops              TEXT
                );

                -- ── indexes ───────────────────────────────────────────────

                CREATE INDEX IF NOT EXISTS idx_files_dir        ON files(directory_id);
                CREATE INDEX IF NOT EXISTS idx_files_lang       ON files(language);
                CREATE INDEX IF NOT EXISTS idx_nodes_file       ON nodes(file_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_parent     ON nodes(parent_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_category   ON nodes(category);
                CREATE INDEX IF NOT EXISTS idx_nodes_name       ON nodes(name);
                CREATE INDEX IF NOT EXISTS idx_sym_import       ON symbol_edges(import_node_id);
                CREATE INDEX IF NOT EXISTS idx_sym_target       ON symbol_edges(target_node_id);
                CREATE INDEX IF NOT EXISTS idx_sym_resolution   ON symbol_edges(resolution);
                CREATE INDEX IF NOT EXISTS idx_call_caller      ON call_edges(caller_node_id);
                CREATE INDEX IF NOT EXISTS idx_call_callee      ON call_edges(callee_node_id);
                CREATE INDEX IF NOT EXISTS idx_call_resolution  ON call_edges(resolution);
            """)
            conn.commit()

    # ── insert: Stage 1 ──────────────────────────────────────────────────

    def insert_directory(self, directory: Directory) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO directories (id, path, name, relative_path) VALUES (?,?,?,?)",
                (directory.id, directory.path, directory.name, directory.relative_path)
            )
            conn.commit()

    def insert_file(self, file: File, directory_id: str = None) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO files
                   (id, directory_id, path, name, relative_path, language, size,
                    line_count, encoding, hash, last_modified,
                    is_empty, is_large, has_syntax_errors, warnings)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    file.id, directory_id, file.path, file.name,
                    file.relative_path, file.language, file.size,
                    file.line_count, file.encoding, file.hash, file.last_modified,
                    int(file.is_empty), int(file.is_large), int(file.has_syntax_errors),
                    json.dumps(file.warnings or []),
                )
            )
            conn.commit()

    # ── insert: Stage 2 ──────────────────────────────────────────────────

    def insert_node(self, node: Node, file_id: str) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO nodes
                   (id, file_id, parent_id, category, node_type, name, qualified_name,
                    start_line, end_line, start_column, end_column, text, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    node.id, file_id,
                    node.parent.id if node.parent else None,
                    node.category, node.node_type, node.name, node.qualified_name,
                    node.start_line, node.end_line,
                    node.start_column, node.end_column,
                    node.text, json.dumps(node.metadata or {}),
                )
            )
            conn.commit()

    def insert_nodes_bulk(self, nodes: list, file_id: str) -> None:
        """Insert all nodes for one file in a single transaction."""
        rows = [
            (
                node.id, file_id,
                node.parent.id if node.parent else None,
                node.category, node.node_type, node.name, node.qualified_name,
                node.start_line, node.end_line,
                node.start_column, node.end_column,
                node.text, json.dumps(node.metadata or {}),
            )
            for node in nodes
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO nodes
                   (id, file_id, parent_id, category, node_type, name, qualified_name,
                    start_line, end_line, start_column, end_column, text, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows
            )
            conn.commit()

    # ── insert: Stage 3 ──────────────────────────────────────────────────

    def insert_symbol_map(self, symbol_map: SymbolMap) -> None:
        """
        Persist every entry in the SymbolMap — resolved, external, and unresolved.
        Resolution is read from the entry itself (node_id=None → EXTERNAL or UNRESOLVED).
        """
        rows = []
        for import_id, symbols in symbol_map._by_import.items():
            for symbol_name, entry in symbols.items():
                target_id       = entry.get("node_id")
                external_module = entry.get("external_module")
                hops            = entry.get("hops", [])
                resolution      = (
                    "IMPORTED"   if target_id else
                    "EXTERNAL"   if external_module else
                    "UNRESOLVED"
                )
                rows.append((
                    import_id, symbol_name,
                    target_id, external_module,
                    resolution, json.dumps(hops),
                ))

        with self.get_connection() as conn:
            conn.executemany(
                """INSERT INTO symbol_edges
                   (import_node_id, symbol_name, target_node_id,
                    external_module, resolution, hops)
                   VALUES (?,?,?,?,?,?)""",
                rows
            )
            conn.commit()

    # ── insert: Stage 4 ──────────────────────────────────────────────────

    def insert_call_graph(self, call_graph: CallGraph) -> None:
        """Persist every edge in the CallGraph — LOCAL, IMPORTED, EXTERNAL, UNRESOLVED."""
        rows = [
            (
                edge.caller_node_id,
                edge.callee_node_id,
                edge.call_site_node_id,
                edge.edge_type,
                edge.resolution,
                json.dumps(edge.hops or []),
            )
            for edge in call_graph.all_edges()
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """INSERT INTO call_edges
                   (caller_node_id, callee_node_id, call_site_node_id,
                    edge_type, resolution, hops)
                   VALUES (?,?,?,?,?,?)""",
                rows
            )
            conn.commit()

    # ── populate: full pipeline ───────────────────────────────────────────

    def populate(
        self,
        files:       list,
        symbol_map:  SymbolMap,
        call_graph:  CallGraph,
        directories: list = None,
    ) -> None:
        """
        Store the complete output of all four pipeline stages.

        :param files:       List[File] with .nodes populated
        :param symbol_map:  SymbolMap from symbol_Resolver
        :param call_graph:  CallGraph from call_Resolver
        :param directories: Optional List[Directory] from file_Walker
        """
        # Build directory lookup: relative_path_prefix → directory_id
        dir_lookup = {}
        if directories:
            for d in directories:
                self.insert_directory(d)
                dir_lookup[d.relative_path.replace("\\", "/")] = d.id

        for file in files:
            # Match file to its directory by its folder path
            folder = "/".join(file.relative_path.replace("\\", "/").split("/")[:-1])
            directory_id = dir_lookup.get(folder)

            self.insert_file(file, directory_id)
            self.insert_nodes_bulk(file.nodes, file.id)

        self.insert_symbol_map(symbol_map)
        self.insert_call_graph(call_graph)

    # ── queries ───────────────────────────────────────────────────────────

    def get_directory(self, directory_id: str) -> dict:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM directories WHERE id = ?", (directory_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_file(self, file_id: str) -> dict:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE id = ?", (file_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_nodes(self, file_id: str) -> list:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE file_id = ? ORDER BY start_line", (file_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_callees(self, caller_node_id: str) -> list:
        """Which functions does this function call?"""
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT ce.*, n.name, n.file_id
                   FROM call_edges ce
                   LEFT JOIN nodes n ON ce.callee_node_id = n.id
                   WHERE ce.caller_node_id = ?""",
                (caller_node_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_callers(self, callee_node_id: str) -> list:
        """Which functions call this function?"""
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT ce.*, n.name, n.file_id
                   FROM call_edges ce
                   LEFT JOIN nodes n ON ce.caller_node_id = n.id
                   WHERE ce.callee_node_id = ?""",
                (callee_node_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        """Row counts for every table."""
        with self.get_connection() as conn:
            return {
                "directories": conn.execute("SELECT COUNT(*) FROM directories").fetchone()[0],
                "files":       conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
                "nodes":       conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
                "symbol_edges": conn.execute("SELECT COUNT(*) FROM symbol_edges").fetchone()[0],
                "call_edges":  conn.execute("SELECT COUNT(*) FROM call_edges").fetchone()[0],
            }
