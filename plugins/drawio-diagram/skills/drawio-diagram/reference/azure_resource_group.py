"""Worked example: one Azure resource group (rg-myapp) drawn with draw.io's built-in Azure icons.

Facts come from `az resource list -g rg-myapp`, `az containerapp show`, `az cognitiveservices account
deployment list` and `az role assignment list --assignee <MI principalId> --all`. Layout: RG as outer group,
compute env left, AI models right, bottom row identity · registry · observability · search; dashed edges for
supporting services. Uses Page.icon / Page.icard / group(icon=…) from drawio_kit.

    python3 azure_resource_group.py out.drawio
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from drawio_kit import Page, mono, pill, write_drawio

def arch() -> Page:
    p = Page("rg", "rg-myapp", 1560, 760)
    p.title(40, 22, 900, "rg-myapp · Azure resources",
            "Web app with AI features · Sweden Central, AI Search in Switzerland North · keyless via one managed identity")
    p.legend(1020, 28, [("violet", "Compute"), ("green", "AI models"), ("amber", "Search"),
                        ("pink", "Identity"), ("slate", "Registry"), ("teal", "Observability")], per_row=3, col_w=160)

    # users, outside the RG
    ug = p.group(40, 215, 130, 200, "blue", "Users")
    p.icon(ug, 37, 55, "browser", 56)
    p.text(10, 120, 110, 60, "Browser<br>HTTPS", ug, size=11, align="center")

    RX, RY = 200, 110
    rg = p.group(RX, RY, 1320, 610, "azure", "rg-myapp", "12 resources",
                 icon="resource_group")

    # Container Apps environment
    cae = p.group(20, 55, 820, 265, "violet", "cae-myapp-xxxx",
                  "Container Apps env · Consumption · no VNet · logs → Log Analytics", rg, icon="container_app_env")
    web = p.icard(cae, 15, 60, 230, 185, "violet", "container_app", "myapp-web", mono("myapp-web:1.1.2"),
                f"{pill('external', 'azure')} ingress {mono(':5173')}<br>"
                "0.25 vCPU · 0.5 Gi<br>replicas <b>1–2</b><br><br>"
                f"{mono('API_URL')} → myapp-api")
    api = p.icard(cae, 285, 60, 230, 185, "violet", "container_app", "myapp-api", mono("myapp-api:1.1.4"),
                f"{pill('external', 'azure')} ingress {mono(':8000')}<br>"
                "0.5 vCPU · 1 Gi<br>replicas <b>1–1</b><br><br>"
                f"REST API · OTel {mono('myapp-api')}<br>{mono('MODEL_DEPLOYMENT')}=gpt-chat<br>"
                f"{mono('SESSIONS')}=in_memory {pill('no cache', 'warn')}")
    worker = p.icard(cae, 555, 60, 230, 185, "violet", "container_app", "myapp-worker", mono("myapp-worker:1.2.3"),
                f"{pill('internal', 'local')} ingress {mono(':8001')}<br>"
                "1 vCPU · 2 Gi<br>replicas <b>1–3</b><br><br>"
                f"background jobs + indexing<br>{mono('SEARCH_ENDPOINT')}=srch-…<br>{mono('INDEX_ON_START')}=true")

    # Foundry
    fg = p.group(880, 55, 420, 265, "green", "aif-myapp-xxxx", "Foundry (AIServices) · S0", rg,
                 icon="foundry")
    p_ = p.icard(fg, 15, 45, 390, 48, "green", "foundry_project", "proj-myapp", "Foundry project",
               "", isz=32)
    gpt = p.icard(fg, 15, 101, 390, 72, "green", "openai", "gpt-chat", "chat model deployment",
                f"<b>500K TPM</b> · used by myapp-api", isz=28)
    emb = p.icard(fg, 15, 181, 390, 72, "green", "openai", "text-embedding-3-large", "embedding model · v1",
                f"GlobalStandard · <b>100K TPM</b> · used by myapp-worker", isz=28)

    # bottom row
    idg = p.group(20, 360, 280, 230, "pink", "Identity", parent=rg, icon="managed_identity")
    mi = p.icard(idg, 15, 50, 250, 162, "pink", "managed_identity", "id-myapp-…", "user-assigned MI · all 3 apps",
               "<b>ACR</b> · AcrPull<br><b>Search</b> · Service Contributor,<br>&nbsp;&nbsp;Index Data Contributor<br>"
               "<b>Foundry</b> · Foundry User,<br>&nbsp;&nbsp;Cognitive Services OpenAI User<br>"
               f"{mono('AZURE_CLIENT_ID')} in api/worker")
    acg = p.group(320, 360, 230, 230, "slate", "Registry", parent=rg, icon="container_registry")
    acr = p.icard(acg, 15, 50, 200, 162, "slate", "container_registry", "crmyapp…", "Container Registry · Basic",
                f"{mono('myapp-web')}<br>{mono('myapp-api')}<br>{mono('myapp-worker')}<br><br>"
                "pulled by the apps via the MI")
    og = p.group(570, 360, 270, 230, "teal", "Observability", parent=rg, icon="app_insights")
    appi = p.icard(og, 15, 48, 240, 50, "teal", "app_insights", "appi-myapp-…", "App Insights · OTel + GenAI content",
                 isz=30)
    log = p.icard(og, 15, 106, 240, 50, "teal", "log_analytics", "log-myapp-…", "Log Analytics · app + env logs",
                isz=30)
    al = p.icard(og, 15, 164, 240, 50, "teal", "alerts", "Failure Anomalies", "smart detector on appi · global",
               isz=30)

    sg = p.group(880, 360, 420, 230, "amber", "srch-myapp-xxxx", "AI Search · Switzerland North", rg,
                 icon="ai_search")
    srch = p.icard(sg, 15, 50, 390, 162, "amber", "ai_search", "Search index", "SKU serverless",
                 f"hybrid keyword + vector search<br>"
                 "auth: Entra ID <b>or</b> API key (401 bearer challenge)<br>"
                 f"public network access {pill('enabled', 'opt')}<br><br>"
                 "documents embedded with text-embedding-3-large,<br>indexed by myapp-worker")

    # edges (abs coords: cae at RX+20, RY+55; cards at +60 → y 225..475, mid 350)
    p.edge(ug, web, "HTTPS", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#2563EB")
    p.edge(web, api, "HTTPS", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#7C3AED")
    p.edge(api, worker, "jobs", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#7C3AED")
    # api → gpt: up over the worker card through the CAE title band
    api_x = RX + 20 + 285 + 115
    p.edge(api, gpt, "chat completions", "exitX=0.5;exitY=0;entryX=0;entryY=0.5;", color="#059669",
           points=[(api_x, 212), (1060, 212), (1060, 302)], label_x=-0.35)
    # worker → embeddings
    p.edge(worker, emb, "embeddings", "exitX=1;exitY=0.85;entryX=0;entryY=0.5;", color="#059669")
    # worker → search: down out of CAE into corridor
    wk_x = RX + 20 + 555 + 184
    p.edge(worker, srch, "index + search", "exitX=0.8;exitY=1;entryX=0;entryY=0.35;", color="#D97706",
           points=[(wk_x, 450), (1060, 450), (1060, 577)], label_x=-0.2)
    # supporting services → CAE (dashed)
    p.edge(mi, cae, "assigned to apps", "exitX=0.5;exitY=0;entryX=0.17;entryY=1;", color="#DB2777", dashed=True)
    p.edge(acr, cae, "AcrPull", "exitX=0.5;exitY=0;entryX=0.505;entryY=1;", color="#475569", dashed=True)
    p.edge(cae, appi, "telemetry", "exitX=0.85;exitY=1;entryX=0.544;entryY=0;", color="#0D9488", dashed=True)
    return p


if __name__ == "__main__":
    write_drawio(sys.argv[1], [arch()])
