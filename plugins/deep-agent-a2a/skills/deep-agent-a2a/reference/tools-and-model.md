# Model, tools, skills, hooks, approvals (`agent/agent.py`, `agent.toml`)

## Model

`init_chat_model(MODEL, base_url=MODEL_BASE_URL, api_key=MODEL_API_KEY, use_responses_api=True, store=False,
include=["reasoning.encrypted_content"])`.

- **Responses API with `store=False`:** the provider keeps nothing; the history comes from the checkpointer, so a
  model or replica change breaks no conversation. `include` keeps reasoning usable across turns without storage.
- Some models behind a gateway (e.g. `azure-gpt-6-luna`) refuse function tools on Chat Completions
  ("Function tools with reasoning_effort are not supported ... use /v1/responses"): another reason for the
  Responses API. The endpoint must support `/v1/responses`.
- Swap provider or model through `MODEL` / `MODEL_BASE_URL`; agents hold no keys when a gateway sits in front.

## MCP tools

- **Client:** LangChain's built-in adapter, `langchain[mcp]` → `from langchain.mcp import MCPAdapter` (beta, built
  on FastMCP; silence `LangChainBetaWarning`). `async with MCPAdapter(url) as mcp: tools = await mcp.list_tools()`;
  the tools reconnect per call, which suits stateless servers.
- **Don't use `langchain-mcp-adapters`:** no longer maintained, and it pins an older `mcp` client.
- **Server:** FastMCP with `mcp.run(transport="http", stateless_http=True)`: no session, any replica serves any
  request. One call shows as three POSTs (initialize, initialized, tools/call).
- `mcp_url` in `agent.toml` (or `MCP_URL`) per agent; no `mcp_url` means no tools beyond the built-ins.
- Prefer existing MCP servers (e.g. Microsoft's: Azure, Learn, DevOps, Dataverse, GitHub); write one only when none
  fits. Version and deploy MCP servers separately from agents so several agents share them.

## Skills

`agent/agents/<name>/skills/<skill>/SKILL.md`, routed into Deep Agents' virtual filesystem:
`CompositeBackend(default=StateBackend(), routes={"/skills/": FilesystemBackend(root_dir=..., virtual_mode=True)})`
and `skills=["/skills/"]`. Read-only, in the image. Name skill folders after the skill: progress says
"Reading the <folder> skill…". Scratch files the agent writes go to `StateBackend`, i.e. into the checkpoint.

## Hooks

`@wrap_tool_call` middleware around every tool call (`log_tool_calls` logs `tool call: <name> <args>`). Put
guardrails, auditing or PII redaction here; pass them in `middleware=[...]`.

## Approvals and progress (`agent.toml`)

```toml
approve_tools = ["save_note"]                  # -> interrupt_on={"save_note": True}
[progress]                                     # while the model proposes the call
save_note = "Preparing a note…"
[running]                                      # when the approved call runs
save_note = "Saving the note on the MCP server…"
```

Built-in progress texts cover `read_file` of a skill, `write_todos` and `task` (subagents); other tools fall back
to "Using <tool>…" / "Running <tool>…".
