---
name: drawio-diagram
description: Create professional, light-themed draw.io (.drawio) diagrams — architecture overviews, component maps, data/processing pipelines, multi-tab diagrams of a codebase, Azure resource groups with official Azure icons — generated from Python with a consistent house style (tinted groups, white cards, numbered stages, pills, legend) and visually verified by rendering to PNG. Use whenever the user asks for a draw.io / diagrams.net / .drawio diagram, an architecture drawing, or to update one made in this style.
---

# draw.io diagrams in the house style

The look: white page, tinted rounded **groups** per component type (each with a bold coloured title and a grey
subtitle such as the port or path), white **cards** inside with a coloured title and grey body, **numbered
stages** for pipelines, small **pills** (`local`, `Azure`, `optional`, `default`), a colour **legend** top-right,
thin grey orthogonal **edges** with short labels, and a **strategy/checklist** panel where it helps.
The user prefers this light theme; never produce dark fills.

Tools in `scripts/` (next to this file):
- `drawio_kit.py` — `Page` (one per tab) with `title`, `legend`, `group`, `card`, `stage`, `badge`, `node`,
  `checklist`, `text`, `edge`; `pill()`, `mono()`, `write_drawio()`; palette `PAL` (blue, cyan, violet, green,
  amber, pink, slate, azure, teal, orange). Azure icons: `icon()`, `icard()`, `group(…, icon=…)` and the
  `AZURE_ICONS` dict of verified icon paths (compute, AI/Foundry, search, identity, observability, and data:
  `postgres`, `sql_database`, `cosmos_db`, `redis`, `managed_redis`, `key_vault`, `storage_account`).
- `render.py file.drawio out_dir` — renders every tab to PNG (headless Chromium + draw.io viewer, needs network).
- `example.py` — a small two-tab template showing every helper.

## Workflow

1. **Understand the subject first.** For a codebase, read the real code (entry points, services, stores,
   pipelines, infra, config) so every box says something concrete and true: names, ports, file paths, commands,
   the actual strategies/thresholds. No generic filler.
2. **Plan the tabs.** Typically tab 1 = architecture (components and how they talk), tab 2+ = a process in
   depth (data pipeline, request flow, deployment). Name tabs plainly ("Architecture", "Order pipeline").
3. **Plan the layout on a grid before writing code.**
   - Architecture: columns left→right in call order (clients → front end → API → workers/servers → data), a
     bottom row for shared providers (models, observability, databases), a full-width band for build/deploy.
   - Pipelines: horizontal lanes (one per phase) of numbered stages flowing left→right; connect lanes through
     the gap between them with explicit waypoints; a side panel for "strategies at a glance".
   - Leave ~40 px gaps between groups (edges run there) and ~30-40 px corridors between rows/lanes.
   - Align cards across columns so edges are straight horizontal lines (same abs y centres).
   - Colours encode component type consistently; add a legend for them.
4. **Write a generator** in the scratchpad (copy `example.py`, `sys.path.insert` the scripts dir), output to
   the requested path (default `docs/<name>.drawio` in a repo). The scratchpad doesn't last: for a diagram that
   lives in a repo, offer to save the generator next to it (e.g. `docs/diagrams/<name>.py`) so later updates
   regenerate it instead of hand-editing XML.
5. **Render and look at every PNG** (`python3 render.py out.drawio <scratchpad>` then Read the PNGs). Fix and
   re-render until clean. Check for: text overflowing cards (enlarge or shorten), large empty space in cards
   (shrink), edge labels colliding (move with `label_x`, shorten), edges looping or crossing titles (pin
   exit/entry, add `points`, target a free spot on the group), lines through cards.
6. Report what each tab shows, and mention the file path. Don't commit unless asked.

## Rules and gotchas

- `adaptiveColors="none"` is set by `Page.xml()` — keep it; otherwise draw.io in dark mode inverts the pastel
  fills while the inline text colours stay, making the diagram dark and unreadable.
- Plain digits in badges and titles — circled digits (①②③) don't render in Helvetica.
- Labels are HTML; `vertex()` XML-escapes them. Write `&lt;slug&gt;` for literal angle brackets.
- Children of a group/card use coordinates relative to it; edge `points` are absolute page coordinates.
- Pin edges with `exitX/exitY/entryX/entryY` in the style string; auto-routing alone tends to loop in narrow gaps.
- An edge may start/end on a group (container) — useful for "service → provider" arrows.
- `label_x` moves an edge label along the edge (-1 source … 1 target); use it where labels meet on a shared corridor.
- Dashed edges (`dashed=True`) for optional, async or telemetry flows; colour edges by the target type when it helps.
- Keep text short: card bodies 1-5 lines, 11 px; use `<b>` for key terms, `mono()` for commands/env vars/paths,
  `pill()` for environment/optional tags.
