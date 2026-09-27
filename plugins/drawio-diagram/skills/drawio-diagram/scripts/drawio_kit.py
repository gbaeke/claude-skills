"""Helpers for generating professional, light-themed draw.io diagrams from Python.

Usage (from a generator script):

    import sys; sys.path.insert(0, "<skill dir>/scripts")
    from drawio_kit import Page, mono, pill, write_drawio

    p = Page("arch", "Architecture", 1640, 1230)          # one Page = one draw.io tab
    p.title(40, 22, 920, "Product · architecture", "one-line subtitle")
    p.legend(1000, 30, [("blue", "Clients"), ("violet", "API")])
    g = p.group(40, 110, 300, 400, "blue", "Clients", "subtitle")   # tinted container
    a = p.card(g, 15, 50, 270, 95, "blue", "Title", "body <b>html</b>")  # white card inside, coords relative
    b = p.stage(g, 15, 160, 270, 200, "blue", 1, "Step title", "body")   # numbered pipeline step
    az = p.group(380, 110, 300, 200, "violet", "cae-prod", "Container Apps env", icon="container_app_env")
    c = p.icard(az, 15, 50, 270, 100, "violet", "container_app", "api", "image:1.0", "body")  # Azure icon card
    p.edge(a, b, "label", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", points=[(x, y)], label_x=0.3)
    write_drawio("docs/architecture.drawio", [p, ...])

Coordinates: children of a group/card are relative to that parent; edge `points` are absolute page
coordinates (when the edge's parent is the page). Label HTML is escaped for XML automatically, so write
normal HTML and use &lt; / &gt; for literal angle brackets.
"""

import html

