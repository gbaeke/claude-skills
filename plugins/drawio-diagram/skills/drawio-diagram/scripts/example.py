"""Template generator: a two-tab diagram (architecture + pipeline). Copy to a scratchpad and adapt.

    python3 example.py out.drawio && python3 render.py out.drawio /tmp/preview
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from drawio_kit import Page, mono, pill, write_drawio  # noqa: E402


def architecture() -> Page:
    p = Page("arch", "Architecture", 1180, 700)
    p.title(40, 22, 700, "Acme · architecture", "Web client → API → worker → database · two container images")
    p.legend(760, 30, [("blue", "Clients"), ("violet", "api image"), ("green", "worker"), ("amber", "Data")],
             per_row=2)

    g = p.group(40, 110, 260, 300, "blue", "Clients")
    web = p.card(g, 15, 50, 230, 90, "blue", "Browser", "Single-page app, calls <b>/api</b>")
    cli = p.card(g, 15, 155, 230, 90, "blue", f"CLI · {mono('acme')}", "admin commands")

    api = p.group(340, 110, 380, 300, "violet", "api image", "FastAPI :8000")
    ep = p.card(api, 15, 50, 150, 195, "violet", "/api", "REST + SSE")
    core = p.card(api, 195, 50, 170, 195, "violet", "Service", container=True)
    a = p.node(core, 15, 50, 60, 36, "violet", "<b>plan</b>", solid=True)
    b = p.node(core, 95, 50, 60, 36, "violet", "<b>act</b>")
    p.edge(a, b, parent=core, color="#7C3AED", style="endSize=5;strokeWidth=1.2;")

    d = p.group(760, 110, 380, 300, "amber", "Data")
    db = p.card(d, 15, 50, 350, 90, "amber", f"PostgreSQL {pill('cloud', 'cloud')}", "state + history")

    dep = p.group(40, 450, 1100, 200, "azure", "Build & deploy", "keyless")
    for i, (t, body) in enumerate([("images", "semver per image"), ("infra", "Bicep"), ("CI", "lint + tests")]):
        p.card(dep, 15 + i * 360, 45, 350, 130, "azure", t, body)

    p.edge(web, ep, "HTTPS", "exitX=1;exitY=0.5;entryX=0;entryY=0.25;")
    p.edge(cli, ep, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.8;")
    p.edge(ep, core, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    p.edge(core, db, "SQL", "exitX=1;exitY=0.3;entryX=0;entryY=0.5;", color="#D97706")
    return p


def pipeline() -> Page:
    p = Page("flow", "Pipeline", 1180, 560)
    p.title(40, 22, 900, "Acme · data pipeline", "from source to answer")
    lane = p.group(40, 100, 760, 250, "teal", "Ingest", "src/ingest/")
    steps = [("Fetch", "crawl sources"), ("Clean", "strip boilerplate"), ("Store", "upsert rows")]
    ids = [p.stage(lane, 15 + i * 250, 50, 220, 180, "teal", i + 1, t, b) for i, (t, b) in enumerate(steps)]
    for x, y in zip(ids, ids[1:]):
        p.edge(x, y, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#0D9488")
    panel = p.group(830, 100, 310, 250, "orange", "Strategies")
    p.checklist(panel, 15, 44, 280, [("Quality", ["dedupe", "validate"]), ("Ops", ["retry with backoff"])])
    return p


if __name__ == "__main__":
    write_drawio(sys.argv[1] if len(sys.argv) > 1 else "example.drawio", [architecture(), pipeline()])
