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
  const labels = ["Length only", "Composition", "Graph: contact edges", "Graph: distance edges", "Graph: chain only"];
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

// ---------- speaker notes for slides 8-14 (about 6 minutes in total) ----------
const NOTE = {
  sparse: `[~0:45]
Thanks. So our graph has two kinds of edges. The blue ones are local: each residue links to its neighbours, up to two steps away along the chain, so messages can travel along the sequence.

The orange ones are long-range: each residue also links to eight partners chosen by our contact prior. The idea is to connect residues that might touch in 3D.

Each edge carries a few features, like the contact frequency and the distance along the chain. Only about one in ten pairs becomes an edge, so the graph stays small even for long chains.`,
  gat: `[~0:50]
The model is a graph attention network. It runs two rounds of message passing. In each round, every residue collects messages from its neighbours and uses attention to decide how much to listen to each one.

The key detail is here, in orange: the edge features go into the attention score. So the model can learn how much to trust our contact prior, instead of us fixing it by hand.

After two rounds, we pool over the whole chain, add the chain length, and predict Rg. The whole model has under nineteen thousand parameters, which is tiny by deep-learning standards.`,
  train: `[~0:50]
To find out whether the graph really helps, we set up a fair test. We train three versions of the same network.

The first has our contact edges. The second is a control: the same number of long-range edges, but picked by distance alone. The third has no long-range edges at all, just the chain.

We compare them with two simple baselines that use no graph. One uses only the chain length, and one adds the amino-acid composition.

So, if the graph helps, the graph models should beat composition. And if our contact edges help, the first model should win.`,
  restest: `[~1:00]
Here are the results on four thousand simulated proteins that the models never saw. Lower is better.

The grey bars are the baselines, and composition, this dashed line, is the one to beat.

Now the orange bar: the chain-only graph. Its error is about a third lower than composition, and all three training runs, these dots, agree. So message passing along the chain clearly helps.

But look at the first blue bar. When we add our contact edges, the error goes up, and the model falls behind composition. So the graph helps, but our long-range edges hold it back.`,
  resexp: `[~0:45]
Next, 151 proteins whose size was measured in the lab. Remember, the models only ever saw simulations.

Here, every graph model beats both baselines. The chain-only and the contact-edge models are tied, both eight to nine percent better than composition. So on real data, the long-range edges neither help nor hurt.

The errors are larger than on simulations, because we inherit the gap between the simulations and real proteins.

So why do our contact edges fail?`,
  limits: `[~1:00]
We looked at how they are chosen. Our edge score divides the contact frequency of a residue pair by the average frequency at that distance. The chemistry part varies only about two-fold. The distance part varies more than a thousand-fold.

So distance wins. Ninety-seven percent of the chosen partners are simply the farthest residues, and the amino-acid type barely matters. That is why the distance-only control behaves the same.

And it costs us residue order. Here are six sequences with the same amino acids in different orders. Their measured sizes differ a lot. The chain-only model picks up much of that difference. With our contact edges, the predictions barely move.`,
  close: `[~0:35]
To wrap up. First, the graph helps: a tiny network passing messages along the chain beats composition, on simulations and on real measurements.

Second, our long-range edges are the bottleneck, because sequence distance, rather than chemistry, decides which edges we draw.

Third, the next step is to rebuild the contact table for each distance band, so that chemistry picks the edges.

Thank you. We are happy to take questions.`,
};

// ---------- 8 two kinds of edges ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "Two kinds of edges in one sparse graph");
img(s, "adjacency_long.png", 0.6, 1.7, 5.0, 5.0, "Adjacency matrix of a 155-residue chain: blue diagonal band of local edges, scattered orange long-range edges far from the diagonal");
block(s, 6.2, 1.8, 6.5, 1.35, "Local edges", "Neighbours up to 2 steps along the chain, so messages travel along the sequence", { headColor: C.accent1 });
block(s, 6.2, 3.3, 6.5, 1.35, "Long-range edges", "Each residue’s top 8 partners by the contact prior, meant to link residues that touch in 3D", { headColor: C.accent3 });
rule(s, 6.2, 4.9, 6.5);
txt(s, "Every edge carries features such as contact frequency and distance along the chain. About 1 in 10 residue pairs becomes an edge, so the graph stays small for long chains.", { x: 6.2, y: 5.1, w: 6.5, h: 1.4 });
s.addNotes(NOTE.sparse);

// ---------- 9 GAT ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD", "Edge-aware graph attention network");
[["Residue graph", "Nodes are residues"],
 ["2 rounds of message passing", "Attention over each residue’s neighbours"],
 ["Pool the chain", "Mean and max over residues, plus chain length"],
 ["Predicted Rg", "One number per sequence"],
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
  { text: "The edge-feature term lets the model learn how much to trust the contact prior. " },
  { text: "18,721 parameters", options: { bold: true, color: C.text1 } }, { text: " in total." },
], { x: 0.6, y: 5.8, w: 12.1, h: 0.9 });
s.addNotes(NOTE.gat);

