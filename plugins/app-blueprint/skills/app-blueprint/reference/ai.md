# An LLM assistant or agent in the app

This isn't a module, because each app's AI part differs. These are the patterns that worked, from a real build
(widget-shop, October 2026: deepagents 0.7.21, langchain-openai, langgraph-checkpoint-postgres, openai 3.x). Versions
move fast here: check the current release and read the installed source before relying on a detail below.

## Models: Azure Foundry

- Foundry's OpenAI v1 endpoint, no `api-version`:
  `ChatOpenAI(base_url="https://<resource>.openai.azure.com/openai/v1/", api_key=..., model=<deployment name>)`.
  The model is the **deployment** name, not the model name.
- Use the **Responses API**: `ChatOpenAI(..., use_responses_api=True, store=False,
  include=["reasoning.encrypted_content"])`. Reasoning models (gpt-6.x) reject function tools on `/chat/completions`
  ("Function tools with reasoning_effort are not supported ... use /v1/responses"). With `store=False`, the encrypted
  reasoning travels with the conversation instead of living at OpenAI.
- House dev setup: the author's other apps go through a local agentgateway at `http://localhost:4000/v1` (API key
  `not-needed`, model aliases such as `azure-gpt-6.1-sol`). If it's running, point the base URL there locally, and use
  Foundry directly on Azure.
- Settings: base URL, deployment, and the key as `SecretStr` in `config.py` (all in `.env.example`). Add an
  `assistant_configured` property: without settings the rest of the app works, and the assistant endpoints answer 503
  in the error envelope ("not configured").
- Failures keep the envelope: map `openai.APIError` (timeouts, 401, 429, 5xx) to
  `ApiError("assistant_error", ..., 502)`. Set a timeout per model call (e.g. 60 s).

## Agents: LangChain Deep Agents

- `create_deep_agent(model=..., tools=[...], system_prompt=..., checkpointer=..., middleware=[...])` **always** adds
  filesystem tools (`ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`) and `task` (a
  general-purpose subagent). For a read-only assistant that's the wrong default.
- Cleanest restriction: a small `AgentMiddleware` allowlist. `wrap_model_call` filters `request.tools` down to the
  allowed names (`request.override(tools=...)`), and `wrap_tool_call` refuses any other name. It works for every
  model, fakes included. The alternatives don't fit: `FilesystemMiddleware(tools=[...])` requires `read_file`, and a
  `HarnessProfile` with `excluded_tools` is registered globally per provider/model and isn't found for test models.
  Test the allowlist.
- Tools are plain functions over the app's own data: read-only, a fresh `Session` per call from the app's
  `session_factory`, results as small dicts (summaries for lists, details for one item). The system prompt keeps the
  agent to that data and tells it not to invent facts.
- Keep the agent in one module (`assistant.py`: model, tools, middleware, `build_agent`, `ask`, `history`) and the
  routes thin (`api/chat.py`).

## Conversation memory: a Postgres checkpointer

- `langgraph-checkpoint-postgres` (`PostgresSaver`) in the app's own PostgreSQL, keyed by `thread_id` in the run
  config. It creates and migrates its own `checkpoint*` tables in `setup()` at startup. Add `"checkpoint"` to
  `EXTERNAL_TABLE_PREFIXES` in `migrations/env.py` (see `database.md`).
- It uses a psycopg pool, separate from SQLAlchemy's engine. Type it `ConnectionPool[Connection[DictRow]]` with
  `row_factory=dict_row` and `autocommit=True`. `check=ConnectionPool.check_connection` needs a
  `# pyright: ignore[reportArgumentType]` (typed for tuple rows). On Azure, pass `kwargs=lambda: {..., "password":
  password()}` with `password = entra_password()` from `db.py`.
- Read a thread's messages with `agent.get_state(config)`, not raw checkpoint `channel_values`: messages live in a
  delta channel. Show only human and final AI messages. Delete a thread with `checkpointer.delete_thread(thread_id)`.
- The browser keeps the thread id in `sessionStorage`: a reload continues, a new tab starts fresh. "Clear history"
  deletes the thread on the server and starts a new id. Old threads pile up, so add a cleanup (by age) before real
  use.
- Open points to decide per app: two messages at once on one thread (lock per thread, or disable sending while
  waiting), streaming (SSE) versus whole answers with a typing indicator, and a rate limit on public chat endpoints.
  Every message costs money.

## Tests: never a real model

- A scripted fake: `ScriptedChatModel(GenericFakeChatModel)` with a list of responses (`AIMessage`s, including tool
  calls). `bind_tools` records the offered tool names and returns `self`; a `fail_with` field raises a given exception.
  The app takes the model (or a factory) as a `create_app` parameter, so tests pass the fake.
- openai 3.x uses `httpx2`: tests that construct openai exceptions need `httpx2.Request` (pyright catches the
  mismatch).
- Test through the HTTP API: a question triggers the right tool and returns the answer; history survives a new client;
  clear deletes; a model failure is a 502 in the envelope; the allowlist hides the filesystem tools.

## Secrets on Azure

The model key is a `@secure()` param in `app.bicep`. It becomes a Container Apps secret and a `secretRef` env var,
added to the template's `secrets` / `appEnv` concat lists. `azure-deploy.sh` passes it in a parameters file written
with `umask 077` (`-p @file`, deleted afterwards), never on the command line, where it would show in the process
list and shell history. The value comes from the environment or the deployment state file (`.azure/<rg>.env`), like
the WorkOS settings. Better still is no key: Entra auth to the model, with the managed identity holding the "Cognitive
Services OpenAI User" role on the Foundry resource. Check how the current langchain-openai / openai SDK take a token
provider for the v1 endpoint before choosing it (not verified in the build above).
