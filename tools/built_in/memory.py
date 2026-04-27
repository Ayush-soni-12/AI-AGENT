import sqlite3
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class MemoryParams(BaseModel):
    action: Literal["set", "get", "search", "delete"] = Field(..., description="The action to perform on the memory database.")
    key: Optional[str] = Field(None, description="The unique key for the memory. Required for set, get, delete.")
    value: Optional[str] = Field(None, description="The content to store. Required for set.")
    query: Optional[str] = Field(None, description="The search term to look for. Required for search.")
    category: Optional[str] = Field("general", description="Optional category to group memories (e.g., 'coding_rules', 'user_preference', 'architecture').")

class MemoryTool(Tool):
    name = "memory"
    description = "Store, retrieve, or search long-term architectural rules or user preferences in a native project SQLite database."
    kind = ToolKind.MEMORY
    schema = MemoryParams

    def _get_db_path(self, cwd: Path) -> Path:
        return cwd / ".agent_memory.db"

    def _init_db(self, db_path: Path):
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = MemoryParams(**invocation.params)
        db_path = self._get_db_path(invocation.cwd)
        
        try:
            self._init_db(db_path)
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                if params.action == "set":
                    if not params.key or params.value is None:
                        return ToolResult.error_result("Action 'set' requires 'key' and 'value'.")
                        
                    cursor.execute(
                        "INSERT OR REPLACE INTO memories (key, value, category, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                        (params.key, params.value, params.category)
                    )
                    conn.commit()
                    return ToolResult.success_result(f"Memory saved successfully under key '{params.key}'.")
                    
                elif params.action == "get":
                    if not params.key:
                        return ToolResult.error_result("Action 'get' requires 'key'.")
                        
                    cursor.execute("SELECT value, category, updated_at FROM memories WHERE key = ?", (params.key,))
                    row = cursor.fetchone()
                    if row:
                        return ToolResult.success_result(f"[{row[1]}] {params.key}: {row[0]}\n(Last updated: {row[2]})")
                    return ToolResult.error_result(f"Memory not found for key '{params.key}'.")
                    
                elif params.action == "search":
                    if not params.query:
                        return ToolResult.error_result("Action 'search' requires 'query'.")
                        
                    search_term = f"%{params.query}%"
                    cursor.execute(
                        "SELECT key, value, category FROM memories WHERE key LIKE ? OR value LIKE ? OR category LIKE ? LIMIT 50",
                        (search_term, search_term, search_term)
                    )
                    rows = cursor.fetchall()
                    if not rows:
                        return ToolResult.success_result(f"No memories found matching '{params.query}'.")
                        
                    results = [f"- [{row[2]}] **{row[0]}**: {row[1]}" for row in rows]
                    return ToolResult.success_result(f"Found {len(rows)} matching memories:\n" + "\n".join(results))
                    
                elif params.action == "delete":
                    if not params.key:
                        return ToolResult.error_result("Action 'delete' requires 'key'.")
                        
                    cursor.execute("DELETE FROM memories WHERE key = ?", (params.key,))
                    conn.commit()
                    if cursor.rowcount > 0:
                        return ToolResult.success_result(f"Memory '{params.key}' deleted successfully.")
                    return ToolResult.error_result(f"Memory '{params.key}' not found.")
                    
        except Exception as e:
            return ToolResult.error_result(f"Database error: {e}")
