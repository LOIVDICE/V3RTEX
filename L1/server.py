"""
server.py

Entry point for the V3RTEX HTTP API.
Opens the SQLite database and serves it through the FastAPI app
defined in the server/ package.

Usage:
    python server.py
"""

import uvicorn

from sql_Bd import DatabaseManager
from server.app import create_app

DB_PATH = "v3rtex.db"
HOST    = "127.0.0.1"
PORT    = 7331

db  = DatabaseManager(DB_PATH)
app = create_app(db)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
