"""Sample MCP server with one tool.

What the tool does is not important: it fakes saving a note so the agent has a
tool with a side effect, and therefore one that needs human approval. Replace it
with your own tools, or point the agent at an existing MCP server instead.

The server is stateless (`stateless_http=True`): every request stands on its
own, so any replica can serve any request.
"""

import os
import uuid

from fastmcp import FastMCP

mcp = FastMCP("notes")


@mcp.tool
def save_note(title: str, text: str) -> dict:
    """Save a note and return it with its id.

    Args:
        title: Short title, starting with the subject.
        text: The facts to remember, in one to three sentences.
    """
    return {"id": f"NOTE-{uuid.uuid4().hex[:6].upper()}", "title": title, "text": text}


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8001")),
        stateless_http=True,
    )
