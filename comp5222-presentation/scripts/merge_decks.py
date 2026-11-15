"""Replace slides FROM..end of <base.pptx> with the same slides of <src.pptx>.
Usage: merge_decks.py <base.pptx> <src.pptx> <first slide no.> <out.pptx>"""
import copy
import io
import sys

from pptx import Presentation
from pptx.oxml.ns import qn

base_path, src_path, first, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
dst, src = Presentation(base_path), Presentation(src_path)
assert len(dst.slides) == len(src.slides)
layouts = {l.name: l for l in dst.slide_layouts}

sld_lst = dst.slides._sldIdLst
old_ids = []
for sld in list(sld_lst)[first - 1:]:
    old_ids.append(sld.get("id"))
    dst.part.drop_rel(sld.get(qn("r:id")))
    sld_lst.remove(sld)

new_ids = []
for s in list(src.slides)[first - 1:]:
    n = dst.slides.add_slide(layouts[s.slide_layout.name])
    for sh in list(n.shapes):
        sh._element.getparent().remove(sh._element)
    tree = n.shapes._spTree
    for el in s.shapes._spTree.iterchildren():
        if el.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        el = copy.deepcopy(el)
        for blip in el.iter(qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            blob = s.part.related_part(rid).blob
            _, new_rid = n.part.get_or_add_image_part(io.BytesIO(blob))
            blip.set(qn("r:embed"), new_rid)
        tree.append(el)
    if s.has_notes_slide:
        # the base deck's notes master has no body placeholder, so copy the notes shapes too
        ntree = n.notes_slide.shapes._spTree
        for sh in list(n.notes_slide.shapes):
            ntree.remove(sh._element)
        for el in s.notes_slide.shapes._spTree.iterchildren():
            if el.tag not in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
                ntree.append(copy.deepcopy(el))
    new_ids.append(list(sld_lst)[-1].get("id"))

# keep the PowerPoint section list pointing at the new slide ids
id_map = dict(zip(old_ids, new_ids))
for el in dst.part._element.iter("{http://schemas.microsoft.com/office/powerpoint/2010/main}sldId"):
    if el.get("id") in id_map:
        el.set("id", id_map[el.get("id")])
dst.save(out)
print("replaced", old_ids, "->", new_ids)
