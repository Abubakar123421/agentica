import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import get_settings


class EvidenceMCPClient:
    def __init__(self) -> None:
        backend_dir = Path(__file__).resolve().parents[2]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(backend_dir)
        environment["DATABASE_URL"] = get_settings().database_url
        self.parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            env=environment,
            cwd=str(backend_dir.parent),
        )

    @asynccontextmanager
    async def session(self):
        async with stdio_client(self.parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    @staticmethod
    def _decode(result) -> Any:
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            if set(structured) == {"result"}:
                return structured["result"]
            return structured
        texts = [item.text for item in result.content if getattr(item, "type", None) == "text"]
        if not texts:
            return None
        text = "\n".join(texts)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    async def call(self, session: ClientSession, name: str, arguments: dict) -> Any:
        result = await session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(f"MCP tool {name} failed: {self._decode(result)}")
        return self._decode(result)
