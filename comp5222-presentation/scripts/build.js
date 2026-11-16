// Build ContactGAT talk as .pptx (v4: flat layout, native charts).
// Usage: node build.js <figs dir> <slides html dir> <out.pptx> <apply_theme.js> <data dir>
// Slides 2-4 are placeholders here: the partner's versions are merged in afterwards (merge_slides.py).
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const [FIGS, HTML, OUT, APPLY, DATA] = process.argv.slice(2);
const { applyTheme } = require(APPLY);

const THEME = {
  name: "ContactGAT",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "13233A", lt1: "FFFFFF", dk2: "3C4757", lt2: "EEF2F6",
    accent1: "2F6FB0", accent2: "D9692A", accent3: "A34D18", accent4: "8FB8E3",
    accent5: "1F3452", accent6: "5E6875", hlink: "2F6FB0", folHlink: "5E6875",
  },
};
// chart and table colours: grey = baselines, blue = graph with contact edges, orange = local-only graph
const HEX = { ink: "13233A", body: "3C4757", grey: "B9C2CC", blueBar: "A9C8E8", orangeBar: "E8925A", rule: "D5DCE4", grid: "E1E5EA", blueRow: "E3ECF6", orangeRow: "FBE7DA" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Contact-frequency graph attention for IDP radius of gyration";
pres.author = "Tian Jiaxin, Chung Ka Wai";
const C = pres.SchemeColor;
const S = pres.shapes;
const fig = (f) => path.join(FIGS, f);
const data = (f) => JSON.parse(fs.readFileSync(path.join(DATA, f), "utf8"));

// speaker notes come from the web deck's <aside> blocks
const notes = (id) => {
  const m = fs.readFileSync(path.join(HTML, `${id}.html`), "utf8").match(/<aside>([\s\S]*?)<\/aside>/);
  return m ? m[1].replace(/&amp;/g, "&").replace(/&gt;/g, ">").replace(/&lt;/g, "<").trim() : "";
};

// ---------- layouts ----------
const headPh = (eyeColor, titleColor) => [
  { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.38, w: 12.1, h: 0.32, fontSize: 13, bold: true, color: eyeColor, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.74, w: 12.1, h: 0.7, fontSize: 32, bold: true, color: titleColor, margin: 0, valign: "top" }, text: "" } },
];
const num = (color) => ({ x: 12.13, y: 7.0, w: 0.6, h: 0.3, fontSize: 11, color, align: "right" });