- A group's title and subtitle share one line. A subtitle longer than the group width minus the title wraps
  under it and lands on the first card: keep it short and move details into a card's subtitle or body.
- Size each `Page(w, h)` to its content (+ ~40 px margin) so renders and page view have no big empty areas.
- When updating an existing diagram made with this skill, look for its generator (repo, then scratchpad) first; if
  it's gone, edit the .drawio XML directly or regenerate from a new script (read the file to keep content).
- Editing the XML directly: labels are HTML stored inside an XML attribute, so they're double-encoded in the file
  (`value="&lt;span style=…&gt;Title&lt;/span&gt;"`). A search-and-replace on the visible text only matches the
  escaped form; safer is to parse the XML, edit the `value` attribute, and write it back. Check the file still
  parses (`xml.dom.minidom.parse`) and re-render.

## Azure icons and Azure resource diagrams

When the user asks for Azure icons, or the diagram shows Azure resources, use draw.io's built-in Azure set
(`image=img/lib/azure2/<category>/<Name>.svg`). It renders in draw.io, diagrams.net and `render.py`, and needs
no embedding.
- `p.icard(parent, x, y, w, h, color, "container_app", title, sub, body)` gives an icon card: icon plus title and
  subtitle on top, body below. Its height ≈ icon size + 20 + 15 per body line + 10. Use `isz=28-32` for compact
  cards. `p.group(…, icon="container_app_env")` puts an icon before a group title. `p.icon(parent, x, y, key, size)`
  places an icon on its own.
- Keys live in `AZURE_ICONS`. The names aren't obvious: Container App = `other/Worker_Container_App.svg`,
  AI Search = `app_services/Search_Services.svg`. Never guess a path. A wrong one renders as an empty box. For
  icons that aren't in the dict, list the real ones:
  `curl -s "https://api.github.com/repos/jgraph/drawio/git/trees/dev?recursive=1" | grep -o 'img/lib/azure2/[^"]*' | grep -i <term>`
- To diagram a live resource group, collect the facts with `az` first:
  - `az resource list -g <rg> -o json`: gives the inventory.
  - `az containerapp show`: gives ingress (external or internal, port), image:tag, CPU/memory, min/max replicas
    and env vars. The env vars reveal who calls whom.
  - `az cognitiveservices account deployment list`: gives models, versions, SKU and TPM.
  - `az role assignment list --assignee <MI principalId> --all`: gives the managed identity's roles.
  - For search, env and network settings, use `az search service show` and `az containerapp env show`.
  Never put secrets or connection strings on the diagram.
- Layout that works:
  - The resource group is the outer group, with users/clients outside it on the left.
  - The compute environment sits left with apps in call order. AI/models sit on the right.
  - A bottom row holds identity · registry · observability · data.
  - Dashed edges run from those supporting services into the environment.
  - Flag findings with pills: a region different from the rest, public network access, in-memory state, and so on.
- A **generic** resource diagram (for a reusable IaC repo rather than one live resource group):
  - Take the facts from the Bicep/Terraform files (resource names, SKUs, conditions, app env vars), not from `az`.
  - Write names as the IaC patterns (`rg-&lt;name&gt;`, `aif-&lt;name&gt;-&lt;token&gt;`) and say what the
    placeholders are in the resource group's subtitle.
  - Replace live values (image tags, region, capacity, tenant) with the parameter or env var that sets them,
    e.g. `myapp-api:&lt;version&gt;`, "500K TPM (`MODEL_CAPACITY`)".
  - Show conditional resources with `pill('optional', 'opt')` plus the flag that enables them
    (`ENABLE_POSTGRES=true`), and settings that vary as alternatives (`SESSIONS=in_memory | redis`).
  - Starting from a live diagram works well: copy its generator and swap the values. Search the result for
    leftover specifics (names, suffixes, regions, URLs) before handing it over.

## Reference

`reference/two_tab_platform.py` — a full, verified generator for a fictional order platform (architecture tab with
8 colour-coded groups + a mini state machine; pipeline tab with 4 lanes, 19 numbered stages and a strategies panel). Read it when
planning a large diagram to reuse its proportions: 300-460 px columns, 40 px gaps, cards 70-110 px tall,
stage cards ~176-320 px wide, lanes ~200-390 px tall.

`reference/azure_resource_group.py` is a verified Azure resource-group diagram built with Azure icons. It shows the
Container Apps env, Foundry and its deployments, AI Search, identity, ACR and observability, and uses
`icard`/`group(icon=)` at scale.
