"""Full worked example (standalone, predates drawio_kit but uses the same helpers): a fictional order platform in two tabs — architecture + order pipeline. Study it for real-scale layout: column alignment, corridors, waypoints, label_x.

    python3 two_tab_platform.py out.drawio
"""

import html
import sys

PAL = {  # strong, fill, mid (card stroke), dark (titles)
    "blue": ("#2563EB", "#EFF6FF", "#93C5FD", "#1E3A8A"),
    "cyan": ("#0891B2", "#ECFEFF", "#67E8F9", "#164E63"),
    "violet": ("#7C3AED", "#F5F3FF", "#C4B5FD", "#4C1D95"),
    "green": ("#059669", "#ECFDF5", "#6EE7B7", "#064E3B"),
    "amber": ("#D97706", "#FFFBEB", "#FCD34D", "#78350F"),
    "pink": ("#DB2777", "#FDF2F8", "#F9A8D4", "#831843"),
    "slate": ("#475569", "#F8FAFC", "#CBD5E1", "#1E293B"),
    "azure": ("#0078D4", "#F0F7FF", "#9CC9F0", "#003A6C"),
    "teal": ("#0D9488", "#F0FDFA", "#5EEAD4", "#134E4A"),
    "orange": ("#EA580C", "#FFF7ED", "#FDBA74", "#7C2D12"),
}
FONT = "fontFamily=Helvetica;"


def pill(text, kind="local"):
    bg, fg = {"local": ("#E2E8F0", "#334155"), "azure": ("#DBEAFE", "#1D4ED8"), "opt": ("#FEF3C7", "#92400E"),
              "default": ("#EDE9FE", "#5B21B6")}[kind]
    return (f'<span style="background-color:{bg};color:{fg};border-radius:9px;padding:1px 7px;'
            f'font-size:9px;font-weight:bold;">{text}</span>')


def mono(text):
    return f'<font face="Courier New" color="#0F172A">{text}</font>'


