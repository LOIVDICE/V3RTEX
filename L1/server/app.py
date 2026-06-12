"""
server/app.py

HTTP API for the V3RTEX database.

Endpoints
---------
    GET /              — API overview + row counts
    GET /files         — source files          (?language=, ?limit=, ?offset=)
    GET /files/{id}    — one file + its nodes
    GET /nodes         — AST nodes             (?file_id=, ?category=, ?name=, ?limit=, ?offset=)
    GET /nodes/{id}    — one node
    GET /symbols       — all imports (symbol edges)   (?resolution=, ?symbol=, ?limit=, ?offset=)
    GET /calls         — all calls (call graph edges) (?resolution=, ?caller=, ?callee=, ?limit=, ?offset=)
"""

from fastapi import FastAPI, HTTPException, Query

from sql_Bd import DatabaseManager


def _rows(cursor) -> list:
    return [dict(r) for r in cursor.fetchall()]


def create_app(db: DatabaseManager) -> FastAPI:
    app = FastAPI(title="V3RTEX API", description="Serves the V3RTEX code-graph database.")

    # ── root ──────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        return {
            "endpoints": ["/files", "/files/{id}", "/nodes", "/nodes/{id}", "/symbols", "/calls"],
            "stats": db.stats(),
        }

    # ── files ─────────────────────────────────────────────────────────────

    @app.get("/files")
    def list_files(
        language: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        query  = "SELECT * FROM files"
        params = []
        if language:
            query += " WHERE language = ?"
            params.append(language)
        query += " ORDER BY relative_path LIMIT ? OFFSET ?"
        params += [limit, offset]

        with db.get_connection() as conn:
            files = _rows(conn.execute(query, params))
        return {"count": len(files), "files": files}

    @app.get("/files/{file_id}")
    def get_file(file_id: str):
        file = db.get_file(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail=f"file not found: {file_id}")
        file["nodes"] = db.get_nodes(file_id)
        return file

    # ── nodes ─────────────────────────────────────────────────────────────

    @app.get("/nodes")
    def list_nodes(
        file_id: str | None = None,
        category: str | None = None,
        name: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        query   = "SELECT * FROM nodes"
        clauses = []
        params  = []
        if file_id:
            clauses.append("file_id = ?")
            params.append(file_id)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if name:
            clauses.append("name LIKE ?")
            params.append(f"%{name}%")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY file_id, start_line LIMIT ? OFFSET ?"
        params += [limit, offset]

        with db.get_connection() as conn:
            nodes = _rows(conn.execute(query, params))
        return {"count": len(nodes), "nodes": nodes}

    @app.get("/nodes/{node_id}")
    def get_node(node_id: str):
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"node not found: {node_id}")
        return dict(row)

    # ── symbols: all imports ──────────────────────────────────────────────

    @app.get("/symbols")
    def list_symbols(
        resolution: str | None = None,
        symbol: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        query = """
            SELECT se.*,
                   i.text           AS import_text,
                   i.file_id        AS import_file_id,
                   t.name           AS target_name,
                   t.qualified_name AS target_qualified_name,
                   t.file_id        AS target_file_id
            FROM symbol_edges se
            LEFT JOIN nodes i ON se.import_node_id = i.id
            LEFT JOIN nodes t ON se.target_node_id = t.id
        """
        clauses = []
        params  = []
        if resolution:
            clauses.append("se.resolution = ?")
            params.append(resolution.upper())
        if symbol:
            clauses.append("se.symbol_name LIKE ?")
            params.append(f"%{symbol}%")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY se.id LIMIT ? OFFSET ?"
        params += [limit, offset]

        with db.get_connection() as conn:
            symbols = _rows(conn.execute(query, params))
        return {"count": len(symbols), "symbols": symbols}

    # ── calls: all call graph edges ───────────────────────────────────────

    @app.get("/calls")
    def list_calls(
        resolution: str | None = None,
        caller: str | None = None,
        callee: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        query = """
            SELECT ce.*,
                   cr.name           AS caller_name,
                   cr.qualified_name AS caller_qualified_name,
                   cr.file_id        AS caller_file_id,
                   cl.name           AS callee_name,
                   cl.qualified_name AS callee_qualified_name,
                   cl.file_id        AS callee_file_id,
                   cs.text           AS call_site_text,
                   cs.start_line     AS call_site_line
            FROM call_edges ce
            LEFT JOIN nodes cr ON ce.caller_node_id    = cr.id
            LEFT JOIN nodes cl ON ce.callee_node_id    = cl.id
            LEFT JOIN nodes cs ON ce.call_site_node_id = cs.id
        """
        clauses = []
        params  = []
        if resolution:
            clauses.append("ce.resolution = ?")
            params.append(resolution.upper())
        if caller:
            clauses.append("cr.name LIKE ?")
            params.append(f"%{caller}%")
        if callee:
            clauses.append("cl.name LIKE ?")
            params.append(f"%{callee}%")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ce.id LIMIT ? OFFSET ?"
        params += [limit, offset]

        with db.get_connection() as conn:
            calls = _rows(conn.execute(query, params))
        return {"count": len(calls), "calls": calls}

    return app
