import asyncio
import os
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Map logical names to database file paths relative to workspace
DBS = {
    "default": os.path.join("instance", "pacientes.db"),
    "users": os.path.join("instance", "users.db"),
    "history": os.path.join("instance", "history.db"),
}

# On Windows venv, the console script is in Scripts\
SERVER_CMD = os.path.join(".venv", "Scripts", "mcp-server-sqlite.exe")


async def check_db(name: str, db_path: str):
    print(f"\n--- Testing MCP for '{name}' -> {db_path}")
    if not os.path.exists(db_path):
        print(
            f"[note] {db_path} does not exist yet "
            f"(SQLite will create on first write). Proceeding."
        )

    params = StdioServerParameters(
        command=SERVER_CMD,
        args=["--db-path", db_path],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print("tools:", sorted(tool_names))

            # Ensure the expected schema tools are present
            if "list_tables" not in tool_names:
                raise RuntimeError(
                    "list_tables tool not available from server"
                )

            # Call list_tables
            result = await session.call_tool("list_tables", arguments={})
            tables = None
            # Prefer structured content when available
            if (
                hasattr(result, "structuredContent")
                and result.structuredContent
            ):
                tables = result.structuredContent
            else:
                # Fallback: parse text blocks if returned as text
                try:
                    from mcp.types import TextContent
                    texts = [
                        c.text
                        for c in result.content
                        if isinstance(c, TextContent)
                    ]
                    if texts:
                        # Try eval-safe parse for simple Python-like lists
                        import json
                        import ast
                        for t in texts:
                            t_strip = t.strip()
                            parsed = None
                            # JSON array
                            if (
                                t_strip.startswith("[")
                                and t_strip.endswith("]")
                            ):
                                try:
                                    parsed = json.loads(t_strip)
                                except Exception:
                                    try:
                                        parsed = ast.literal_eval(t_strip)
                                    except Exception:
                                        parsed = None
                            if parsed is not None:
                                tables = parsed
                                break
                except Exception:
                    pass

            print("tables:", tables)
            return tables


async def main():
    results = {}
    for name, path in DBS.items():
        try:
            tables = await check_db(name, path)
            results[name] = tables
        except Exception as e:
            print(f"[error] {name}: {e}")
            results[name] = None

    print("\n==== Summary ====")
    for name, tables in results.items():
        print(f"{name}: {tables}")

if __name__ == "__main__":
    asyncio.run(main())