class Page:
    def __init__(self, pid, name, w, h):
        self.pid, self.name, self.w, self.h = pid, name, w, h
        self.cells = []
        self.n = 0

    def _id(self, hint):
        self.n += 1
        return f"{self.pid}-{hint}-{self.n}"

    def vertex(self, x, y, w, h, value, style, parent="1", hint="v"):
        cid = self._id(hint)
        self.cells.append(
            f'<mxCell id="{cid}" value={quote(value)} style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return cid

    def edge(self, src, tgt, value="", style="", points=None, parent="1", dashed=False, color="#64748B", label_x=None):
        cid = self._id("e")
        base = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;{FONT}"
                f"strokeColor={color};strokeWidth=1.5;endArrow=blockThin;endFill=1;endSize=7;fontSize=10;"
                f"fontColor=#334155;labelBackgroundColor=#FFFFFF;jumpStyle=arc;jumpSize=8;")
        if dashed:
            base += "dashed=1;dashPattern=6 4;"
        pts = ""
        lx = f'x="{label_x}" ' if label_x is not None else ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        self.cells.append(
            f'<mxCell id="{cid}" value={quote(value)} style="{base}{style}" edge="1" parent="{parent}" '
            f'source="{src}" target="{tgt}"><mxGeometry {lx}relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return cid

    # ── building blocks ──
    def title(self, x, y, w, title, subtitle):
        value = (f'<span style="font-size:26px;font-weight:bold;color:#0F172A">{title}</span><br>'
                 f'<span style="font-size:13px;color:#64748B">{subtitle}</span>')
        return self.vertex(x, y, w, 70, value, f"text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;{FONT}"
                           "strokeColor=none;fillColor=none;", hint="title")

    def group(self, x, y, w, h, color, title, subtitle="", parent="1"):
        s, fill, mid, dark = PAL[color]
        sub = f'&nbsp;&nbsp;<span style="font-weight:normal;font-size:11px;color:#64748B">{subtitle}</span>' if subtitle else ""
        value = f'<b>{title}</b>{sub}'
        style = (f"rounded=1;absoluteArcSize=1;arcSize=20;whiteSpace=wrap;html=1;{FONT}fillColor={fill};"
                 f"strokeColor={mid};strokeWidth=1.5;verticalAlign=top;align=left;spacingLeft=16;spacingTop=8;"
                 f"fontSize=15;fontColor={dark};container=1;collapsible=0;recursiveResize=0;")
        return self.vertex(x, y, w, h, value, style, parent, hint="grp")

    def card(self, parent, x, y, w, h, color, title, body="", *, top=8, container=False, fill="#FFFFFF"):
        s, _fill, mid, dark = PAL[color]
        value = f'<span style="font-size:12px;font-weight:bold;color:{dark}">{title}</span>'
        if body:
            value += f'<div style="margin-top:4px;line-height:1.35">{body}</div>'
        style = (f"rounded=1;absoluteArcSize=1;arcSize=12;whiteSpace=wrap;html=1;{FONT}fillColor={fill};"
                 f"strokeColor={mid};strokeWidth=1;verticalAlign=top;align=left;spacingLeft=11;spacingRight=9;"
                 f"spacingTop={top};fontSize=11;fontColor=#475569;")
        if container:
            style += "container=1;collapsible=0;recursiveResize=0;"
        return self.vertex(x, y, w, h, value, style, parent, hint="card")

    def stage(self, parent, x, y, w, h, color, num, title, body):
        """A numbered pipeline stage: badge + title, body below."""
        s, _fill, mid, dark = PAL[color]
        style = (f"rounded=1;absoluteArcSize=1;arcSize=12;whiteSpace=wrap;html=1;{FONT}fillColor=#FFFFFF;"
                 f"strokeColor={mid};strokeWidth=1;verticalAlign=top;align=left;spacingLeft=12;spacingRight=10;"
                 f"spacingTop=46;fontSize=11;fontColor=#475569;container=1;collapsible=0;recursiveResize=0;")
        cid = self.vertex(x, y, w, h, f'<div style="line-height:1.4">{body}</div>', style, parent, hint="stage")
        self.badge(cid, 12, 12, num, color)
        self.vertex(46, 10, w - 56, 30, f'<b>{title}</b>',
                    f"text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;{FONT}fontSize=13;"
                    f"fontColor={dark};strokeColor=none;fillColor=none;", cid, hint="st")
        return cid

    def badge(self, parent, x, y, num, color):
        s = PAL[color][0]
        return self.vertex(x, y, 26, 26, f"<b>{num}</b>",
                           f"ellipse;whiteSpace=wrap;html=1;{FONT}fillColor={s};strokeColor=none;fontColor=#FFFFFF;"
                           "fontSize=12;aspect=fixed;", parent, hint="badge")

    def xml(self):
        return (f'<diagram id="{self.pid}" name="{self.name}"><mxGraphModel dx="1600" dy="1000" grid="1" '
                f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{self.w}" pageHeight="{self.h}" background="#FFFFFF" adaptiveColors="none" math="0" shadow="0"><root>'
                '<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells) + "</root></mxGraphModel></diagram>")


def quote(value):
    return '"' + html.escape(value, quote=True) + '"'


def legend(p, x, y, items):
    for i, (color, label) in enumerate(items):
        col, row = i % 4, i // 4
        s, fill, mid, dark = PAL[color]
        p.vertex(x + col * 150, y + row * 24, 14, 14, "", f"rounded=1;arcSize=25;fillColor={fill};strokeColor={mid};"
                 "strokeWidth=1.5;", hint="lg")
        p.vertex(x + col * 150 + 20, y + row * 24 - 3, 128, 20, label,
                 f"text;html=1;align=left;verticalAlign=middle;{FONT}fontSize=11;fontColor=#475569;strokeColor=none;"
                 "fillColor=none;", hint="lgt")


# ═════════════════════════════════════════ Page 1: architecture ═════════════════════════════════════════
def page_architecture():
    p = Page("arch", "Architecture", 1640, 1230)
    p.title(40, 22, 920, "Order platform · architecture",
            "Storefront SPA → REST API → worker service → PostgreSQL / object storage (local or Azure) · "
            "three versioned images")
    legend(p, 1000, 30, [("blue", "Clients"), ("cyan", "web image"), ("violet", "api image"), ("green", "worker image"),
                         ("amber", "Data"), ("pink", "External services"), ("slate", "Observability"),
                         ("azure", "Build & deploy")])

    # Clients
    g = p.group(40, 110, 300, 400, "blue", "Clients")
    c_hook = p.card(g, 15, 50, 270, 95, "blue", "Partner systems · webhooks",
                    "Marketplaces push orders to <b>/webhooks</b>, signed with HMAC — same rules as the storefront")
    c_cli = p.card(g, 15, 160, 270, 105, "blue", f"CLI · {mono('shopctl')}",
                   "orders · refunds · catalog import · replay-events · migrate · seed · dev")
    c_br = p.card(g, 15, 280, 270, 105, "blue", "Browser",
                  "Storefront <b>SPA</b> with cart and checkout (no page reloads) · "
                  "<b>admin console</b> with a live order feed")

    # web image
    g = p.group(40, 530, 300, 240, "cyan", "web image", "nginx :8080")
    w_static = p.card(g, 15, 45, 270, 85, "cyan", "Static site · web/",
                      "SPA bundle · checkout · admin console · images and fonts, built at image build time")
    p.card(g, 15, 140, 270, 85, "cyan", "/config.js",
           "Written at start-up: API URL, feature flags and the tenant's branding")

    # api image
    api = p.group(380, 110, 460, 660, "violet", "api image", "REST API :8000")
    a_hook = p.card(api, 15, 50, 150, 95, "violet", "/webhooks", "signature check + idempotency key")
    a_orders = p.card(api, 15, 160, 150, 225, "violet", "/api/orders",
                      "REST + Server-Sent Events:<br><b>created · paid · picked · shipped · cancelled</b><br><br>"
                      "order_id → event stream")
    p.card(api, 15, 400, 150, 70, "violet", "/health · /docs", "version, build, dependency checks")
    a_tel = p.card(api, 15, 485, 150, 75, "violet", "Telemetry", "request · database · queue spans")
    a_ses = p.card(api, 15, 575, 150, 70, "violet", "Sessions", "store: in_memory · redis")
    a_svc = p.card(api, 195, 50, 250, 95, "violet", "OrderService — the only write path",
                   "REST, webhooks and the CLI all go through it, so the rules are the same everywhere")
    a_sm = p.card(api, 195, 160, 250, 195, "violet", "Order state machine", container=True)
    a_pub = p.card(api, 195, 370, 250, 70, "violet", "Outbox publisher",
                   "outbox table → message queue, at-least-once delivery to the worker")
    p.card(api, 195, 455, 250, 110, "violet", "Business rules",
           "Price, tax and stock checked server-side · idempotent writes · ≤ 3 payment retries · "
           "every change audited")
    p.card(api, 195, 578, 250, 67, "violet", "config.py", "typed settings · per-tenant overrides")

    # mini state graph
    node = f"html=1;whiteSpace=wrap;{FONT}fontSize=11;"
    n_new = p.vertex(12, 60, 52, 26, "NEW", "ellipse;" + node + "fillColor=#F1F5F9;strokeColor=#CBD5E1;fontColor=#475569;fontSize=9;", a_sm)
    n_order = p.vertex(88, 50, 72, 46, '<b>order</b><br><span style="font-size:9px">validate + price</span>',
                       "rounded=1;arcSize=20;" + node + "fillColor=#7C3AED;strokeColor=none;fontColor=#FFFFFF;", a_sm)
    n_pay = p.vertex(176, 50, 62, 46, '<b>payment</b><br><span style="font-size:9px">provider</span>',
                     "rounded=1;arcSize=20;" + node + "fillColor=#EDE9FE;strokeColor=#C4B5FD;fontColor=#4C1D95;", a_sm)
    n_paid = p.vertex(98, 124, 52, 26, "PAID", "ellipse;" + node + "fillColor=#F1F5F9;strokeColor=#CBD5E1;fontColor=#475569;fontSize=9;", a_sm)
    p.vertex(10, 158, 232, 30, "a failed payment loops back to the order; a confirmed one ends in PAID",
             f"text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;{FONT}fontSize=10;fontColor=#64748B;"
             "strokeColor=none;fillColor=none;", a_sm)
    mini = "endSize=5;strokeWidth=1.2;"
    p.edge(n_new, n_order, style=mini, parent=a_sm, color="#7C3AED")
    p.edge(n_order, n_pay, style=mini + "exitX=1;exitY=0.3;entryX=0;entryY=0.3;", parent=a_sm, color="#7C3AED")
    p.edge(n_pay, n_order, style=mini + "exitX=0;exitY=0.7;entryX=1;entryY=0.7;", parent=a_sm, color="#7C3AED")
    p.edge(n_order, n_paid, style=mini, parent=a_sm, color="#7C3AED")

    # worker image
    wk = p.group(880, 110, 380, 660, "green", "worker image", "queue consumer · 4 concurrent jobs")
    k_jobs = p.card(wk, 15, 50, 350, 110, "green", "Job handlers",
                    "<b>fulfil_order</b>(order_id) → picking list + shipping label<br>"
                    "<b>send_receipt</b>(order_id) → PDF receipt + e-mail")
    k_retry = p.card(wk, 15, 175, 350, 80, "green", "Retry policy",
                     "<b>none</b> · <b>backoff</b> — exponential backoff with jitter, dead-letter queue after 5 tries")
    k_store = p.card(wk, 15, 270, 350, 140, "green", "Storage adapters",
                     "<b>local</b> — files on disk<br><b>blob</b> — Azure Blob Storage<br>"
                     "signed download URLs expire after 15 minutes")
    k_idx = p.card(wk, 15, 425, 350, 80, "green", "Search indexer",
                   "keeps the product search index in sync with the catalog · batches of 100")
    k_night = p.card(wk, 15, 520, 350, 125, "green", "Nightly jobs",
                     "Reconcile payments with the provider → rebuild the search index → export sales reports. "
                     "Order handling is detailed on the <b>Order pipeline</b> tab.")

    # data
    d = p.group(1300, 110, 300, 660, "amber", "Data")
    p.card(d, 15, 50, 270, 175, "amber", "Same code, local or Azure",
           f"{mono('DB')} sqlite | postgres<br>{mono('STORAGE')} local | blob<br>"
           f"{mono('QUEUE')} memory | servicebus<br>{mono('SESSIONS')} in_memory | redis<br>"
           f"{mono('TENANT')} → schema, branding, limits")
    d_lite = p.card(d, 15, 255, 270, 80, "amber", f"SQLite {pill('local')}",
                    "Single file in .data/ (or a Docker volume) · one schema per tenant")
    d_pg = p.card(d, 15, 350, 270, 100, "amber", f"PostgreSQL {pill('Azure', 'azure')}",
                  "Flexible server · one schema per tenant · point-in-time restore · managed identity")
    d_ten = p.card(d, 15, 470, 270, 175, "amber", "Tenants · tenants/&lt;slug&gt;/",
                   "<b>tenant.json</b> branding, currency, tax rules, limits<br>"
                   "<b>catalog/*.csv</b> product import<br>"
                   "<b>templates/</b> e-mail and receipt templates<br><b>fixtures/</b> test orders")

    # bottom row
    o = p.group(40, 820, 300, 170, "slate", "Observability", "OpenTelemetry")
    p.card(o, 15, 45, 130, 110, "slate", "Grafana", f"{pill('local')}<br>:3000 UI<br>OTLP :4318<br>make otel")
    p.card(o, 155, 45, 130, 110, "slate", "App Insights", f"{pill('Azure', 'azure')}<br>requests, dependencies and exceptions")
    ex = p.group(380, 820, 880, 170, "pink", "External services", "HTTPS APIs")
    p.card(ex, 15, 45, 270, 110, "pink", f"Payment provider {pill('sandbox')}",
           "Card and wallet payments; test keys locally, live keys in Azure (PAYMENT_BASE_URL)")
    p.card(ex, 305, 45, 270, 110, "pink", f"Shipping carrier {pill('Azure', 'azure')}",
           "Labels, pick-up requests and tracking scans · rate-limited to 10 requests/s")
    p.card(ex, 595, 45, 270, 110, "pink", f"E-mail relay {pill('local')}",
           "SMTP for receipts and status mails; a local catcher in dev, a relay service in Azure")
    ca = p.group(1300, 820, 300, 170, "amber", "Session cache")
    p.card(ca, 15, 45, 270, 110, "amber", f"Redis {pill('Azure · optional', 'opt')}",
           "Sessions and rate-limit counters · Entra token auth · lets the API scale out")

    # deploy band
    dep = p.group(40, 1030, 1560, 160, "azure", "Build & deploy", "Azure Container Apps · keyless (managed identity)")
    cards = [
        ("images.json", "web · api · worker with independent semver + content hash; CI refuses a change without a "
                        "version bump"),
        ("Containers locally", "make compose — the same versioned images, with SQLite, a local queue and Grafana"),
        ("infra/main.bicep", "Container Apps env · ACR · user-assigned managed identity · PostgreSQL · Blob · "
                             "Service Bus · App Insights · optional Redis"),
        ("deploy.sh · release.sh", "Full infra + apps, or push only the new image versions and roll the apps"),
        (f"Quality gate · {mono('make test')}", "Unit and contract tests, then a smoke test that places and "
                                                "cancels an order on staging"),
    ]
    for i, (t, b) in enumerate(cards):
        p.card(dep, 15 + i * 309, 45, 294, 100, "azure", t, b)

    # edges
    p.edge(c_hook, a_hook, "webhook", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    p.edge(c_cli, a_orders, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.23;")
    p.edge(c_br, a_orders, "SSE", "exitX=1;exitY=0.5;entryX=0;entryY=0.76;")
    p.edge(w_static, c_br, "serves the SPA", "exitX=0.5;exitY=0;entryX=0.5;entryY=1;")
    p.edge(a_hook, a_svc, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    p.edge(a_orders, a_svc, "", "exitX=1;exitY=0.12;entryX=0;entryY=0.85;", points=[(560, 297), (560, 241)])
    p.edge(a_svc, a_sm, "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    p.edge(a_sm, a_pub, "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    p.edge(a_pub, k_jobs, "queue", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#059669")
    p.edge(k_jobs, k_retry, "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    p.edge(k_retry, k_store, "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    p.edge(k_night, k_idx, "", "exitX=0.5;exitY=0;entryX=0.5;entryY=1;")
    p.edge(k_idx, k_store, "", "exitX=0.5;exitY=0;entryX=0.5;entryY=1;")
    p.edge(k_store, d_lite, "", "exitX=1;exitY=0.18;entryX=0;entryY=0.5;", color="#D97706")
    p.edge(k_store, d_pg, "", "exitX=1;exitY=0.93;entryX=0;entryY=0.5;", color="#D97706")
    p.edge(d_ten, k_night, "catalog", "exitX=0;exitY=0.64;entryX=1;entryY=0.5;", color="#D97706")
    p.edge(a_tel, o, "OTLP", "exitX=0;exitY=0.5;entryX=1;entryY=0.5;", points=[(360, 632), (360, 905)],
           dashed=True, color="#475569")
    p.edge(a_ses, ca, "sessions", "exitX=0.5;exitY=1;entryX=0.85;entryY=0;",
           points=[(470, 797), (1555, 797)], dashed=True, color="#D97706", label_x=0.8)
    p.edge(api, ex, "payments", "exitX=0.5;exitY=1;entryX=0.261;entryY=0;", color="#DB2777")
    p.edge(wk, ex, "labels · tracking · e-mail", "exitX=0.5;exitY=1;entryX=0.784;entryY=0;", color="#DB2777")
    return p


# ═════════════════════════════════════════ Page 2: order pipeline ═════════════════════════════════════════
def page_pipeline():
    p = Page("orders", "Order pipeline", 1800, 1320)
    p.title(40, 22, 1300, "Order pipeline · from checkout to delivered order",
            "How an order is captured, fulfilled and tracked — and the reliability strategies that keep every order "
            "correct")

    # 1 Capture
    lane = p.group(40, 100, 1720, 300, "teal", "Capture", "checkout to a confirmed, paid order · api/orders.py, payments.py")
    cap = [
        ("Sources",
         f"<b>Storefront checkout</b><br>{mono('POST /api/orders')}<br>"
         f"{mono('shopctl orders import FILE')}<br>{mono('shopctl replay-events --since T')}<br><br>"
         "<b>Partner webhooks</b> — marketplace orders pushed as JSON<br><br>"
         "<b>Admin console</b> — manual orders and refunds"),
        ("Validate",
         "Every order, whatever its source:<br>"
         "• JSON schema check; at most <b>50 lines</b> per order<br>"
         "• <b>idempotency key</b> — a repeated request returns the first result<br>"
         "• stock <b>reserved</b> for 15 minutes<br>"
         "• address normalised and checked against the carrier<br>"
         "• rejects unknown tenants and closed shops"),
        ("Price & tax",
         "• prices come from the catalog, <b>never from the client</b><br>"
         "• tax rules per tenant and destination country<br>"
         "• one discount code per order; codes don't stack<br>"
         "• amounts in minor units (cents), rounded once at the end<br>"
         "• the total is frozen on the order, so later catalog changes don't touch it"),
        ("Payment",
         "• payment intent at the provider, with the order id as reference<br>"
         "• 3-D Secure when the card requires it<br>"
         "• transient errors retried with backoff, <b>max 3</b><br>"
         "• the provider's webhook is the source of truth, not the redirect<br>"
         "• an unpaid order is released after 30 minutes"),
        ("Persist",
         f"{mono('orders')} + {mono('order_lines')} tables<br>"
         "• state <b>paid</b>, with the price snapshot<br>"
         "• an <b>outbox row</b> in the same transaction → the event is published exactly once<br>"
         "• audit log entry with who, what and when<br>"
         f"• receipts regenerate any time: {mono('shopctl orders receipt ID')}"),
    ]
    cap_ids = [p.stage(lane, 15 + i * 346, 50, 306, 232, "teal", i + 1, t, b) for i, (t, b) in enumerate(cap)]
    for a, b in zip(cap_ids, cap_ids[1:]):
        p.edge(a, b, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#0D9488")

    # 2 Fulfil
    lane = p.group(40, 430, 1720, 390, "violet", "Fulfil", "pick, pack and ship · worker/fulfil.py, shipping.py")
    fulfil_lane = lane
    batch = p.stage(lane, 15, 50, 610, 325, "violet", 6, "Batch · every 5 minutes · max 50 orders", "")
    subs = [
        (f"single {pill('default', 'default')}", "One picking list per order; simplest, fine for small "
                                                 "warehouses"),
        ("wave", "Orders grouped per warehouse zone, picked in one walk"),
        ("express", "Skips the batch; shipped within the hour"),
    ]
    for i, (t, b) in enumerate(subs):
        p.card(batch, 15 + i * 197, 50, 186, 98, "violet", t, b, fill="#FAF8FF")
    rules = (
        '<span style="font-size:12px;font-weight:bold;color:#4C1D95">Fulfilment rules</span>'
        '<div style="margin-top:4px;line-height:1.45">'
        "• every picking list starts with the <b>order id and bin locations</b>, sorted by walking route<br>"
        "• orders from different tenants are <b>never batched</b> together — packaging and branding differ<br>"
        "• small orders for the same address are <b>combined</b> into one parcel, up to the carrier's weight limit<br>"
        "• a missing item stops only its own order; the rest of the batch continues<br>"
        "• handlers are <b>idempotent</b>: a redelivered message never ships twice<br>"
        "• <b>parcel.fits()</b>: no parcel exceeds the carrier's size and weight limits<br>"
        "• shipment id = order id + parcel number; a re-run replaces the old labels</div>"
    )
    p.vertex(15, 160, 580, 152, rules,
             f"rounded=1;absoluteArcSize=1;arcSize=10;whiteSpace=wrap;html=1;{FONT}fillColor=#F5F3FF;strokeColor=none;"
             "verticalAlign=top;align=left;spacingLeft=12;spacingRight=10;spacingTop=8;fontSize=11;fontColor=#475569;",
             batch)
    ful = [
        (7, f"Notify {pill('optional', 'opt')}",
         "Status messages to the customer:<br>"
         "• e-mail on <b>paid, shipped and delivered</b>, in the tenant's language<br>"
         "• optional SMS on delivery day<br>"
         "• rendered from the tenant's templates, so every shop keeps its own branding<br>"
         "• queued, never sent inside the order transaction<br>"
         f"• {mono('tenant.notify')}, {mono('sms_enabled')}"),
        (8, "Ship",
         "Carrier adapters: <b>postnl</b> · <b>dhl</b> · <b>ups</b><br>"
         "• the carrier is chosen per <b>destination</b>:<br>"
         "&nbsp;&nbsp;domestic → the cheapest carrier<br>"
         "&nbsp;&nbsp;EU → the fastest tracked service<br>"
         "&nbsp;&nbsp;outside the EU → with customs data<br>"
         "• labels stored as PDF in object storage<br>"
         "• a new carrier = a new adapter, same interface<br>"
         f"• test with {mono('shopctl ship --dry-run')}"),
        (9, "Close",
         "• state <b>shipped</b>, tracking number on the order<br>"
         "• stock reservation turned into a sale<br><br>"
         f"<b>SQLite</b> {pill('local')}<br>everything in one file, no server<br><br>"
         f"<b>PostgreSQL</b> {pill('Azure', 'azure')}<br>row-level locks per order → safe with "
         "<b>parallel</b> workers<br><br>"
         "• the nightly job reconciles open orders with the provider"),
    ]
    ful_ids = [batch] + [p.stage(lane, 665 + i * 360, 50, 320, 325, "violet", n, t, b) for i, (n, t, b) in enumerate(ful)]
    for a, b in zip(ful_ids, ful_ids[1:]):
        p.edge(a, b, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#7C3AED")
    p.edge(cap_ids[-1], batch, "queue: order.paid · shopctl replay-events · nightly reconcile",
           "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", points=[(1592, 415), (360, 415)], color="#0D9488")

    # 3 Track
    lane = p.group(40, 850, 1240, 205, "blue", "Track", "the customer's and support's view · api/tracking.py")
    tr = [
        ("Status request", "Storefront, e-mail link, support console or CLI → GET /api/orders/{id}"),
        ("Access check", "Signed link or login · support sees every tenant, customers only their own orders"),
        ("Order lookup", f"{mono('orders')} + events<br>from the database, newest first"),
        ("Carrier sync", "<b>cached</b>: last known scans<br><b>live</b>: poll the carrier when the cache is older "
                         "than 10 minutes"),
        ("Merge", "Order events + carrier scans → one timeline · <b>dedupe</b> per scan id"),
        ("Timeline", "Streamed to the page · says what is delayed and why · link to the carrier"),
    ]
    tr_ids = [p.stage(lane, 15 + i * 206, 50, 176, 135, "blue", i + 1, t, b) for i, (t, b) in enumerate(tr)]
    for a, b in zip(tr_ids, tr_ids[1:]):
        p.edge(a, b, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#2563EB")
    p.edge(ful_ids[-1], tr_ids[4], "shipment events", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;",
           points=[(1585, 835), (967, 835)], color="#D97706", label_x=0.4)

    # 4 Measure
    lane = p.group(40, 1085, 1240, 205, "amber", "Measure & improve", "check before and after every change to order handling")
    ms = [
        ("Test orders", f"{mono('shopctl seed')} — fixture orders for every tax rule, carrier and payment method; "
                        "kept per tenant in tenants/&lt;slug&gt;/fixtures/"),
        ("Load test", f"{mono('make load')} — 200 checkouts/minute for 10 minutes → "
                      "<b>p50 · p95 · error rate</b> per endpoint"),
        ("End-to-end run", f"{mono('make e2e')} on staging: place, pay, ship and cancel orders · checks "
                           "<b>states · totals · e-mails</b> + latency"),
        ("Report & decide", f"{mono('make report')} — HTML comparison with the previous release · a regression "
                            "blocks the release"),
    ]
    ms_ids = [p.stage(lane, 15 + i * 310, 50, 280, 135, "amber", i + 1, t, b) for i, (t, b) in enumerate(ms)]
    for a, b in zip(ms_ids, ms_ids[1:]):
        p.edge(a, b, "", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", color="#D97706")
    p.edge(ms_ids[-1], fulfil_lane, "tune",
           "exitX=1;exitY=0.5;entryX=0.7297;entryY=1;", points=[(1295, 1202)], dashed=True, color="#D97706", label_x=0.3)

    # Strategies panel
    s = p.group(1310, 850, 450, 440, "orange", "Reliability strategies at a glance")
    sections = [
        ("Input", ["Validate every source with the same rules",
                   "Idempotency keys on every write",
                   "Prices and totals computed server-side"]),
        ("Payments", ["Provider webhook is the source of truth",
                      "Retry transient errors with backoff, max 3",
                      "Release unpaid orders after 30 minutes",
                      "Amounts in minor units, rounded once"]),
        ("Fulfilment", ["Outbox table → publish each event exactly once",
                        "Idempotent handlers, dead-letter after 5 tries",
                        "Never batch orders from different tenants",
                        "Row-level locks per order in PostgreSQL",
                        "Nightly reconcile with the payment provider"]),
        ("Tracking", ["Cache carrier scans, poll only when stale",
                      "One merged timeline, deduped per scan"]),
        ("Process", ["Ship a change only when the e2e run shows no regression"]),
    ]
    y = 44
    for name, items in sections:
        body = "<br>".join(f'<font color="#EA580C">✓</font>&nbsp; {it}' for it in items)
        h = 26 + 15 * len(items)
        p.vertex(15, y, 420, h,
                 f'<span style="font-size:11px;font-weight:bold;color:#7C2D12;letter-spacing:0.5px">{name.upper()}'
                 f'</span><div style="line-height:1.35">{body}</div>',
                 f"rounded=1;absoluteArcSize=1;arcSize=10;whiteSpace=wrap;html=1;{FONT}fillColor=#FFFFFF;"
                 "strokeColor=#FED7AA;verticalAlign=top;align=left;spacingLeft=12;spacingTop=5;fontSize=11;"
                 "fontColor=#475569;", s)
        y += h + 8
    return p


def main(out):
    pages = [page_architecture(), page_pipeline()]
    xml = '<mxfile host="app.diagrams.net" type="device">' + "".join(pg.xml() for pg in pages) + "</mxfile>\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)


if __name__ == "__main__":
    main(sys.argv[1])
