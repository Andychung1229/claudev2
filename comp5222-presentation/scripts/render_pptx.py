"""Approximate PPTX renderer for layout review (no LibreOffice). Draws solid fills, shapes, pictures,
text (Carlito = Calibri metrics), tables and simple bar/line charts, and reports text that overflows its box.
Usage: render_pptx.py <deck.pptx> <out dir> <fonts dir> [slide numbers...]"""
import colorsys
import io
import sys
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

DECK, OUT, FONTS = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
ONLY = {int(a) for a in sys.argv[4:]}
OUT.mkdir(parents=True, exist_ok=True)
PX = 100 / 914400  # 100 px per inch
N = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
     "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
     "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
     "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
A, P = "{%s}" % N["a"], "{%s}" % N["p"]
_fonts = {}


def font(pt, bold):
    k = (round(pt * 100 / 72), bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(str(FONTS / ("Carlito-Bold.ttf" if bold else "Carlito-Regular.ttf")), k[0])
    return _fonts[k]


prs = Presentation(DECK)
theme = etree.fromstring(prs.slide_masters[0].part.part_related_by(RT.THEME).blob)
SCHEME = {}
for el in theme.find(".//a:clrScheme", N):
    c = el[0]
    SCHEME[etree.QName(el).localname] = c.get("val") if c.tag == A + "srgbClr" else c.get("lastClr", "000000")
ALIAS = {"tx1": "dk1", "bg1": "lt1", "tx2": "dk2", "bg2": "lt2"}


def color(parent):
    """RGB tuple from the first colour element under parent (srgbClr / schemeClr with lum mods)."""
    if parent is None:
        return None
    if parent.find(A + "noFill") is not None:
        return None
    c = parent.find(A + "srgbClr")
    if c is None:
        c = parent.find(A + "schemeClr")
        if c is None:
            return None
        hx = SCHEME.get(ALIAS.get(c.get("val"), c.get("val")), "808080")
    else:
        hx = c.get("val")
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    for m in c:
        v = int(m.get("val", "0")) / 100000
        tag = etree.QName(m).localname
        if tag == "lumMod":
            l *= v
        elif tag == "lumOff":
            l += v
        elif tag == "tint":
            l = l + (1 - l) * (1 - v)
        elif tag == "shade":
            l *= v
    r, g, b = colorsys.hls_to_rgb(h, min(max(l, 0), 1), s)
    rgb = tuple(int(x * 255) for x in (r, g, b))
    a = c.find(A + "alpha")
    return rgb + (int(int(a.get("val")) / 100000 * 255),) if a is not None else rgb


def solid(sppr):
    return color(sppr.find(A + "solidFill")) if sppr is not None and sppr.find(A + "solidFill") is not None else None


def background(slide):
    for part in (slide, slide.slide_layout, slide.slide_layout.slide_master):
        bg = part._element.find(".//p:bg/p:bgPr", N)
        if bg is not None and bg.find(A + "solidFill") is not None:
            return color(bg.find(A + "solidFill"))
    return (255, 255, 255)


def ph_key(sp):
    ph = sp.find(".//p:nvPr/p:ph", N)
    return None if ph is None else (ph.get("type", "body"), ph.get("idx", "0"))


def layout_ph(slide, key):
    """Matching placeholder sp on the layout, then master."""
    for part in (slide.slide_layout, slide.slide_layout.slide_master):
        for sp in part._element.iter(P + "sp"):
            k = ph_key(sp)
            if k and (k[1] == key[1] and k[1] != "0" or k[0] == key[0]):
                return sp
    return None


def xfrm(el):
    x = el.find("./p:spPr/a:xfrm", N)
    if x is None:
        x = el.find("./p:xfrm", N)
    if x is None:
        x = el.find("./p:grpSpPr/a:xfrm", N)
    if x is None or x.find(A + "off") is None:
        return None
    o, e = x.find(A + "off"), x.find(A + "ext")
    return int(o.get("x")), int(o.get("y")), int(e.get("cx")), int(e.get("cy")), x


class R:
    def __init__(self, img, slide, no):
        self.img, self.d, self.slide, self.no, self.warn = img, ImageDraw.Draw(img, "RGBA"), slide, no, []

    def box(self, x, y, w, h, T):
        a, b = T(x, y)
        c, d = T(x + w, y + h)
        return a * PX, b * PX, c * PX, d * PX

    def tree(self, el, T):
        for ch in el:
            tag = etree.QName(ch).localname
            if tag == "grpSp":
                g = ch.find("p:grpSpPr/a:xfrm", N)
                o, e = g.find(A + "off"), g.find(A + "ext")
                co, ce = g.find(A + "chOff"), g.find(A + "chExt")
                ox, oy, ex, ey = (int(o.get("x")), int(o.get("y")), int(e.get("cx")), int(e.get("cy")))
                cx, cy, cw, chh = int(co.get("x")), int(co.get("y")), int(ce.get("cx")) or 1, int(ce.get("cy")) or 1

                def T2(x, y, T=T, ox=ox, oy=oy, ex=ex, ey=ey, cx=cx, cy=cy, cw=cw, chh=chh):
                    return T(ox + (x - cx) * ex / cw, oy + (y - cy) * ey / chh)
                self.tree(ch, T2)
            elif tag in ("sp", "cxnSp"):
                self.shape(ch, T)
            elif tag == "pic":
                self.pic(ch, T)
            elif tag == "graphicFrame":
                self.frame(ch, T)

    def geom(self, el):
        g = xfrm(el)
        if g is None:
            k = ph_key(el)
            src = layout_ph(self.slide, k) if k else None
            g = xfrm(src) if src is not None else None
        return g

    def shape(self, el, T):
        g = self.geom(el)
        if g is None:
            return
        x, y, w, h, xf = g
        bx = self.box(x, y, w, h, T)
        sppr = el.find("p:spPr", N)
        prst = sppr.find("a:prstGeom", N) if sppr is not None else None
        prst = prst.get("prst") if prst is not None else "rect"
        fill = solid(sppr)
        style = el.find("p:style", N)
        if fill is None and style is not None and sppr is not None and sppr.find(A + "noFill") is None:
            fr = style.find("a:fillRef", N)
            if fr is not None and fr.get("idx") != "0":
                fill = color(fr)
        ln = sppr.find("a:ln", N) if sppr is not None else None
        lc = color(ln.find(A + "solidFill")) if ln is not None and ln.find(A + "solidFill") is not None else None
        if lc is None and style is not None and (ln is None or ln.find(A + "noFill") is None):
            lr = style.find("a:lnRef", N)
            if lr is not None and lr.get("idx") != "0":
                lc = color(lr)
        lw = max(1, int(int(ln.get("w", "12700")) / 12700 * 100 / 72)) if ln is not None else 1
        if etree.QName(el).localname == "cxnSp" or prst in ("line", "straightConnector1"):
            x0, y0, x1, y1 = bx
            if xf.get("flipH") == "1":
                x0, x1 = x1, x0
            if xf.get("flipV") == "1":
                y0, y1 = y1, y0
            self.d.line([x0, y0, x1, y1], fill=lc or (90, 90, 90), width=lw)
        elif fill or lc:
            bx2 = [min(bx[0], bx[2]), min(bx[1], bx[3]), max(bx[0], bx[2]), max(bx[1], bx[3])]
            if prst == "ellipse":
                self.d.ellipse(bx2, fill=fill, outline=lc, width=lw)
            elif prst == "roundRect":
                self.d.rounded_rectangle(bx2, radius=min(12, (bx2[3] - bx2[1]) / 2), fill=fill, outline=lc, width=lw)
            elif prst == "rightArrow":
                x0, y0, x1, y1 = bx2
                m = (y0 + y1) / 2
                self.d.polygon([(x0, y0 + (y1 - y0) * .25), (x1 - (y1 - y0) * .5, y0 + (y1 - y0) * .25),
                                (x1 - (y1 - y0) * .5, y0), (x1, m), (x1 - (y1 - y0) * .5, y1),
                                (x1 - (y1 - y0) * .5, y1 - (y1 - y0) * .25), (x0, y1 - (y1 - y0) * .25)], fill=fill)
            else:
                self.d.rectangle(bx2, fill=fill, outline=lc, width=lw)
        tb = el.find("p:txBody", N)
        if tb is not None:
            src = layout_ph(self.slide, ph_key(el)) if ph_key(el) else None
            self.text(tb, bx, src, el.get("name") or el.find(".//p:cNvPr", N).get("name"))

    def defaults(self, src):
        d = {"sz": 18.0, "b": False, "c": color_of(SCHEME["dk1"]), "algn": "l"}
        if src is not None:
            for r in src.iter(A + "defRPr", A + "rPr", A + "endParaRPr"):
                if r.get("sz"):
                    d["sz"] = int(r.get("sz")) / 100
                    d["b"] = r.get("b") == "1"
                    c = color(r.find(A + "solidFill")) if r.find(A + "solidFill") is not None else None
                    d["c"] = c or d["c"]
                    break
            p = src.find(".//a:pPr", N)
            if p is not None and p.get("algn"):
                d["algn"] = p.get("algn")
        return d

    def text(self, tb, bx, src, name, cell=None):
        bp = tb.find("a:bodyPr", N)
        srcbp = src.find(".//a:bodyPr", N) if src is not None else None

        def ins(k, dflt):
            for b in (bp, srcbp):
                if b is not None and b.get(k) is not None:
                    return int(b.get(k)) * PX
            return dflt * PX
        if cell is not None:
            li, ri, ti, bi = cell
        else:
            li, ri, ti, bi = ins("lIns", 91440), ins("rIns", 91440), ins("tIns", 45720), ins("bIns", 45720)
        anchor = (bp.get("anchor") if bp is not None and bp.get("anchor") else
                  srcbp.get("anchor") if srcbp is not None and srcbp.get("anchor") else "t")
        nowrap = bp is not None and bp.get("wrap") == "none"
        D = self.defaults(src)
        W = bx[2] - bx[0] - li - ri
        lines = []  # (height, [(x_off, text, font, color)], align)
        for p in tb.findall("a:p", N):
            ppr = p.find("a:pPr", N)
            algn = ppr.get("algn") if ppr is not None and ppr.get("algn") else D["algn"]
            bullet = ppr is not None and ppr.find(A + "buChar") is not None
            indent = int(ppr.get("marL", "0")) * PX if ppr is not None else 0
            spa = ppr.find("a:spcAft/a:spcPts", N) if ppr is not None else None
            spb = ppr.find("a:spcBef/a:spcPts", N) if ppr is not None else None
            words, maxsz = [], 0
            for r in p:
                t = etree.QName(r).localname
                if t not in ("r", "br", "fld"):
                    continue
                rpr = r.find("a:rPr", N)
                sz = int(rpr.get("sz")) / 100 if rpr is not None and rpr.get("sz") else D["sz"]
                b = (rpr.get("b") == "1") if rpr is not None and rpr.get("b") is not None else D["b"]
                c = color(rpr.find(A + "solidFill")) if rpr is not None and rpr.find(A + "solidFill") is not None else D["c"]
                maxsz = max(maxsz, sz)
                if t == "br":
                    words.append(("\n", None, None, sz))
                    continue
                txt = r.findtext("a:t", "", N)
                if t == "fld":
                    txt = str(self.no)
                for i, wd in enumerate(txt.split(" ")):
                    words.append(((" " if i else "") + wd, font(sz, b), c, sz))
            if not words:
                end = p.find("a:endParaRPr", N)
                sz = int(end.get("sz")) / 100 if end is not None and end.get("sz") else D["sz"]
                lines.append((sz * 1.2 * 100 / 72, [], algn, 0))
                continue
            if bullet:
                words.insert(0, ("• ", font(maxsz, False), D["c"], maxsz))
            cur, x, cursz = [], indent, maxsz
            for wd, f, c, sz in words:
                if wd == "\n":
                    lines.append((cursz * 1.2 * 100 / 72, cur, algn, indent)); cur, x = [], indent
                    continue
                wlen = f.getlength(wd)
                if cur and x + wlen > W + 1 and not nowrap:
                    lines.append((cursz * 1.2 * 100 / 72, cur, algn, indent))
                    wd = wd.lstrip(" "); wlen = f.getlength(wd); cur, x = [], indent + (f.getlength("• ") if bullet else 0)
                cur.append((x, wd, f, c)); x += wlen
            lines.append((cursz * 1.2 * 100 / 72, cur, algn, indent))
            if spa is not None:
                lines.append((int(spa.get("val")) / 100 * 100 / 72, [], algn, 0))
            if spb is not None and len(lines) > 1:
                lines.insert(-1, (int(spb.get("val")) / 100 * 100 / 72, [], algn, 0))
        if lines and not lines[-1][1]:
            lines.pop()
        total = sum(h for h, *_ in lines)
        H = bx[3] - bx[1] - ti - bi
        y = bx[1] + ti + {"t": 0, "ctr": (H - total) / 2, "b": H - total}.get(anchor, 0)
        if total > H + 3 and any(l[1] for l in lines):
            self.warn.append(f"overflow {name}: text {total / 100:.2f}in > box {H / 100:.2f}in")
        for h, segs, algn, ind in lines:
            if segs:
                lw = segs[-1][0] + segs[-1][2].getlength(segs[-1][1]) - ind
                off = {"ctr": (W - lw) / 2 - ind / 2, "r": W - lw - ind}.get(algn, 0)
                for xo, wd, f, c in segs:
                    self.d.text((bx[0] + li + xo + off, y + h * 0.1), wd, font=f, fill=c)
                    if xo + f.getlength(wd) > W + 4 and not nowrap:
                        self.warn.append(f"wide word in {name}: {wd!r}")
            y += h

    def pic(self, el, T):
        g = self.geom(el)
        blip = el.find(".//a:blip", N)
        if g is None or blip is None:
            return
        part = self.slide.part.related_part(blip.get("{%s}embed" % N["r"]))
        try:
            im = Image.open(io.BytesIO(part.blob)).convert("RGBA")
        except Exception:
            return
        sr = el.find(".//a:srcRect", N)
        if sr is not None:
            W, H = im.size
            l, t, r, b = (int(sr.get(k, "0")) / 100000 for k in "ltrb")
            im = im.crop((int(W * l), int(H * t), int(W * (1 - r)), int(H * (1 - b))))
        bx = self.box(*g[:4], T)
        w, h = int(bx[2] - bx[0]), int(bx[3] - bx[1])
        if w > 0 and h > 0:
            im = im.resize((w, h))
            self.img.paste(im, (int(bx[0]), int(bx[1])), im)

    def frame(self, el, T):
        g = xfrm(el)
        x, y, w, h, _ = g
        tbl = el.find(".//a:tbl", N)
        if tbl is not None:
            cols = [int(c.get("w")) for c in tbl.findall("a:tblGrid/a:gridCol", N)]
            yy = y
            for tr in tbl.findall("a:tr", N):
                rh = int(tr.get("h"))
                # grow the row if the text needs more height
                xx = x
                for ci, tc in enumerate(tr.findall("a:tc", N)):
                    pr = tc.find("a:tcPr", N)
                    bx = self.box(xx, yy, cols[ci], rh, T)
                    f = solid(pr)
                    self.d.rectangle(bx, fill=f, outline=(205, 211, 218))
                    m = [int(pr.get(k, d)) * PX if pr is not None else d * PX
                         for k, d in (("marL", 91440), ("marR", 91440), ("marT", 45720), ("marB", 45720))]
                    self.text(tc.find("a:txBody", N), bx, None, "table cell", cell=m)
                    xx += cols[ci]
                yy += rh
            if yy > y + h + 20000:
                self.warn.append("table taller than frame")
            return
        ch = el.find(".//c:chart", N)
        if ch is not None:
            self.chart(self.slide.part.related_part(ch.get("{%s}id" % N["r"])), self.box(x, y, w, h, T))

    def chart(self, part, bx):
        root = etree.fromstring(part.blob)
        self.d.rectangle(bx, outline=(220, 220, 220))
        series = []
        for kind in ("barChart", "lineChart"):
            for ct in root.iter("{%s}%s" % (N["c"], kind)):
                for ser in ct.findall("c:ser", N):
                    vals = {}
                    for pt in ser.findall("c:val//c:pt", N):
                        vals[int(pt.get("idx"))] = float(pt.findtext("c:v", "0", N))
                    cats = [v.text for v in ser.findall("c:cat//c:pt/c:v", N)]
                    sp = ser.find("c:spPr", N)
                    lnf = sp.find("a:ln", N) if sp is not None else None
                    mk = ser.find("c:marker/c:spPr", N)
                    sym = ser.find("c:marker/c:symbol", N)
                    if sym is not None and sym.get("val") == "none":
                        mk = None
                    dpt = {int(d.find("c:idx", N).get("val")): solid(d.find("c:spPr", N)) for d in ser.findall("c:dPt", N)}
                    series.append(dict(kind=kind, vals=vals, cats=cats, fill=solid(sp),
                                       ln=None if lnf is None or lnf.find(A + "noFill") is not None else color(lnf.find(A + "solidFill")),
                                       mk=solid(mk) if mk is not None else None, dpt=dpt))
        if not series:
            return
        ncat = max(len(s["cats"]) for s in series)
        cats = next(s["cats"] for s in series if len(s["cats"]) == ncat)
        mx_el = root.find(".//c:valAx/c:scaling/c:max", N)
        mn_el = root.find(".//c:valAx/c:scaling/c:min", N)
        vmax = float(mx_el.get("val")) if mx_el is not None else max(max(s["vals"].values()) for s in series) * 1.15
        vmin = float(mn_el.get("val")) if mn_el is not None else 0
        x0, y0, x1, y1 = bx[0] + 50, bx[1] + 10, bx[2] - 10, bx[3] - 60
        self.d.line([x0, y1, x1, y1], fill=(120, 120, 120))
        for k in range(6):
            v = vmin + (vmax - vmin) * k / 5
            yy = y1 - (y1 - y0) * k / 5
            self.d.line([x0, yy, x1, yy], fill=(225, 225, 225))
            self.d.text((bx[0] + 5, yy - 8), f"{v:.2f}", font=font(12, False), fill=(90, 90, 90))
        cw = (x1 - x0) / ncat
        step = int(root.find(".//c:tickLblSkip", N).get("val")) if root.find(".//c:tickLblSkip", N) is not None else 1
        for i, c in enumerate(cats):
            if i % step:
                continue
            self.d.multiline_text((x0 + cw * i + 4, y1 + 6), "\n".join(__import__("textwrap").wrap(c or "", 12)), font=font(12, False), fill=(60, 60, 60))
        Y = lambda v: y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)
        for s in series:
            for i, v in s["vals"].items():
                cx = x0 + cw * (i + .5)
                if s["kind"] == "barChart":
                    self.d.rectangle([cx - cw * .32, Y(v), cx + cw * .32, y1], fill=s["dpt"].get(i) or s["fill"] or (150, 150, 150))
                    self.d.text((cx - 14, y1 - 20), f"{v:.3f}", font=font(13, False), fill=(20, 35, 58))
                elif s["mk"] is not None:
                    self.d.ellipse([cx - 4, Y(v) - 4, cx + 4, Y(v) + 4], fill=s["mk"])
            if s["kind"] == "lineChart" and s["ln"] is not None:
                pts = [(x0 + cw * (i + .5), Y(v)) for i, v in sorted(s["vals"].items())]
                if len(pts) > 1:
                    self.d.line(pts, fill=s["ln"], width=2)


def color_of(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


W, H = int(prs.slide_width * PX), int(prs.slide_height * PX)
for no, slide in enumerate(prs.slides, 1):
    if ONLY and no not in ONLY:
        continue
    img = Image.new("RGB", (W, H), background(slide))
    r = R(img, slide, no)
    ident = lambda x, y: (x, y)
    # layout and master non-placeholder shapes first (e.g. footer text)
    for part in (slide.slide_layout.slide_master, slide.slide_layout):
        for sp in part._element.find(".//p:cSld/p:spTree", N):
            if etree.QName(sp).localname in ("sp", "pic") and ph_key(sp) is None:
                r.tree([sp], ident)
    r.tree(slide._element.find(".//p:cSld/p:spTree", N), ident)
    img.save(OUT / f"s{no:02d}.png")
    for w in r.warn:
        print(f"slide {no}: {w}")
print("rendered", OUT)
