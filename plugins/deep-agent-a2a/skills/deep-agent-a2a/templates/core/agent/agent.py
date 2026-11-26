"""The deep agent itself: model, system prompt, MCP tools, skills, a hook,
human-in-the-loop and a checkpointer.

The code is the same for every agent. What makes an agent different lives in
its config folder (agents/<name>/agent.toml + skills/), chosen with the
AGENT_CONFIG environment variable.

This file knows nothing about A2A or HTTP. `main.py` wraps it.
"""

import logging
import os
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain.agents.middleware import wrap_tool_call
from langchain.chat_models import init_chat_model
from langchain_core._api import LangChainBetaWarning

warnings.filterwarnings("ignore", category=LangChainBetaWarning)  # langchain.mcp is in beta
from langchain.mcp import MCPAdapter  # noqa: E402

log = logging.getLogger("agent")


@dataclass
class AgentConfig:
    """What makes an agent this agent; read from agents/<name>/agent.toml."""

    name: str
    display_name: str
    description: str
    system_prompt: str
    folder: Path
    examples: list[str] = field(default_factory=list)
    mcp_url: str | None = None
    approve_tools: list[str] = field(default_factory=list)
    progress: dict[str, str] = field(default_factory=dict)  # tool -> text while the model proposes it
    running: dict[str, str] = field(default_factory=dict)  # tool -> text when an approved call runs

    @classmethod
    def load(cls, folder: str | Path) -> "AgentConfig":
        folder = Path(folder)
        data = tomllib.loads((folder / "agent.toml").read_text())
        data["mcp_url"] = os.environ.get("MCP_URL", data.get("mcp_url"))
        return cls(folder=folder, **data)


# A hook: middleware that runs around every tool call. Real agents put
# guardrails, auditing or PII redaction here; this one only logs.
@wrap_tool_call
async def log_tool_calls(request, handler):
    call = request.tool_call
    log.info("tool call: %s %s", call["name"], call["args"])
    return await handler(request)


async def build_agent(config: AgentConfig, checkpointer):
    # Model: LangChain's model interface, pointed at the AI gateway. Swapping the
    # model or provider is configuration (MODEL, MODEL_BASE_URL), not code.
    model = init_chat_model(
        os.environ.get("MODEL", "openai:azure-gpt-6-luna"),
        base_url=os.environ.get("MODEL_BASE_URL", "http://localhost:4000/v1"),
        api_key=os.environ.get("MODEL_API_KEY", "not-needed"),  # the gateway holds the real key
        # Responses API in stateless mode: we send the history ourselves (from the
        # checkpointer) and the provider stores nothing.
        use_responses_api=True,
        store=False,
        include=["reasoning.encrypted_content"],
    )

    # Tools: discovered on the MCP server over the network, with LangChain's
    # built-in MCP adapter (langchain[mcp], beta). Each tool call opens its own
    # connection, which suits a stateless MCP server.
    tools = []
    if config.mcp_url:
        async with MCPAdapter(config.mcp_url) as mcp:
            tools = await mcp.list_tools()

    return create_deep_agent(
        name=config.name,
        model=model,
        system_prompt=config.system_prompt,
        tools=tools,
        # Skills: SKILL.md folders, read-only, shipped in the image. Deep Agents
        # reads them through its virtual filesystem; /skills/ is routed to disk,
        # everything else stays in the agent state (and so in the checkpoint).
        skills=["/skills/"],
        backend=CompositeBackend(
            default=StateBackend(),
            routes={"/skills/": FilesystemBackend(root_dir=config.folder / "skills", virtual_mode=True)},
        ),
        # Human-in-the-loop: the run pauses before these tools run.
        interrupt_on={tool: True for tool in config.approve_tools} or None,
        middleware=[log_tool_calls],
        # Conversation state per thread, in PostgreSQL.
        checkpointer=checkpointer,
    )