pres.defineSlideMaster({
  title: "Cover", background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.05, w: 11.8, h: 2.45, fontSize: 42, bold: true, color: C.background1, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: 0.6, y: 4.65, w: 10.5, h: 0.95, fontSize: 20, color: C.background2, margin: 0, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({ title: "Content", background: { color: C.background1 }, objects: headPh(C.accent1, C.text1), slideNumber: num(C.accent6) });
pres.defineSlideMaster({ title: "Content Tint", background: { color: C.background2 }, objects: headPh(C.accent1, C.text1), slideNumber: num(C.accent6) });
pres.defineSlideMaster({ title: "Statement", background: { color: C.text1 }, objects: headPh(C.accent4, C.background1), slideNumber: num(C.accent4) });

// ---------- helpers ----------
let objN = 0;
const name = (s) => `${s}-${++objN}`;
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(S.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0.75 }, rectRadius: 0.1, objectName: name("card") });
}
function txt(slide, content, o) {
  slide.addText(content, { isTextBox: true, margin: 0, valign: "top", fontSize: 17, color: C.text2, paraSpaceAfter: 4, objectName: name("text"), ...o });
}
// heading + body paragraphs inside a card (only used by the placeholder slides 2-4)
function cardText(slide, x, y, w, h, head, body, o = {}) {
  const hc = o.headColor || C.text1;
  const bc = o.bodyColor || C.text2;
  const runs = [{ text: head, options: { bold: true, fontSize: o.headSize || 18, color: hc, breakLine: true, paraSpaceAfter: 6 } }];
  const parts = Array.isArray(body) ? body : [{ text: body }];
  parts.forEach((p, i) => runs.push({ text: p.text, options: { fontSize: o.bodySize || 15, color: bc, ...p.options, breakLine: i < parts.length - 1 && !(p.options && p.options.breakLine === false) } }));
  txt(slide, runs, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: h - 0.4 });
}
function head(slide, eyebrow, title, fontSize) {
  slide.addText(eyebrow, { placeholder: "eyebrow" });
  slide.addText(title, fontSize ? { placeholder: "title", fontSize } : { placeholder: "title" });
}
function img(slide, file, x, y, w, h, alt) {
  slide.addImage({ path: fig(file), x, y, w, h, altText: alt, objectName: name("figure") });
}
function bigStat(slide, value, x, y, w, color = C.accent1, fontSize = 44) {
  txt(slide, value, { x, y, w, h: fontSize / 58, fontSize, bold: true, color, paraSpaceAfter: 0 });
}
// heading line + body text, no panel behind it
function block(slide, x, y, w, h, heading, body, o = {}) {
  const runs = [{ text: heading, options: { bold: true, fontSize: o.headSize || 20, color: o.headColor || C.text1, breakLine: true, paraSpaceAfter: 6 } }];
  (Array.isArray(body) ? body : [{ text: body }]).forEach((p) => runs.push({ text: p.text, options: { fontSize: 17, color: o.bodyColor || C.text2, ...(p.options || {}) } }));
  txt(slide, runs, { x, y, w, h });
}
function rule(slide, x, y, w, color = HEX.rule, pt = 1) {
  slide.addShape(S.LINE, { x, y, w, h: 0, line: { color, width: pt }, objectName: name("rule") });
}
function caption(slide, text, x, y, w, h = 0.5) {
  txt(slide, text, { x, y, w, h, fontSize: 14, color: C.accent6 });
}
const tblOpts = (o) => ({ fontSize: 17, border: { type: "solid", pt: 0.75, color: HEX.rule }, margin: [4, 8, 4, 8], valign: "middle", ...o });
const th = (t, align = "left") => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 }, align } });
const td = (t, align = "left") => ({ text: t, options: { color: C.text1, fill: { color: C.background1 }, align } });
const tdh = (t, fill, align = "left") => ({ text: t, options: { color: C.text1, bold: true, fill: { color: fill }, align } });

// bar = mean, dots = 3 training seeds, dashed line = composition baseline
function ablationChart(slide, ds, base, x, y, w, h, max, step) {
  const seeds = data("seed_mae.json");
  const labels = ["Length only", "Composition + length", "GAT contact edges", "GAT distance edges", "GAT local only"];
  const runs = ["full", "distance_only", "local_only"].map((v) => seeds[`${ds}/${v}`]);
  const mean = (a) => a.reduce((p, q) => p + q, 0) / a.length;
  const bars = [base[0], base[1], ...runs.map(mean)];
  const dot = (k) => ({ name: `Seed ${42 + k}`, labels, values: [null, null, ...runs.map((r) => r[k])] });
  slide.addChart([
    { type: pres.charts.BAR, data: [{ name: "Mean MAE", labels, values: bars }],
      options: { chartColors: [HEX.grey, HEX.grey, HEX.blueBar, HEX.blueBar, HEX.orangeBar], barGapWidthPct: 45,
        showValue: true, dataLabelPosition: "inBase", dataLabelFormatCode: "0.000", dataLabelFontSize: 13, dataLabelFontFace: "Calibri", dataLabelColor: HEX.ink } },
    { type: pres.charts.LINE, data: [{ name: "Composition", labels, values: labels.map(() => base[1]) }],
      options: { chartColors: [HEX.body], lineSize: 1.25, lineDash: "dash", lineDataSymbol: "none" } },
    { type: pres.charts.LINE, data: [0, 1, 2].map(dot),
      options: { chartColors: [HEX.ink, HEX.ink, HEX.ink], lineSize: 0, lineDataSymbol: "circle", lineDataSymbolSize: 9, lineDataSymbolLineColor: "FFFFFF", lineDataSymbolLineSize: 1 } },
  ], {
    x, y, w, h, objectName: name(`${ds}-ablation-chart`), showLegend: false, displayBlanksAs: "gap",
    catAxisLabelFontFace: "Calibri", valAxisLabelFontFace: "Calibri", valAxisTitleFontFace: "Calibri",
    catAxisLabelFontSize: 13, catAxisLabelColor: HEX.body, catAxisLineShow: true, catAxisLineColor: HEX.body,
    valAxisMinVal: 0, valAxisMaxVal: max, valAxisMajorUnit: step, valAxisLabelFormatCode: "0.00", valAxisLabelFontSize: 13,
    valAxisLabelColor: HEX.body, valAxisLineShow: false, valGridLine: { color: HEX.grid, size: 0.75 },
    showValAxisTitle: true, valAxisTitle: "MAE (nm)", valAxisTitleFontSize: 14, valAxisTitleColor: HEX.body,
  });
}

