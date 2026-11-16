"""Replace chosen slides of <base.pptx> with the slides at the same positions in <src.pptx>,
keeping their pictures and speaker notes. Usage: merge_slides.py <base> <src> <out> <slide no>..."""
import copy
import io
import sys

from pptx import Presentation
from pptx.oxml.ns import qn

base_path, src_path, out = sys.argv[1:4]
nums = [int(a) for a in sys.argv[4:]]
dst, src = Presentation(base_path), Presentation(src_path)
layouts = {l.name: l for l in dst.slide_layouts}
P14 = "{http://schemas.microsoft.com/office/powerpoint/2010/main}sldId"

for no in nums:
    s = src.slides[no - 1]
    old = dst.slides[no - 1]
    tree = old.shapes._spTree
    for el in list(tree.iterchildren()):
        if el.tag not in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            tree.remove(el)
    lay = layouts[s.slide_layout.name]
    rel = next(r for r in old.part.rels.values() if r.reltype.endswith("/slideLayout"))
    rel._target = lay.part
    for el in s.shapes._spTree.iterchildren():
        if el.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        el = copy.deepcopy(el)
        for blip in el.iter(qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            _, new_rid = old.part.get_or_add_image_part(io.BytesIO(s.part.related_part(rid).blob))
            blip.set(qn("r:embed"), new_rid)
        tree.append(el)
    # drop image rels the old content used and nothing references now
    used = {b.get(qn("r:embed")) for b in tree.iter(qn("a:blip"))}
    for rid, r in list(old.part.rels.items()):
        if r.reltype.endswith("/image") and rid not in used:
            old.part.drop_rel(rid)
    if s.has_notes_slide:
        ntree = old.notes_slide.shapes._spTree
        for sh in list(old.notes_slide.shapes):
            ntree.remove(sh._element)
        for el in s.notes_slide.shapes._spTree.iterchildren():
            if el.tag not in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
                ntree.append(copy.deepcopy(el))
dst.save(out)
print("merged slides", nums, "from", src_path)
