"""Drop empty <c:pt> cache points that pptxgenjs writes for null chart values (they would read as blanks
in PowerPoint but are not valid numbers). Usage: fix_charts.py <in.pptx> <out.pptx>"""
import re
import sys
import zipfile

src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
    n = 0
    for item in zi.infolist():
        data = zi.read(item.filename)
        if re.match(r"ppt/charts/chart\d+\.xml$", item.filename):
            txt, k = re.subn(r'<c:pt idx="\d+"><c:v></c:v></c:pt>', "", data.decode("utf8"))
            n += k
            data = txt.encode("utf8")
        zo.writestr(item, data)
print("removed", n, "empty chart points")