// ---------- 1 cover ----------
pres.addSection({ title: "Background" });
let s = pres.addSlide({ masterName: "Cover", sectionTitle: "Background" });
s.addShape(S.RECTANGLE, { x: 0.6, y: 1.2, w: 0.9, h: 0.07, fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: name("accent-rule") });
txt(s, "COMP 5222 project presentation", { x: 0.6, y: 1.45, w: 10, h: 0.4, fontSize: 16, bold: true, color: C.accent4 });
s.addText("Contact-frequency graph attention for predicting the radius of gyration of intrinsically disordered proteins", { placeholder: "title" });
s.addText("Turning simulation contact statistics into a residue graph, and predicting protein size with an 18.7k-parameter graph attention network", { placeholder: "sub" });
txt(s, "Tian Jiaxin and Chung Ka Wai", { x: 0.6, y: 6.15, w: 8, h: 0.45, fontSize: 20, bold: true, color: C.background1 });
s.addNotes(notes("cover"));

// ---------- 2 IDPs ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Background" });
head(s, "BIOLOGY BACKGROUND", "About 30% of our proteome never folds into one shape");
[[0.6, "Folded protein", "energy_folded.png", "Energy landscape with one deep well",
  [{ text: "One deep energy well → the chain sits in a " }, { text: "single structure", options: { bold: true, breakLine: false } }, { text: ". One set of coordinates describes it." }]],
 [6.78, "Intrinsically disordered region (IDR)", "energy_idr.png", "Shallow energy landscape with many small wells",
  [{ text: "Shallow, flat landscape → the chain keeps moving between " }, { text: "many shapes", options: { bold: true, breakLine: false } }, { text: ". Only an ensemble describes it." }]],
].forEach(([x, h, f, alt, body]) => {
  card(s, x, 1.65, 5.95, 3.95);
  txt(s, h, { x: x + 0.25, y: 1.85, w: 5.45, h: 0.4, fontSize: 18, bold: true, color: C.text1 });
  img(s, f, x + 0.43, 2.4, 5.1, 1.675, alt);
  const runs = body.map((p, i) => ({ text: p.text, options: { ...(p.options || {}), breakLine: false } }));
  txt(s, runs, { x: x + 0.25, y: 4.35, w: 5.45, h: 1.05, fontSize: 15 });
});
txt(s, "IDRs drive:", { x: 0.6, y: 5.95, w: 1.3, h: 0.5, fontSize: 14, color: C.accent6, valign: "middle" });
let px = 1.9;
for (const [label, w] of [["Transcription regulation", 2.6], ["Cell signalling", 1.85], ["Condensates / phase separation", 3.3], ["Molecular recognition", 2.45]]) {
  s.addShape(S.ROUNDED_RECTANGLE, { x: px, y: 5.95, w, h: 0.5, fill: { color: C.background2 }, line: { color: C.background2 }, rectRadius: 0.25, objectName: name("pill") });
  txt(s, label, { x: px, y: 5.95, w, h: 0.5, fontSize: 14, bold: true, color: C.text1, align: "center", valign: "middle", paraSpaceAfter: 0 });
  px += w + 0.18;
}
s.addNotes(notes("idp"));

