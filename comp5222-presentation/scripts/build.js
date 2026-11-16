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
// Model colours: blue = contact, dark grey = distance-only, orange = chain-only; baselines = light grey.
const HEX = { ink: "13233A", body: "3C4757", grey: "B9C2CC", blueBar: "A9C8E8", distanceBar: "8B939F", orangeBar: "E8925A", rule: "D5DCE4", grid: "E1E5EA", blueRow: "E3ECF6", orangeRow: "FBE7DA" };

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
  const labels = ["Graph size only", "Node-type histogram", "Graph: contact edges", "Graph: distance edges", "Graph: chain only"];
  const runs = ["full", "distance_only", "local_only"].map((v) => seeds[`${ds}/${v}`]);
  const mean = (a) => a.reduce((p, q) => p + q, 0) / a.length;
  const bars = [base[0], base[1], ...runs.map(mean)];
  const dot = (k) => ({ name: `Seed ${42 + k}`, labels, values: [null, null, ...runs.map((r) => r[k])] });
  slide.addChart([
    { type: pres.charts.BAR, data: [{ name: "Mean MAE", labels, values: bars }],
      options: { chartColors: [HEX.grey, HEX.grey, HEX.blueBar, HEX.distanceBar, HEX.orangeBar], barGapWidthPct: 45,
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

// ---------- speaker notes for slides 8-14 (about 6 minutes in total), written for a graph audience ----------
const NOTE = {
  sparse: `[~1:00]
Thanks. We have seen how the sequence becomes a graph. Now, let's see how we use that graph to predict protein size, and whether those extra edges actually help.

Each protein is a chain. We turn it into a graph, with one node for each amino acid. Each node has a type and a position.

Blue edges connect nearby nodes along the chain. Orange edges connect selected pairs farther apart. Each node selects up to eight long-range partners, and we make the edges undirected.

From this graph, we predict Rg: one number describing how spread out the protein is in space. We use the sequence, without a 3D structure at prediction time.

The question is: does this graph help us make better predictions?`,
  gat: `[~0:45]
We use a graph attention network with two layers.

Each node receives messages from its neighbours. Attention gives different weights to these messages. The orange part of the formula shows how edge information affects those weights.

We then combine information from all nodes using mean and max pooling, add the log graph size, and predict Rg.

The model has fewer than nineteen thousand parameters. Now, let's test whether it helps, and which edges we need.`,
  train: `[~0:50]
Our idea was that contact information could help us build a better graph. To test this, we compare three graphs using the same network: contact edges, distance-only edges, and chain-only edges.

The distance-only control uses the same top-eight selection budget, but ranks partners by distance. The chain-only graph removes all long-range edges.

We also test two simple baselines. One uses graph size. The other uses node-type proportions plus size, but no edges. We call this the histogram baseline.

Each graph model is trained three times. We ask: can it beat the histogram? And does adding contact edges improve on the chain-only graph?`,
  restest: `[~0:50]
First, we test on about four thousand unseen simulated proteins. Lower error is better.

Look at the orange bar: the chain-only graph. Its average error is thirty-three percent lower than the histogram baseline, shown by the dashed line. All three training runs beat that baseline.

So yes, a simple chain-based graph model is useful for this task.

But look at the blue bar. Adding our contact edges makes the error higher. This is our main surprise: more edges do not always mean better predictions.`,
  resexp: `[~0:40]
Does this result carry over to real measurements?

Here we test on 151 proteins measured in the lab. The models were trained only on simulations.

All three graph models have lower average error than the baselines. The contact-edge and chain-only models improve on the histogram by about eight to nine percent.

Their errors are close, so we see no clear extra benefit from contact edges here.

This led us to ask: what kinds of edges are we actually adding?`,
  limits: `[~1:00]
We found two clues.

First, our edge score uses both node types and distance along the chain. But the distance term varies much more: over a thousand-fold, compared with about two-fold for node types. So distance dominates. Ninety-seven percent of selected partners are in the farthest available distance band.

Second, look at these six sequences. They have the same node-type counts, but different orders. Their measured sizes span 0.73 nanometres. The chain-only predictions span 0.47, but the contact-edge predictions span just 0.06.

In this group, the contact-edge model is less sensitive to order. This is a clue, not yet proof of why it performs worse.`,
  close: `[~0:45]
Our results show that a simple chain-based graph model is useful for this task. But more edges do not always mean better predictions.

The next step is to choose better long-range links and study how to combine them with local messages. We also want to test whether a wider message-passing range helps with longer chains.

The main takeaway is: graphs help, but how we connect the nodes matters.

Thank you.`,
};

// ---------- 8 the task in graph terms ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "The task in graph terms: one graph per protein");
const mapRow = (a, b, col) => [td(a), { text: b, options: { color: col || C.text1, bold: !!col, fill: { color: C.background1 } } }];
s.addTable([
  [th("Protein"), th("Graph")],
  mapRow("A chain of amino acids", "One graph, up to 512 nodes"),
  mapRow("Each amino acid", "Node: one of 20 types, plus position"),
  mapRow("Neighbours along the chain", "Local edges", THEME.colors.accent1),
  mapRow("Candidate long-range pairs", "Select up to 8 partners per node", THEME.colors.accent3),
  mapRow("Size of the chain in space (Rg)", "Target: one number per graph"),
], tblOpts({ x: 0.6, y: 1.75, w: 7.25, colW: [3.1, 4.15], rowH: 0.52, objectName: name("mapping-table") }));
txt(s, [
  { text: "Graph-level regression. ", options: { bold: true, color: C.text1 } },
  { text: "At prediction time, we use the sequence without a fixed 3D structure." },
], { x: 0.6, y: 5.15, w: 7.0, h: 0.95 });
caption(s, "Long-range partners come from contact statistics counted in 28 million simulation frames.", 0.6, 6.15, 7.0, 0.5);
img(s, "adjacency_long.png", 8.1, 1.75, 4.6, 4.6, "Adjacency matrix of a 155-node graph: blue diagonal band of local edges, scattered orange long-range edges far from the diagonal");
caption(s, "Adjacency of one 155-node graph. About 1 in 10 node pairs is an edge.", 8.1, 6.4, 4.63, 0.45);
s.addNotes(NOTE.sparse);

// ---------- 9 GAT ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "Edge-aware graph attention network");
[["Protein graph", "Nodes are amino acids"],
 ["2 attention layers", "Each node weights messages from its neighbours"],
 ["Pool all nodes", "Mean and max, plus log graph size"],
 ["Predicted Rg", "One number per graph"],
].forEach(([h, b], i) => {
  const x = 0.6 + i * 3.12;
  rule(s, x, 2.1, 2.6, i === 1 ? C.accent2 : C.accent1, 2.5);
  block(s, x, 2.25, 2.6, 1.6, h, b, { headColor: C.text1 });
  if (i < 3) s.addShape(S.RIGHT_ARROW, { x: x + 2.68, y: 2.32, w: 0.36, h: 0.3, fill: { color: C.accent4 }, line: { color: C.accent4, width: 0 }, objectName: name("arrow") });
});
rule(s, 0.6, 4.3, 12.13);
txt(s, "Attention score of each edge", { x: 0.6, y: 4.6, w: 8, h: 0.4, fontSize: 17, bold: true, color: C.accent1 });
txt(s, [
  { text: "u(i,j) = LeakyReLU(a_src·Wh(i) + a_dst·Wh(j) + " },
  { text: "a_edge·MLP(e(i,j))", options: { bold: true, color: C.accent3 } }, { text: ")" },
], { x: 0.6, y: 5.05, w: 12.1, h: 0.5, fontSize: 22, color: C.text1 });
txt(s, [
  { text: "Edge features enter the score, so the model learns how much to trust each long-range edge. " },
  { text: "18,721 parameters", options: { bold: true, color: C.text1 } }, { text: " in total." },
], { x: 0.6, y: 5.8, w: 12.1, h: 0.9 });
s.addNotes(NOTE.gat);

// ---------- 10 experiment design ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Method" });
head(s, "EXPERIMENT", "The test: three graphs and two baselines");
[["variant_contact.png", "Contact edges", "Our model", C.accent1],
 ["variant_distance.png", "Distance edges", "Same top-8 budget, distance-only ranking", C.accent6],
 ["variant_local.png", "Chain only", "No long-range edges", C.accent3],
].forEach(([f, h, b, col], i) => {
  const y = 1.7 + i * 1.3;
  img(s, f, 0.6, y, 3.7, 1.1, `Schematic of the ${h.toLowerCase()} graph`);
  block(s, 4.55, y + 0.05, 3.3, 1.2, h, b, { headColor: col });
});
txt(s, "Two baselines that ignore edges", { x: 8.45, y: 1.75, w: 4.28, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
txt(s, [
  { text: "Graph size: ", options: { bold: true, color: C.text1 } }, { text: "Rg as a power of node count", options: { breakLine: true } },
  { text: "Node-type histogram: ", options: { bold: true, color: C.text1 } }, { text: "node-type proportions, plus size" },
], { x: 8.45, y: 2.25, w: 4.28, h: 1.8, paraSpaceAfter: 10 });
rule(s, 8.45, 4.15, 4.28);
txt(s, "Train on 18,860 simulated proteins. Each graph model trains 3 times.", { x: 8.45, y: 4.3, w: 4.28, h: 0.95 });
txt(s, [
  { text: "Compare the chain-based GNN with a histogram, then test the added " },
  { text: "contact edges", options: { bold: true, color: C.accent1 } }, { text: "." },
], { x: 0.6, y: 5.75, w: 12.1, h: 0.8, fontSize: 22, color: C.text1 });
s.addNotes(NOTE.train);

// ---------- 11 results: simulations ----------
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Results" });
head(s, "RESULTS", "Simulations: the chain-only graph cuts error by a third");
ablationChart(s, "test", [0.1240, 0.0984], 0.45, 1.6, 7.1, 4.85, 0.15, 0.03);
caption(s, "Error on 4,103 unseen simulated proteins. Dots: 3 training runs. Dashed line: histogram.", 0.6, 6.45, 7.0, 0.5);
bigStat(s, "33% lower", 7.95, 1.8, 4.8, C.accent3, 48);
txt(s, "average error than the histogram. All 3 runs beat the baseline.", { x: 7.95, y: 2.7, w: 4.78, h: 0.95 });
rule(s, 7.95, 3.9, 4.78);
block(s, 7.95, 4.1, 4.78, 1.0, "Learning along the chain", "The chain-only GNN beats the linear histogram baseline.", { headColor: C.text1 });
block(s, 7.95, 5.3, 4.78, 1.0, "Contact edges make it worse", "Adding them raises the average test error.", { headColor: C.text1 });
s.addNotes(NOTE.restest);

// ---------- 12 results: lab measurements ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Results" });
head(s, "RESULTS", "Lab measurements: every graph model beats the baselines");
ablationChart(s, "exp151", [0.4159, 0.3310], 0.45, 1.6, 7.1, 4.85, 0.45, 0.1);
caption(s, "Error on 151 lab-measured proteins. Dots: 3 training runs. Dashed line: histogram.", 0.6, 6.45, 7.0, 0.5);
bigStat(s, "8–9% lower", 7.95, 1.8, 4.8, C.accent3, 48);
txt(s, "error than the histogram for the chain-only and contact-edge graphs", { x: 7.95, y: 2.7, w: 4.78, h: 0.95 });
rule(s, 7.95, 3.9, 4.78);
block(s, 7.95, 4.1, 4.78, 1.0, "No clear long-range benefit", "Contact-edge and chain-only errors are close.", { headColor: C.text1 });
block(s, 7.95, 5.25, 4.78, 1.2, "Trained on simulations only", "Errors are higher on lab measurements than on simulations.", { headColor: C.text1 });
s.addNotes(NOTE.resexp);

// ---------- 13 diagnosis ----------
pres.addSection({ title: "Wrap-up" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
head(s, "DIAGNOSIS", "Why edge choice matters");
txt(s, "1. Distance dominates edge selection", { x: 0.6, y: 1.7, w: 6.0, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
txt(s, "Edge score = how often these two node types touch, divided by how often any pair this far apart touches", { x: 0.6, y: 2.15, w: 6.0, h: 0.9, fontSize: 17, color: C.text2 });
img(s, "edge_scales.png", 0.6, 3.05, 5.2, 3.23, "Log-scale comparison: the distance term spans about 1,300-fold, the node-type pair term only 2.1-fold");
txt(s, "97% of partners lie in the farthest available distance band.", { x: 0.6, y: 6.35, w: 6.0, h: 0.5, bold: true, color: C.text1 });
txt(s, "2. Reduced sensitivity to node order", { x: 7.0, y: 1.7, w: 5.73, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
txt(s, "Same node-type counts, different orders along the chain. How much do measured and predicted sizes vary?", { x: 7.0, y: 2.15, w: 5.73, h: 0.95 });
s.addChart(pres.charts.BAR, [{ name: "Spread of Rg (nm)", labels: ["Measured", "Chain only", "Contact edges"], values: [0.73, 0.47, 0.06] }], {
  x: 6.85, y: 3.2, w: 5.88, h: 2.7, barDir: "bar", objectName: name("order-chart"), showLegend: false,
  chartColors: [HEX.ink, HEX.orangeBar, HEX.blueBar], barGapWidthPct: 45, catAxisOrientation: "maxMin",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00 \"nm\"", dataLabelFontSize: 15, dataLabelFontFace: "Calibri", dataLabelColor: HEX.ink,
  catAxisLabelFontSize: 16, catAxisLabelFontFace: "Calibri", catAxisLabelColor: HEX.ink, catAxisLineColor: HEX.body,
  valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 0.9, valGridLine: { style: "none" },
});
caption(s, "Rg ranges for 6 sequences (107 nodes), using seed-averaged predictions. For the 334-node group, rankings remain weak.", 7.0, 5.95, 5.73, 0.75);
s.addNotes(NOTE.limits);

// ---------- 14 close ----------
s = pres.addSlide({ masterName: "Statement", sectionTitle: "Wrap-up" });
head(s, "TAKEAWAYS", "What we can say, and what comes next");
[["1", "Chain-based GNN works", "A chain-only GNN beats the histogram baseline: 33% lower average error on simulations and better on lab measurements."],
 ["2", "Edge choice needs improvement", "The current score mostly selects the farthest band. It gives no clear gain on lab data."],
 ["3", "Next: graph design", "Test distance-calibrated edges with separate local and long-range messages, and larger receptive fields for longer chains."],
].forEach(([n, h, b], i) => {
  const x = 0.6 + i * 4.125;
  const col = i === 0 ? C.accent2 : C.accent4;
  rule(s, x, 1.95, 3.75, col, 2);
  txt(s, n, { x, y: 2.1, w: 1, h: 0.7, fontSize: 40, bold: true, color: col, paraSpaceAfter: 0 });
  block(s, x, 2.9, 3.75, 2.5, h, b, { headSize: 22, headColor: C.background1, bodyColor: C.background2 });
});
txt(s, "Thank you. Questions?", { x: 0.6, y: 5.7, w: 12.1, h: 0.75, fontSize: 36, bold: true, color: C.background1 });
s.addNotes(NOTE.close);

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