// ---------- 10 experiment design ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Method" });
head(s, "EXPERIMENT", "The test: three graphs and two baselines");
[["variant_contact.png", "Contact edges", "Our model", C.accent3],
 ["variant_distance.png", "Distance edges", "Control: as many far edges, picked by distance", C.accent6],
 ["variant_local.png", "Chain only", "No long-range edges", C.accent1],
].forEach(([f, h, b, col], i) => {
  const y = 1.7 + i * 1.3;
  img(s, f, 0.6, y, 3.7, 1.1, `Schematic of the ${h.toLowerCase()} graph`);
  block(s, 4.55, y + 0.05, 3.3, 1.2, h, b, { headColor: col });
});
txt(s, "Two baselines with no graph", { x: 8.45, y: 1.75, w: 4.28, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
txt(s, [
  { text: "Length only: ", options: { bold: true, color: C.text1 } }, { text: "size grows as a power of chain length", options: { breakLine: true } },
  { text: "Composition: ", options: { bold: true, color: C.text1 } }, { text: "adds the fraction of each of the 20 amino acids" },
], { x: 8.45, y: 2.25, w: 4.28, h: 1.8, paraSpaceAfter: 10 });
rule(s, 8.45, 4.15, 4.28);
txt(s, "Every model trains on 18,860 simulated chains. Each graph trains 3 times.", { x: 8.45, y: 4.3, w: 4.28, h: 0.95 });
txt(s, [
  { text: "If the graph helps, the graph models beat composition. If our contact edges help, " },
  { text: "contact edges", options: { bold: true, color: C.accent3 } }, { text: " win." },
], { x: 0.6, y: 5.75, w: 12.1, h: 0.8, fontSize: 22, color: C.text1 });
s.addNotes(NOTE.train);

// ---------- 11 results: simulations ----------
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Results" });
head(s, "RESULTS", "Simulations: the chain-only graph cuts error by a third");
ablationChart(s, "test", [0.1240, 0.0984], 0.45, 1.6, 7.1, 4.85, 0.15, 0.03);
caption(s, "Error on 4,103 unseen simulated chains. Dots: 3 training runs. Dashed line: composition.", 0.6, 6.45, 7.0, 0.5);
bigStat(s, "33% lower", 7.95, 1.8, 4.8, C.accent3, 48);
txt(s, "error than composition with the chain-only graph, in all 3 training runs", { x: 7.95, y: 2.7, w: 4.78, h: 0.95 });
rule(s, 7.95, 3.9, 4.78);
block(s, 7.95, 4.1, 4.78, 1.6, "Contact edges make it worse", "Adding our long-range edges raises the error above composition.", { headColor: C.text1 });
s.addNotes(NOTE.restest);

// ---------- 12 results: lab measurements ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Results" });
head(s, "RESULTS", "Lab measurements: every graph model beats the baselines");
ablationChart(s, "exp151", [0.4159, 0.3310], 0.45, 1.6, 7.1, 4.85, 0.45, 0.1);
caption(s, "Error on 151 lab-measured proteins. Dots: 3 training runs. Dashed line: composition.", 0.6, 6.45, 7.0, 0.5);
bigStat(s, "8–9% lower", 7.95, 1.8, 4.8, C.accent3, 48);
txt(s, "error than composition for the chain-only and contact-edge graphs", { x: 7.95, y: 2.7, w: 4.78, h: 0.95 });
rule(s, 7.95, 3.9, 4.78);
block(s, 7.95, 4.1, 4.78, 1.0, "Long-range edges make no difference", "The two graphs tie.", { headColor: C.text1 });
block(s, 7.95, 5.25, 4.78, 1.2, "Trained on simulations only", "All models inherit the gap between simulation and experiment.", { headColor: C.text1 });
s.addNotes(NOTE.resexp);

// ---------- 13 diagnosis ----------
pres.addSection({ title: "Wrap-up" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
head(s, "DIAGNOSIS", "Why our long-range edges fail");
txt(s, "1. Distance decides which edges we draw", { x: 0.6, y: 1.7, w: 6.0, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
img(s, "edge_scales.png", 0.45, 2.2, 5.9, 3.67, "Log-scale comparison: the distance term spans about 1,300-fold, the amino-acid pair term only 2.1-fold");
txt(s, "The distance term varies over 1,000 times more than chemistry, so 97% of chosen partners are simply the farthest residues.", { x: 0.6, y: 5.95, w: 6.0, h: 0.95 });
txt(s, "2. So the model loses residue order", { x: 7.0, y: 1.7, w: 5.73, h: 0.4, fontSize: 20, bold: true, color: C.text1 });
txt(s, "Six sequences with the same amino acids in different orders. How much do their sizes differ?", { x: 7.0, y: 2.2, w: 5.73, h: 0.95 });
s.addChart(pres.charts.BAR, [{ name: "Spread of Rg (nm)", labels: ["Measured", "Chain only", "Contact edges"], values: [0.73, 0.47, 0.06] }], {
  x: 6.85, y: 3.2, w: 5.88, h: 2.7, barDir: "bar", objectName: name("order-chart"), showLegend: false,
  chartColors: [HEX.ink, HEX.orangeBar, HEX.blueBar], barGapWidthPct: 45, catAxisOrientation: "maxMin",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00 \"nm\"", dataLabelFontSize: 15, dataLabelFontFace: "Calibri", dataLabelColor: HEX.ink,
  catAxisLabelFontSize: 16, catAxisLabelFontFace: "Calibri", catAxisLabelColor: HEX.ink, catAxisLineColor: HEX.body,
  valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 0.9, valGridLine: { style: "none" },
});
caption(s, "Spread of Rg across the six sequences (107 residues), mean of 3 runs. For a 334-residue group, no model sees order yet.", 7.0, 5.95, 5.73, 0.75);
s.addNotes(NOTE.limits);

// ---------- 14 close ----------
s = pres.addSlide({ masterName: "Statement", sectionTitle: "Wrap-up" });
head(s, "TAKEAWAYS", "What we can say, and what comes next");
[["1", "The graph helps", "Message passing along the chain beats composition: a third lower error on simulations, and better on lab data."],
 ["2", "Our long-range edges are the bottleneck", "Sequence distance picks them, so they add far-away links and hide residue order."],
 ["3", "Next: edges chosen by chemistry", "Rebuild the contact table for each distance band, from training chains only."],
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