// ---------- 3 Rg ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Background" });
head(s, "BIOLOGY BACKGROUND", "Rg: one number for the size of the whole ensemble");
card(s, 0.6, 1.65, 5.95, 2.35);
cardText(s, 0.6, 1.65, 5.95, 2.35, "What Rg measures", [
  { text: "The root-mean-square distance of residues from the chain’s centre of mass, averaged over the ensemble. Compact chain → small Rg; expanded chain → large Rg." },
  { text: "Measured in the lab by SAXS." },
]);
card(s, 0.6, 4.2, 5.95, 2.5);
cardText(s, 0.6, 4.2, 5.95, 2.5, "Length sets the baseline", "Polymer scaling: Rg ≈ R0 · N^ν. Fitted on our 18,860 training chains:");
bigStat(s, "ν = 0.53", 0.85, 5.55, 5.4);
card(s, 6.78, 1.65, 5.95, 5.05);
txt(s, [
  { text: "Sequence decides the rest", options: { bold: true, fontSize: 18, color: C.text1, breakLine: true, paraSpaceAfter: 6 } },
  { text: "At the same length, chains differ because pairs of residues attract or repel:", options: { breakLine: true, paraSpaceAfter: 10 } },
  { text: "Charges and how they are patterned (electrostatics)", options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
  { text: "Aromatic “stickers” such as W, Y, F", options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
  { text: "Prolines and other residues that stiffen or expand the chain", options: { bullet: true, breakLine: true, paraSpaceAfter: 18 } },
  { text: "Same length, different sequence → different Rg.", options: { bold: true, color: C.text1 } },
], { x: 7.03, y: 1.85, w: 5.45, h: 4.65 });
s.addNotes(notes("rg"));

// ---------- 4 gap ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Background" });
head(s, "PROBLEM", "Why predicting Rg from sequence is hard");
[["01", "No static structures to learn from", "AlphaFold learned from crystal and cryo-EM structures in the PDB. IDRs have none, so it outputs low-confidence ribbons or wrongly collapsed shapes."],
 ["02", "Current models read a 1D string", "Scalar predictors (ALBATROSS, IDP-Bert) and 3D generators (idpGAN, STARLING, IDPFold) treat the sequence as tokens. Pairwise physics must be learned from scratch, and generators need costly sampling to get Rg."],
 ["03", "Not much labelled data", "The Human IDRome has 28,058 simulated chains. Large sequence models are over-sized for this, and it is hard to see which residue pairs drive their predictions."],
].forEach(([n, h, b], i) => {
  const x = 0.6 + i * 4.125;
  card(s, x, 1.7, 3.88, 5.0, C.background1);
  bigStat(s, n, x + 0.25, 1.9, 2, C.accent3);
  cardText(s, x, 2.65, 3.88, 3.9, h, b);
});
s.addNotes(notes("gap"));

// ---------- 5 idea ----------
pres.addSection({ title: "Method" });
s = pres.addSlide({ masterName: "Statement", sectionTitle: "Method" });
head(s, "OUR APPROACH", "Residue pairs as an input graph");
rule(s, 0.85, 2.2, 9.25, C.accent4, 1.5);
[["1", "Simulation trajectories", "Human IDRome: 28,058 chains, about 1,000 frames each", "Offline, once"],
 ["2", "Contact prior", "20 × 20 table of how often each amino-acid pair sits within 8 Å", "Offline, once"],
 ["3", "Residue graph", "One node per residue, with local and top-k contact edges", "Per sequence"],
 ["4", "Edge-aware GAT", "Message passing and pooling give the predicted Rg", "Per sequence"],
].forEach(([n, h, b, tag], i) => {
  const x = 0.6 + i * 3.08;
  const col = i < 2 ? C.accent4 : C.accent2;
  s.addShape(S.OVAL, { x, y: 1.95, w: 0.5, h: 0.5, fill: { color: col }, line: { color: col, width: 0 }, objectName: name("step-dot") });
  txt(s, n, { x, y: 1.95, w: 0.5, h: 0.5, fontSize: 20, bold: true, color: C.text1, align: "center", valign: "middle", paraSpaceAfter: 0 });
  block(s, x, 2.75, 2.8, 1.75, h, b, { headColor: C.background1, bodyColor: C.background2 });
  txt(s, tag, { x, y: 4.6, w: 2.8, h: 0.4, fontSize: 17, bold: true, color: col });
});
txt(s, [
  { text: "Pairwise physics moves from " }, { text: "learned weights", options: { bold: true, color: C.background1 } },
  { text: " into the " }, { text: "input graph", options: { bold: true, color: C.background1 } },
  { text: ". A new sequence needs only steps 3 and 4, with no simulation and one forward pass." },
], { x: 0.6, y: 5.45, w: 11.8, h: 1.0, fontSize: 22, color: C.background2 });
s.addNotes(notes("idea"));

// ---------- 6 prior ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "A contact prior from 28 million simulation frames");
block(s, 0.6, 1.75, 6.3, 1.3, "How we count", [
  { text: "In every frame, a pair (i, j) with |i − j| ≥ 2 counts as a " }, { text: "contact", options: { bold: true } },
  { text: " if closer than 8 Å. We pool the counts by amino-acid type." },
]);
s.addShape(S.RECTANGLE, { x: 0.6, y: 3.25, w: 0.06, h: 0.95, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: name("equation-rule") });
txt(s, [
  { text: "f(a,b) = contacts / opportunities", options: { breakLine: true } },
  { text: "ε(a,b) = log( f(a,b) / mean f )" },
], { x: 0.9, y: 3.25, w: 6.0, h: 0.95, fontSize: 20, color: C.text1, valign: "middle", paraSpaceAfter: 4 });
caption(s, "28,058 chains and 28,055,120 frames give a 12 KB table, built once.", 0.6, 4.35, 6.3, 0.35);
block(s, 0.6, 4.95, 6.3, 1.75, "What it learned", [
  { text: "Enriched: ", options: { bold: true, color: C.accent3 } }, { text: "W–W (+0.48), A–A, Y–Y (+0.35) and other aromatic stickers", options: { breakLine: true } },
  { text: "Depleted: ", options: { bold: true, color: C.accent1 } }, { text: "K–P (−0.27), D–P, E–P, proline next to charged residues" },
]);
img(s, "contact_heatmap.png", 7.25, 1.75, 5.45, 4.84, "20 by 20 heatmap of amino-acid contact enrichment; aromatic pairs are enriched (orange), proline with charged residues is depleted (blue)");
s.addNotes(notes("prior"));

// ---------- 7 graph ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "Each sequence becomes a residue graph");
img(s, "graph_one_node.png", 0.87, 1.55, 11.6, 3.335, "A real 36-residue test sequence; residue F16 has blue local edges to its neighbours and orange arcs to eight non-local partners");
txt(s, [
  { text: "Real test-set IDR (36 aa). Edges chosen for residue F16: " },
  { text: "local neighbours", options: { bold: true, color: C.accent1 } }, { text: " and " },
  { text: "8 non-local partners", options: { bold: true, color: C.accent3 } }, { text: "." },
], { x: 0.6, y: 4.95, w: 12.1, h: 0.35, fontSize: 14, color: C.accent6 });
[["Nodes", C.text1, "One per residue: 20-dim one-hot plus position i / (N − 1)"],
 ["Local edges", C.accent1, "1 ≤ |i − j| ≤ 2, plus self-loops, so the chain stays connected"],
 ["Non-local edges", C.accent3, "Top k = 8 partners per residue by f(a,b) / p(band), undirected"],
].forEach(([h, col, b], i) => {
  const x = 0.6 + i * 4.125;
  rule(s, x, 5.5, 3.85, col, 2);
  block(s, x, 5.65, 3.85, 1.25, h, b, { headColor: col });
});
s.addNotes(notes("graph"));

// ---------- 8 sparse ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "A sparse graph with 10 features per edge");
img(s, "adjacency_long.png", 0.6, 1.7, 5.0, 5.0, "Adjacency matrix of a 155-residue chain: blue diagonal band of local edges, scattered orange non-local edges far from the diagonal");
bigStat(s, "10%", 6.2, 1.75, 4, C.accent1, 54);
txt(s, "of residue pairs become edges in this 155-residue chain (1,192 of 11,935). The edge count grows linearly with N, as O(N·(w + k)).", { x: 6.2, y: 2.75, w: 6.5, h: 1.05 });
rule(s, 6.2, 4.05, 6.5);
txt(s, [
  { text: "10 numbers per edge", options: { bold: true, fontSize: 20, color: C.text1, breakLine: true, paraSpaceAfter: 8 } },
  { text: "Contact frequency f(a,b) from the prior", options: { bullet: true, breakLine: true } },
  { text: "Sequence distance |i − j| / (N − 1)", options: { bullet: true, breakLine: true } },
  { text: "Distance band, one-hot: 1, 2–4, 5–8, 9–16, 17–32, >32", options: { bullet: true, breakLine: true } },
  { text: "Local-edge flag and self-loop flag", options: { bullet: true } },
], { x: 6.2, y: 4.3, w: 6.5, h: 2.4, paraSpaceAfter: 6 });
s.addNotes(notes("sparse"));

// ---------- 9 GAT ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "Edge-aware graph attention network");
[["Attention score per head", "u(i,j) = LeakyReLU(a_src·Wh(i) + a_dst·Wh(j) + a_edge·MLP(e(i,j)))"],
 ["Normalise over neighbours only", "α(i,j) = softmax of u(i,j) over the neighbours j of i"],
 ["Update with residual and LayerNorm", "h'(i) = ELU(LayerNorm(h(i) + Σ_j α(i,j)·Wh(j)))"],
 ["Readout", "ln Rg = MLP(mean h ‖ max h ‖ log N)"],
].forEach(([label, eq], i) => {
  const y = 1.75 + i * 1.25;
  s.addShape(S.RECTANGLE, { x: 0.6, y, w: 0.06, h: 1.0, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: name("equation-rule") });
  txt(s, [
    { text: label, options: { bold: true, fontSize: 16, color: C.accent1, breakLine: true, paraSpaceAfter: 4 } },
    { text: eq, options: { fontSize: 18, color: C.text1 } },
  ], { x: 0.85, y: y + 0.05, w: 7.25, h: 0.95 });
});
[["The prior steers attention", "Contact frequency enters the score as an edge feature, so the model learns how much to trust it."],
 ["Small on purpose", [{ text: "2 layers × 4 heads × 16 channels: " }, { text: "18,721 parameters", options: { bold: true } }]],
 ["Length stays visible", "log N enters the readout next to mean and max pooling."],
].forEach(([h, b], i) => {
  const y = 1.75 + i * 1.65;
  if (i) rule(s, 8.45, y - 0.2, 4.28);
  block(s, 8.45, y, 4.28, 1.4, h, b);
});
s.addNotes(notes("gat"));

// ---------- 10 training ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Method" });
head(s, "METHOD", "Training on unseen-protein splits");
s.addTable([
  [th("Split (70 / 15 / 15)"), th("Chains, N ≤ 512", "right")],
  [td("Train"), td("18,860", "right")],
  [td("Validation"), td("4,020", "right")],
  [td("Test"), td("4,103", "right")],
], tblOpts({ x: 0.6, y: 1.75, w: 5.9, colW: [3.2, 2.7], rowH: 0.45, objectName: name("split-table") }));
txt(s, [
  { text: "Regions from the " }, { text: "same UniProt protein", options: { bold: true } },
  { text: ", and identical sequences, stay in one split (15,331 groups)." },
], { x: 0.6, y: 3.8, w: 5.9, h: 0.9 });
txt(s, [
  { text: "Loss: MSE on ln Rg, AdamW, lr 10⁻³", options: { bullet: true, breakLine: true } },
  { text: "Batches grouped by length to fill the GPU", options: { bullet: true, breakLine: true } },
  { text: "Early stop on validation MAE (patience 15)", options: { bullet: true, breakLine: true } },
  { text: "3 training seeds per model (42, 43, 44)", options: { bullet: true } },
], { x: 0.6, y: 4.85, w: 5.9, h: 1.9, paraSpaceAfter: 8 });
const hist = data("val_hist.json");
const ep = hist.map((r) => String(r[0]));
s.addChart([
  { type: pres.charts.LINE, data: [{ name: "Validation MAE", labels: ep, values: hist.map((r) => r[1]) }],
    options: { chartColors: [THEME.colors.accent1], lineSize: 2.25, lineDataSymbol: "none" } },
  { type: pres.charts.LINE, data: [{ name: "Validation RMSE", labels: ep, values: hist.map((r) => r[2]) }],
    options: { chartColors: [THEME.colors.accent2], lineSize: 1.75, lineDash: "dash", lineDataSymbol: "none" } },
], {
  x: 6.85, y: 1.7, w: 5.88, h: 4.35, objectName: name("val-chart"),
  showLegend: true, legendPos: "t", legendFontFace: "Calibri", catAxisLabelFontFace: "Calibri", valAxisLabelFontFace: "Calibri", catAxisTitleFontFace: "Calibri", valAxisTitleFontFace: "Calibri", legendFontSize: 14, legendColor: HEX.body,
  catAxisLabelFrequency: 5, catAxisLabelFontSize: 13, catAxisLabelColor: HEX.body, catAxisLineColor: HEX.body,
  showCatAxisTitle: true, catAxisTitle: "Epoch", catAxisTitleFontSize: 14, catAxisTitleColor: HEX.body,
  valAxisMinVal: 0, valAxisMaxVal: 0.7, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0.0", valAxisLabelFontSize: 13,
  valAxisLabelColor: HEX.body, valAxisLineShow: false, valGridLine: { color: HEX.grid, size: 0.75 },
  showValAxisTitle: true, valAxisTitle: "Rg error (nm)", valAxisTitleFontSize: 14, valAxisTitleColor: HEX.body,
});
caption(s, "Original seed-42 run. Best validation MAE at epoch 31, stopped at 46. Validation error jumps between epochs.", 6.85, 6.15, 5.88, 0.55);
s.addNotes(notes("train"));

// ---------- 11 results: test ----------
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Results" });
head(s, "RESULTS", "Simulations: the GAT is best without contact edges");
ablationChart(s, "test", [0.1240, 0.0984], 0.45, 1.65, 5.95, 4.7, 0.15, 0.03);
caption(s, "Bars: mean of 3 training seeds (dots). Dashed line: composition.", 0.6, 6.4, 5.8, 0.5);
s.addTable([
  [th("4,103 test chains"), th("MAE (nm)", "right"), th("R²", "right")],
  [td("Length only"), td("0.124", "right"), td("0.972", "right")],
  [td("Composition + length"), td("0.098", "right"), td("0.980", "right")],
  [td("GAT, contact edges"), td("0.111 ± 0.015", "right"), td("0.981", "right")],
  [tdh("GAT, local only", HEX.orangeRow), tdh("0.066 ± 0.007", HEX.orangeRow, "right"), tdh("0.990", HEX.orangeRow, "right")],
], tblOpts({ x: 6.65, y: 1.75, w: 6.08, colW: [2.9, 1.98, 1.2], rowH: 0.46, objectName: name("test-table") }));
[["−0.036 nm", "vs composition, 95% CI [−0.038, −0.033]"],
 ["68%", "of what length alone cannot explain (composition: 31%)"],
].forEach(([v, b], i) => {
  const x = 6.65 + i * 3.14;
  bigStat(s, v, x, 4.4, 2.95, C.accent3, 40);
  txt(s, b, { x, y: 5.15, w: 2.85, h: 0.95 });
});
caption(s, "Mean ± sd over 3 seeds. Our earlier single run (0.100) did not reproduce.", 6.65, 6.4, 6.08, 0.5);
s.addNotes(notes("restest"));

// ---------- 12 results: experiment ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Results" });
head(s, "RESULTS", "On experiments, every GAT beats composition");
ablationChart(s, "exp151", [0.4159, 0.3310], 0.45, 1.65, 5.95, 4.7, 0.45, 0.1);
caption(s, "Bars: mean of 3 training seeds (dots). Dashed line: composition.", 0.6, 6.4, 5.8, 0.5);
s.addTable([
  [th("151 experimental Rg"), th("MAE", "right"), th("R²", "right"), th("r", "right")],
  [td("Length only"), td("0.416", "right"), td("0.744", "right"), td("0.865", "right")],
  [td("Composition + length"), td("0.331", "right"), td("0.822", "right"), td("0.908", "right")],
  [tdh("GAT, contact edges", HEX.blueRow), tdh("0.301", HEX.blueRow, "right"), tdh("0.838", HEX.blueRow, "right"), tdh("0.919", HEX.blueRow, "right")],
  [tdh("GAT, local only", HEX.orangeRow), tdh("0.303", HEX.orangeRow, "right"), tdh("0.841", HEX.orangeRow, "right"), tdh("0.918", HEX.orangeRow, "right")],
], tblOpts({ x: 6.65, y: 1.75, w: 6.08, colW: [3.08, 1.0, 1.0, 1.0], rowH: 0.46, objectName: name("exp-table") }));
block(s, 6.65, 4.35, 6.08, 1.1, "Both GATs beat composition", "Contact edges −0.036 nm [−0.054, −0.018]. Local only −0.029 nm [−0.048, −0.008].");
block(s, 6.65, 5.6, 6.08, 1.1, "Contact edges make no difference here", "Local minus full: +0.008 nm [−0.012, +0.028]. Error stays near 0.30 nm for every GAT.");
s.addNotes(notes("resexp"));

// ---------- 13 diagnosis ----------
pres.addSection({ title: "Wrap-up" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
head(s, "DIAGNOSIS", "Sequence distance dominates the edge score");
img(s, "edge_scales.png", 0.5, 1.7, 6.5, 4.04, "Log-scale comparison: average contact frequency across the five distance bands spans about 1,300-fold; across amino-acid pairs it spans only 2.1-fold");
caption(s, "Edge score = f(a,b) / p(d). The pair term varies 2.1-fold and the distance term 1,338-fold.", 0.6, 5.9, 6.3, 0.6);
bigStat(s, "96.6%", 7.35, 1.7, 5.3, C.accent3, 48);
txt(s, "of chosen partners sit in the farthest band (>32). Distance-only edges perform the same.", { x: 7.35, y: 2.6, w: 5.38, h: 0.95 });
rule(s, 7.35, 3.75, 5.38);
txt(s, "Contact edges blur residue order", { x: 7.35, y: 3.9, w: 5.38, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
s.addTable([
  [th("Reordered"), th("Measured", "right"), th("Contact", "right"), th("Local", "right")],
  [td("6 seqs, 107 aa"), td("0.73", "right"), td("0.06", "right"), tdh("0.47", HEX.orangeRow, "right")],
  [td("7 seqs, 334 aa"), td("1.39", "right"), td("0.08", "right"), td("0.17", "right")],
], tblOpts({ x: 7.35, y: 4.4, w: 5.38, colW: [1.88, 1.2, 1.15, 1.15], rowH: 0.45, objectName: name("perm-table") }));
caption(s, "Spread of Rg (nm) across sequences with the same composition in a different order. Predictions averaged over 3 seeds.", 7.35, 5.9, 5.38, 0.75);
s.addNotes(notes("limits"));

// ---------- 14 close ----------
s = pres.addSlide({ masterName: "Statement", sectionTitle: "Wrap-up" });
head(s, "TAKEAWAYS", "What we can say, and what comes next");
[["1", "Chain message passing works", "An 18.7k-parameter GAT on local edges beats composition on simulations (0.066 vs 0.098 nm) and experiments (0.30 vs 0.33)."],
 ["2", "Our contact edges don't help yet", "Sequence distance picks them, so they hurt on simulations, change nothing on experiments and blur order."],
 ["3", "Next: chemistry-chosen edges", "A band-resolved contact table from training chains only. Long chains still miss residue order."],
].forEach(([n, h, b], i) => {
  const x = 0.6 + i * 4.125;
  const col = i === 0 ? C.accent2 : C.accent4;
  rule(s, x, 1.95, 3.75, col, 2);
  txt(s, n, { x, y: 2.1, w: 1, h: 0.7, fontSize: 40, bold: true, color: col, paraSpaceAfter: 0 });
  block(s, x, 2.9, 3.75, 2.4, h, b, { headSize: 22, headColor: C.background1, bodyColor: C.background2 });
});
txt(s, "Thank you. Questions?", { x: 0.6, y: 5.7, w: 12.1, h: 0.75, fontSize: 36, bold: true, color: C.background1 });
s.addNotes(notes("close"));

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