# name → (strong, fill, mid, dark): strong = badges/edges, fill = group background,
# mid = group and card borders, dark = titles
PAL = {
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
TEXT = "#475569"  # body text
INK = "#0F172A"  # page title, mono text
MUTED = "#64748B"  # subtitles, captions
EDGE = "#64748B"  # default edge colour

PILLS = {  # kind → (background, text)
    "local": ("#E2E8F0", "#334155"),
    "azure": ("#DBEAFE", "#1D4ED8"),
    "cloud": ("#DBEAFE", "#1D4ED8"),
    "opt": ("#FEF3C7", "#92400E"),
    "default": ("#EDE9FE", "#5B21B6"),
    "new": ("#DCFCE7", "#166534"),
    "warn": ("#FEE2E2", "#991B1B"),
}

# draw.io's built-in Azure icon set (verified paths under img/lib/azure2/). Pass a key or any
# "<category>/<Name>.svg" path to icon()/icard()/group(icon=…). Find others with:
#   curl -s "https://api.github.com/repos/jgraph/drawio/git/trees/dev?recursive=1" | grep -o 'img/lib/azure2/[^"]*'
AZURE_ICONS = {
    "resource_group": "general/Resource_Groups.svg",
    "browser": "general/Browser.svg",
    "globe": "general/Globe.svg",
    "container_app": "other/Worker_Container_App.svg",
    "container_app_env": "other/Container_App_Environments.svg",
    "container_registry": "containers/Container_Registries.svg",
    "container_instances": "containers/Container_Instances.svg",
    "aks": "containers/Kubernetes_Services.svg",
    "app_service": "containers/App_Services.svg",
    "foundry": "ai_machine_learning/AI_Foundry.svg",
    "foundry_project": "ai_machine_learning/Foundry_Project.svg",
    "foundry_models": "ai_machine_learning/Foundry_Models.svg",
    "foundry_agent_service": "ai_machine_learning/Foundry_Agent_Service.svg",
    "openai": "ai_machine_learning/Azure_OpenAI.svg",
    "cognitive_services": "ai_machine_learning/Cognitive_Services.svg",
    "ai_search": "app_services/Search_Services.svg",
    "managed_identity": "identity/Managed_Identities.svg",
    "entra_id": "identity/Azure_Active_Directory.svg",
    "app_registration": "identity/App_Registrations.svg",
    "app_insights": "devops/Application_Insights.svg",
    "log_analytics": "analytics/Log_Analytics_Workspaces.svg",
    "monitor": "management_governance/Monitor.svg",
    "alerts": "management_governance/Alerts.svg",
    "front_door": "networking/Front_Doors.svg",
    "postgres": "databases/Azure_Database_PostgreSQL_Server.svg",
    "sql_database": "databases/SQL_Database.svg",
    "cosmos_db": "databases/Azure_Cosmos_DB.svg",
    "redis": "databases/Cache_Redis.svg",
    "managed_redis": "databases/Azure_Managed_Redis.svg",
    "key_vault": "security/Key_Vaults.svg",
    "storage_account": "storage/Storage_Accounts.svg",
}


def pill(text: str, kind: str = "local") -> str:
    """Small rounded tag for inline use in titles: pill('Azure', 'azure')."""
    bg, fg = PILLS[kind]
    return (f'<span style="background-color:{bg};color:{fg};border-radius:9px;padding:1px 7px;'
            f'font-size:9px;font-weight:bold;">{text}</span>')


def mono(text: str) -> str:
    """Inline code / command / env var."""
    return f'<font face="Courier New" color="{INK}">{text}</font>'


def _quote(value: str) -> str:
    return '"' + html.escape(value, quote=True) + '"'


class Page:
    """One draw.io tab. Every method returns the new cell id."""

    def __init__(self, pid: str, name: str, w: int, h: int) -> None:
        self.pid, self.name, self.w, self.h = pid, name, w, h
        self.cells: list[str] = []
        self.n = 0

    def _id(self, hint: str) -> str:
        self.n += 1
        return f"{self.pid}-{hint}-{self.n}"

    # ── primitives ──
    def vertex(self, x, y, w, h, value, style, parent="1", hint="v") -> str:
        cid = self._id(hint)
        self.cells.append(
            f'<mxCell id="{cid}" value={_quote(value)} style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return cid

    def edge(self, src, tgt, value="", style="", points=None, parent="1", dashed=False, color=EDGE,
             label_x=None, width=1.5) -> str:
        """Orthogonal rounded edge with a small arrow. Pin exit/entry in `style`
        ("exitX=1;exitY=0.5;entryX=0;entryY=0.5;"), route with absolute `points`, and move the label
        along the edge with `label_x` (-1 = source end … 0 = middle … 1 = target end)."""
        cid = self._id("e")
        base = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;{FONT}"
                f"strokeColor={color};strokeWidth={width};endArrow=blockThin;endFill=1;endSize=7;fontSize=10;"
                f"fontColor=#334155;labelBackgroundColor=#FFFFFF;jumpStyle=arc;jumpSize=8;")
        if dashed:
            base += "dashed=1;dashPattern=6 4;"
        lx = f'x="{label_x}" ' if label_x is not None else ""
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        self.cells.append(
            f'<mxCell id="{cid}" value={_quote(value)} style="{base}{style}" edge="1" parent="{parent}" '
            f'source="{src}" target="{tgt}"><mxGeometry {lx}relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return cid

    def text(self, x, y, w, h, value, parent="1", size=10, color=MUTED, align="left") -> str:
        return self.vertex(x, y, w, h, value,
                           f"text;html=1;whiteSpace=wrap;align={align};verticalAlign=middle;{FONT}fontSize={size};"
                           f"fontColor={color};strokeColor=none;fillColor=none;", parent, hint="txt")

    # ── building blocks ──
    def title(self, x, y, w, title, subtitle="") -> str:
        value = f'<span style="font-size:26px;font-weight:bold;color:{INK}">{title}</span>'
        if subtitle:
            value += f'<br><span style="font-size:13px;color:{MUTED}">{subtitle}</span>'
        return self.vertex(x, y, w, 70, value, f"text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;{FONT}"
                           "strokeColor=none;fillColor=none;", hint="title")

    def legend(self, x, y, items, per_row=4, col_w=150) -> None:
        """items: [(palette name, label), …] as small swatches."""
        for i, (color, label) in enumerate(items):
            col, row = i % per_row, i // per_row
            _s, fill, mid, _d = PAL[color]
            self.vertex(x + col * col_w, y + row * 24, 14, 14, "",
                        f"rounded=1;arcSize=25;fillColor={fill};strokeColor={mid};strokeWidth=1.5;", hint="lg")
            self.vertex(x + col * col_w + 20, y + row * 24 - 3, col_w - 22, 20, label,
                        f"text;html=1;align=left;verticalAlign=middle;{FONT}fontSize=11;fontColor={TEXT};"
                        "strokeColor=none;fillColor=none;", hint="lgt")

    def group(self, x, y, w, h, color, title, subtitle="", parent="1", icon=None) -> str:
        """Tinted rounded container with a bold title (+ grey subtitle) top-left. Children use relative coords;
        leave ~45-50 px at the top for the title. `icon` (AZURE_ICONS key or path) puts a 26 px icon before it."""
        _s, fill, mid, dark = PAL[color]
        sub = (f'&nbsp;&nbsp;<span style="font-weight:normal;font-size:11px;color:{MUTED}">{subtitle}</span>'
               if subtitle else "")
        style = (f"rounded=1;absoluteArcSize=1;arcSize=20;whiteSpace=wrap;html=1;{FONT}fillColor={fill};"
                 f"strokeColor={mid};strokeWidth=1.5;verticalAlign=top;align=left;spacingLeft={46 if icon else 16};"
                 f"spacingTop=8;fontSize=15;fontColor={dark};container=1;collapsible=0;recursiveResize=0;")
        gid = self.vertex(x, y, w, h, f"<b>{title}</b>{sub}", style, parent, hint="grp")
        if icon:
            self.icon(gid, 14, 9, icon, 26)
        return gid

    def card(self, parent, x, y, w, h, color, title, body="", *, top=8, container=False, fill="#FFFFFF") -> str:
        """White card: coloured bold title, grey body (HTML: <b>, <br>, pill(), mono())."""
        _s, _f, mid, dark = PAL[color]
        value = f'<span style="font-size:12px;font-weight:bold;color:{dark}">{title}</span>'
        if body:
            value += f'<div style="margin-top:4px;line-height:1.35">{body}</div>'
        style = (f"rounded=1;absoluteArcSize=1;arcSize=12;whiteSpace=wrap;html=1;{FONT}fillColor={fill};"
                 f"strokeColor={mid};strokeWidth=1;verticalAlign=top;align=left;spacingLeft=11;spacingRight=9;"
                 f"spacingTop={top};fontSize=11;fontColor={TEXT};")
        if container:
            style += "container=1;collapsible=0;recursiveResize=0;"
        return self.vertex(x, y, w, h, value, style, parent, hint="card")

    def icon(self, parent, x, y, key, size=36) -> str:
        """draw.io built-in Azure icon: `key` is an AZURE_ICONS key or an img/lib/azure2/ relative path."""
        path = AZURE_ICONS.get(key, key)
        return self.vertex(x, y, size, size, "",
                           f"image;aspect=fixed;html=1;points=[];image=img/lib/azure2/{path};", parent, hint="ico")

    def icard(self, parent, x, y, w, h, color, icon, title, sub="", body="", *, isz=36) -> str:
        """White card with an Azure icon + bold title / grey subtitle on top and the body below it.
        Height ≈ isz + 20 (header) + 15 per body line + ~10; with no body, isz + 20 is enough."""
        _s, _f, mid, dark = PAL[color]
        cid = self.vertex(x, y, w, h, f'<div style="line-height:1.4">{body}</div>',
                          f"rounded=1;absoluteArcSize=1;arcSize=12;whiteSpace=wrap;html=1;{FONT}fillColor=#FFFFFF;"
                          f"strokeColor={mid};strokeWidth=1;verticalAlign=top;align=left;spacingLeft=11;"
                          f"spacingRight=9;spacingTop={isz + 20};fontSize=11;fontColor={TEXT};container=1;"
                          "collapsible=0;recursiveResize=0;", parent, hint="icard")
        self.icon(cid, 10, 10, icon, isz)
        value = f'<span style="font-size:12px;font-weight:bold;color:{dark}">{title}</span>'
        if sub:
            value += f'<br><span style="font-size:10px;color:{MUTED}">{sub}</span>'
        self.vertex(isz + 18, 8, w - isz - 24, isz + 4, value,
                    f"text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;{FONT}strokeColor=none;"
                    "fillColor=none;", cid, hint="it")
        return cid

    def stage(self, parent, x, y, w, h, color, num, title, body="") -> str:
        """Numbered pipeline step: badge + title on top, body below (the card is a container too)."""
        _s, _f, mid, dark = PAL[color]
        style = (f"rounded=1;absoluteArcSize=1;arcSize=12;whiteSpace=wrap;html=1;{FONT}fillColor=#FFFFFF;"
                 f"strokeColor={mid};strokeWidth=1;verticalAlign=top;align=left;spacingLeft=12;spacingRight=10;"
                 f"spacingTop=46;fontSize=11;fontColor={TEXT};container=1;collapsible=0;recursiveResize=0;")
        cid = self.vertex(x, y, w, h, f'<div style="line-height:1.4">{body}</div>', style, parent, hint="stage")
        self.badge(cid, 12, 12, num, color)
        self.vertex(46, 10, w - 56, 30, f"<b>{title}</b>",
                    f"text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;{FONT}fontSize=13;"
                    f"fontColor={dark};strokeColor=none;fillColor=none;", cid, hint="st")
        return cid

    def badge(self, parent, x, y, num, color) -> str:
        """Filled circle with a number/letter. Use plain digits: ①②③ don't render in Helvetica."""
        return self.vertex(x, y, 26, 26, f"<b>{num}</b>",
                           f"ellipse;whiteSpace=wrap;html=1;{FONT}fillColor={PAL[color][0]};strokeColor=none;"
                           "fontColor=#FFFFFF;fontSize=12;aspect=fixed;", parent, hint="badge")

    def node(self, parent, x, y, w, h, color, label, *, solid=False, shape="rounded") -> str:
        """Small flow node for mini diagrams inside a card (state machines, loops): solid = filled strong colour."""
        s, _f, mid, dark = PAL[color]
        base = "ellipse;" if shape == "ellipse" else "rounded=1;arcSize=20;"
        colors = (f"fillColor={s};strokeColor=none;fontColor=#FFFFFF;" if solid
                  else f"fillColor=#FFFFFF;strokeColor={mid};fontColor={dark};")
        return self.vertex(x, y, w, h, label, f"{base}html=1;whiteSpace=wrap;{FONT}fontSize=11;{colors}", parent,
                           hint="node")

    def checklist(self, parent, x, y, w, sections, color="orange", line=15) -> int:
        """Stacked white boxes: [(HEADING, [item, …]), …] with ✓ marks. Returns the y below the last box."""
        s, _f, mid, dark = PAL[color]
        for name, items in sections:
            body = "<br>".join(f'<font color="{s}">✓</font>&nbsp; {it}' for it in items)
            h = 26 + line * len(items)
            self.vertex(x, y, w, h,
                        f'<span style="font-size:11px;font-weight:bold;color:{dark};letter-spacing:0.5px">'
                        f'{name.upper()}</span><div style="line-height:1.35">{body}</div>',
                        f"rounded=1;absoluteArcSize=1;arcSize=10;whiteSpace=wrap;html=1;{FONT}fillColor=#FFFFFF;"
                        f"strokeColor={mid};verticalAlign=top;align=left;spacingLeft=12;spacingTop=5;fontSize=11;"
                        f"fontColor={TEXT};", parent, hint="chk")
            y += h + 8
        return y

    def xml(self) -> str:
        # adaptiveColors="none": otherwise draw.io's dark mode inverts the pastel fills (unreadable)
        return (f'<diagram id="{self.pid}" name="{self.name}"><mxGraphModel dx="1600" dy="1000" grid="1" '
                f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{self.w}" pageHeight="{self.h}" background="#FFFFFF" adaptiveColors="none" math="0" '
                'shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells)
                + "</root></mxGraphModel></diagram>")


def write_drawio(path, pages: list[Page]) -> None:
    import xml.dom.minidom

    doc = '<mxfile host="app.diagrams.net" type="device">' + "".join(p.xml() for p in pages) + "</mxfile>\n"
    xml.dom.minidom.parseString(doc)  # fail fast on invalid XML
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
