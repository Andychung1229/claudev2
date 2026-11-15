// Build ContactGAT talk as .pptx. Usage: node build.js <figs dir> <slides html dir> <out.pptx> <apply_theme.js>
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const [FIGS, HTML, OUT, APPLY] = process.argv.slice(2);
const { applyTheme } = require(APPLY);

const THEME = {
  name: "ContactGAT",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "13233A", lt1: "FFFFFF", dk2: "44505F", lt2: "E9EEF3",
    accent1: "2F6FB0", accent2: "D9692A", accent3: "A34D18", accent4: "8FB8E3",
    accent5: "1F3452", accent6: "5E6875", hlink: "2F6FB0", folHlink: "5E6875",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Contact-frequency graph attention for IDP radius of gyration";
pres.author = "Tian Jiaxin, Chung Ka Wai";
const C = pres.SchemeColor;
const S = pres.shapes;
const fig = (f) => path.join(FIGS, f);

// speaker notes come from the web deck's <aside> blocks
const notes = (id) => {
  const m = fs.readFileSync(path.join(HTML, `${id}.html`), "utf8").match(/<aside>([\s\S]*?)<\/aside>/);
  return m ? m[1].replace(/&amp;/g, "&").replace(/&gt;/g, ">").replace(/&lt;/g, "<").trim() : "";
};

// ---------- layouts ----------
const footer = (color) => [
  { text: { text: "Tian and Chung · COMP 5222", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color, margin: 0 } } },
];
const headPh = (eyeColor, titleColor) => [
  { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.38, w: 12.1, h: 0.32, fontSize: 12, bold: true, color: eyeColor, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.74, w: 12.1, h: 0.62, fontSize: 30, bold: true, color: titleColor, margin: 0, valign: "top" }, text: "" } },
];
const num = (color) => ({ x: 12.13, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color, align: "right" });

pres.defineSlideMaster({
  title: "Cover", background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.0, w: 11.8, h: 2.3, fontSize: 40, bold: true, color: C.background1, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: 0.6, y: 4.45, w: 10.5, h: 0.9, fontSize: 18, color: C.background2, margin: 0, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({ title: "Content", background: { color: C.background1 }, objects: [...headPh(C.accent1, C.text1), ...footer(C.accent6)], slideNumber: num(C.accent6) });
pres.defineSlideMaster({ title: "Content Tint", background: { color: C.background2 }, objects: [...headPh(C.accent1, C.text1), ...footer(C.accent6)], slideNumber: num(C.accent6) });
pres.defineSlideMaster({ title: "Statement", background: { color: C.text1 }, objects: [...headPh(C.accent4, C.background1), ...footer(C.accent4)], slideNumber: num(C.accent4) });

// ---------- helpers ----------
let objN = 0;
const name = (s) => `${s}-${++objN}`;
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(S.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0.75 }, rectRadius: 0.1, objectName: name("card") });
}
function txt(slide, content, o) {
  slide.addText(content, { isTextBox: true, margin: 0, valign: "top", fontSize: 15, color: C.text2, paraSpaceAfter: 4, objectName: name("text"), ...o });
}
// heading + body paragraphs inside a card
function cardText(slide, x, y, w, h, head, body, o = {}) {
  const hc = o.headColor || C.text1;
  const bc = o.bodyColor || C.text2;
  const runs = [{ text: head, options: { bold: true, fontSize: o.headSize || 18, color: hc, breakLine: true, paraSpaceAfter: 6 } }];
  const parts = Array.isArray(body) ? body : [{ text: body }];
  parts.forEach((p, i) => runs.push({ text: p.text, options: { fontSize: o.bodySize || 15, color: bc, ...p.options, breakLine: i < parts.length - 1 && !(p.options && p.options.breakLine === false) } }));
  txt(slide, runs, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: h - 0.4 });
}
function head(slide, eyebrow, title) {
  slide.addText(eyebrow, { placeholder: "eyebrow" });
  slide.addText(title, { placeholder: "title" });
}
function img(slide, file, x, y, w, h, alt) {
  slide.addImage({ path: fig(file), x, y, w, h, altText: alt, objectName: name("figure") });
}
function bigStat(slide, value, x, y, w, color = C.accent1) {
  txt(slide, value, { x, y, w, h: 0.75, fontSize: 44, bold: true, color, paraSpaceAfter: 0 });
}

// ---------- 1 cover ----------
pres.addSection({ title: "Background" });
let s = pres.addSlide({ masterName: "Cover", sectionTitle: "Background" });
txt(s, "COMP 5222 · PROJECT PRESENTATION", { x: 0.6, y: 1.45, w: 10, h: 0.35, fontSize: 13, bold: true, color: C.accent4, charSpacing: 2 });
s.addText("Contact-frequency graph attention for predicting the radius of gyration of intrinsically disordered proteins", { placeholder: "title" });
s.addText("Turning simulation contact statistics into a residue graph, and predicting protein size with an 18.7k-parameter graph attention network", { placeholder: "sub" });
txt(s, "Tian Jiaxin  ·  Chung Ka Wai", { x: 0.6, y: 6.2, w: 8, h: 0.45, fontSize: 18, bold: true, color: C.background1 });
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
head(s, "OUR APPROACH", "Give the model the residue pairs directly, as a graph");
[["1", "Simulation trajectories", "Human IDRome: 28,058 chains, ~1,000 frames each", "Offline, once"],
 ["2", "Contact prior", "20 × 20 table: how often each amino-acid pair is within 8 Å", "Offline, once"],
 ["3", "Residue graph", "One node per residue; local + top-k contact edges", "Per sequence"],
 ["4", "Edge-aware GAT", "Message passing → pooling → predicted Rg", "Per sequence"],
].forEach(([n, h, b, tag], i) => {
  const x = 0.6 + i * 3.19;
  card(s, x, 1.9, 2.5, 2.95, C.accent5);
  txt(s, [
    { text: n, options: { fontSize: 28, bold: true, color: C.accent4, breakLine: true, paraSpaceAfter: 4 } },
    { text: h, options: { fontSize: 18, bold: true, color: C.background1, breakLine: true, paraSpaceAfter: 6 } },
    { text: b, options: { fontSize: 14, color: C.background2 } },
  ], { x: x + 0.2, y: 2.05, w: 2.1, h: 2.2 });
  txt(s, tag, { x: x + 0.2, y: 4.3, w: 2.1, h: 0.35, fontSize: 13, bold: true, color: i < 2 ? C.accent4 : C.background1 });
  if (i < 3) s.addShape(S.RIGHT_ARROW, { x: x + 2.62, y: 3.2, w: 0.45, h: 0.35, fill: { color: C.accent4 }, line: { color: C.accent4 }, objectName: name("arrow") });
});
txt(s, [
  { text: "Pairwise physics moves from " }, { text: "learned weights", options: { bold: true, color: C.background1 } },
  { text: " into the " }, { text: "input graph", options: { bold: true, color: C.background1 } },
  { text: ". A new sequence needs only steps 3–4: no simulation, one forward pass." },
], { x: 0.6, y: 5.3, w: 12.1, h: 1.0, fontSize: 20, color: C.background2 });
s.addNotes(notes("idea"));

// ---------- 6 prior ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD · STEP 1–2", "Learn a contact prior from 28 million simulation frames");
card(s, 0.6, 1.65, 6.7, 3.05);
cardText(s, 0.6, 1.65, 6.7, 1.2, "How we count", [
  { text: "In every frame, a pair (i, j) with |i − j| ≥ 2 is a " }, { text: "contact", options: { bold: true, breakLine: false } },
  { text: " if closer than 8 Å. Pooled by amino-acid type:" },
].map((p) => ({ ...p, options: { ...(p.options || {}), breakLine: false } })));
s.addShape(S.RECTANGLE, { x: 0.85, y: 3.0, w: 6.2, h: 0.95, fill: { color: C.background1 }, line: { color: C.background1 }, objectName: name("equation-box") });
txt(s, [
  { text: "f(a,b) = contacts / opportunities", options: { breakLine: true } },
  { text: "ε(a,b) = log( f(a,b) / mean f )" },
], { x: 1.05, y: 3.08, w: 5.8, h: 0.8, fontSize: 16, color: C.text1, valign: "middle", paraSpaceAfter: 2 });
txt(s, "28,058 chains · 28,055,120 frames → a 12 KB table, built once.", { x: 0.85, y: 4.1, w: 6.2, h: 0.35, fontSize: 12, color: C.accent6 });
card(s, 0.6, 4.9, 6.7, 1.8);
cardText(s, 0.6, 4.9, 6.7, 1.8, "What it learned", [
  { text: "Enriched: ", options: { bold: true, color: C.accent3, breakLine: false } }, { text: "W–W (+0.48), A–A, Y–Y (+0.35), aromatic stickers." },
  { text: "Depleted: ", options: { bold: true, color: C.accent1, breakLine: false } }, { text: "K–P (−0.27), D–P, E–P, proline with charged residues." },
]);
img(s, "contact_heatmap.png", 7.55, 1.75, 5.175, 4.6, "20 by 20 heatmap of amino-acid contact enrichment; aromatic pairs are enriched, proline with charged residues is depleted");
s.addNotes(notes("prior"));

// ---------- 7 graph ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD · STEP 3", "Turn each sequence into a residue graph");
img(s, "graph_one_node.png", 0.87, 1.55, 11.6, 3.335, "A real 36-residue test sequence; residue F16 has blue local edges to its neighbours and orange arcs to eight non-local partners");
txt(s, [
  { text: "Real test-set IDR (36 aa). Edges chosen for one residue, F16: " },
  { text: "local neighbours", options: { bold: true, color: C.accent1 } }, { text: " and its " },
  { text: "8 non-local partners", options: { bold: true, color: C.accent3 } }, { text: "." },
], { x: 0.6, y: 4.95, w: 12.1, h: 0.35, fontSize: 12, color: C.accent6 });
[["Nodes", C.text1, "One per residue: 20-dim one-hot + position i / (N − 1)"],
 ["Local edges", C.accent1, "1 ≤ |i − j| ≤ 2, plus self-loops. Keep the chain connected."],
 ["Non-local edges", C.accent3, "Each residue keeps its top k = 8 partners by f(a,b) / p(band), then made undirected."],
].forEach(([h, col, b], i) => {
  const x = 0.6 + i * 4.125;
  card(s, x, 5.4, 3.88, 1.4);
  cardText(s, x, 5.38, 3.88, 1.4, h, b, { headColor: col, headSize: 17, bodySize: 14 });
});
s.addNotes(notes("graph"));

// ---------- 8 sparse ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD · STEP 3", "The graph is sparse, and every edge carries features");
img(s, "adjacency_long.png", 0.6, 1.65, 5.0, 5.0, "Adjacency matrix of a 155-residue chain: blue diagonal band of local edges, scattered orange non-local edges far from the diagonal");
card(s, 5.9, 1.65, 6.83, 2.15);
bigStat(s, "10%", 6.15, 1.8, 3);
txt(s, "of residue pairs become edges in this 155-residue chain (1,192 of 11,935). Edges grow as O(N·(w + k)), not O(N²).", { x: 6.15, y: 2.6, w: 6.33, h: 1.0 });
card(s, 5.9, 4.0, 6.83, 2.65);
txt(s, [
  { text: "10 numbers per edge", options: { bold: true, fontSize: 18, color: C.text1, breakLine: true, paraSpaceAfter: 8 } },
  { text: "Contact frequency f(a,b) from the prior", options: { bullet: true, breakLine: true } },
  { text: "Sequence distance |i − j| / (N − 1)", options: { bullet: true, breakLine: true } },
  { text: "Distance band, one-hot: 1, 2–4, 5–8, 9–16, 17–32, >32", options: { bullet: true, breakLine: true } },
  { text: "Local-edge flag and self-loop flag", options: { bullet: true } },
], { x: 6.15, y: 4.2, w: 6.33, h: 2.3, paraSpaceAfter: 6 });
s.addNotes(notes("sparse"));

// ---------- 9 GAT ----------
s = pres.addSlide({ masterName: "Content", sectionTitle: "Method" });
head(s, "METHOD · STEP 4", "An edge-aware graph attention network reads the graph");
[["ATTENTION SCORE (PER HEAD)", "u(i,j) = LeakyReLU( a_src · Wh(i) + a_dst · Wh(j) + a_edge · MLP(e(i,j)) )"],
 ["NORMALISE OVER NEIGHBOURS ONLY", "α(i,j) = softmax over j ∈ N(i) of u(i,j)"],
 ["UPDATE (RESIDUAL + LAYERNORM)", "h′(i) = ELU( LayerNorm( h(i) + Σ_j α(i,j) · Wh(j) ) )"],
 ["READOUT", "ln Rg = MLP( mean h ‖ max h ‖ log N )"],
].forEach(([label, eq], i) => {
  const y = 1.65 + i * 1.28;
  txt(s, label, { x: 0.6, y, w: 7.0, h: 0.28, fontSize: 11, bold: true, color: C.accent1, charSpacing: 1 });
  s.addShape(S.RECTANGLE, { x: 0.6, y: y + 0.3, w: 7.0, h: 0.78, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: name("equation-box") });
  txt(s, eq, { x: 0.8, y: y + 0.3, w: 6.6, h: 0.78, fontSize: 15, color: C.text1, valign: "middle", paraSpaceAfter: 0 });
});
[["The prior steers attention", "Contact frequency enters the score as an edge feature, not as a fixed weight. The model learns how much to trust it."],
 ["Small on purpose", [{ text: "2 layers × 4 heads × 16 channels: ", options: { breakLine: false } }, { text: "18,721 parameters", options: { bold: true } }]],
 ["Length stays visible", "log N goes straight into the readout, next to mean and max pooling."],
].forEach(([h, b], i) => {
  const y = 1.65 + i * 1.72;
  card(s, 7.9, y, 4.83, 1.55);
  cardText(s, 7.9, y, 4.83, 1.55, h, b, { headSize: 17, bodySize: 14 });
});
s.addNotes(notes("gat"));

// ---------- 10 training ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Method" });
head(s, "METHOD · TRAINING", "Training on unseen-protein splits");
const th = (t, align = "left") => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 }, align } });
const td = (t, align = "left") => ({ text: t, options: { color: C.text1, fill: { color: C.background1 }, align } });
s.addTable([
  [th("Split (70 / 15 / 15)"), th("Chains, N ≤ 512", "right")],
  [td("Train"), td("18,860", "right")],
  [td("Validation"), td("4,020", "right")],
  [td("Test"), td("4,103", "right")],
], { x: 0.6, y: 1.65, w: 6.0, colW: [3.0, 3.0], rowH: 0.4, fontSize: 15, border: { type: "solid", pt: 0.75, color: "D3D9E0" }, margin: [3, 8, 3, 8], objectName: name("split-table") });
txt(s, [
  { text: "Regions from the ", options: { breakLine: false } }, { text: "same UniProt protein", options: { bold: true, breakLine: false } },
  { text: ", and identical sequences, stay in one split (15,331 groups)." },
], { x: 0.6, y: 3.5, w: 6.0, h: 0.75 });
txt(s, [
  { text: "Loss: MSE on ln Rg · AdamW, lr 10⁻³", options: { bullet: true, breakLine: true } },
  { text: "Batches grouped by length to fill the GPU", options: { bullet: true, breakLine: true } },
  { text: "Early stop on validation MAE (patience 15)", options: { bullet: true, breakLine: true } },
  { text: "~13 min on one RTX 5060 Ti", options: { bullet: true } },
], { x: 0.6, y: 4.4, w: 6.0, h: 2.2, paraSpaceAfter: 8 });
img(s, "val_curve.png", 6.95, 1.7, 5.78, 3.59, "Validation MAE and RMSE over 46 epochs, falling to about 0.10 nm with large jumps; best epoch 31");
txt(s, "Best epoch 31, stopped at 46. Validation error jumps between epochs.", { x: 6.95, y: 5.45, w: 5.78, h: 0.35, fontSize: 12, color: C.accent6 });
s.addNotes(notes("train"));

// ---------- 11 results: test ----------
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Results" });
head(s, "RESULTS · SIMULATED TEST SET", "On unseen proteins, the graph beats length alone");
img(s, "test_parity.png", 0.6, 1.65, 5.22, 4.9, "Parity plot of predicted versus simulated Rg for 4,103 test chains; points lie tightly along the diagonal");
const tdb = (t) => ({ text: t, options: { color: C.text1, bold: true, fill: { color: "E3ECF6" }, align: "right" } });
s.addTable([
  [th("4,103 test chains"), th("Length only", "right"), th("ContactGAT", "right")],
  [td("MAE (nm)"), td("0.124", "right"), tdb("0.100")],
  [td("RMSE (nm)"), td("0.210", "right"), tdb("0.173")],
  [td("R²"), td("0.972", "right"), tdb("0.981")],
  [td("Pearson r"), td("0.986", "right"), tdb("0.992")],
], { x: 6.15, y: 1.65, w: 6.58, colW: [2.6, 1.99, 1.99], rowH: 0.42, fontSize: 15, border: { type: "solid", pt: 0.75, color: "D3D9E0" }, margin: [3, 8, 3, 8], objectName: name("test-table") });
[["−19%", "MAE versus the length-only power law (Rg = R0·N^ν, fitted on train)"],
 ["36%", "of the variance that length cannot explain is captured by the graph model"],
].forEach(([v, b], i) => {
  const x = 6.15 + i * 3.39;
  card(s, x, 4.1, 3.19, 2.5);
  bigStat(s, v, x + 0.25, 4.3, 2.7);
  txt(s, b, { x: x + 0.25, y: 5.1, w: 2.69, h: 1.35, fontSize: 14 });
});
s.addNotes(notes("restest"));

// ---------- 12 results: experiment ----------
s = pres.addSlide({ masterName: "Content Tint", sectionTitle: "Results" });
head(s, "RESULTS · EXPERIMENTAL RG", "Trained only on simulations, it still tracks experiments");
img(s, "exp_parity.png", 0.6, 1.65, 5.22, 4.9, "Parity plot of predicted versus experimental Rg for 151 sequences; orange diamonds mark sequences contained in a training sequence");
s.addTable([
  [th("151 experimental Rg"), th("MAE", "right"), th("R²", "right"), th("r", "right")],
  [td("Length only"), td("0.416", "right"), td("0.744", "right"), td("0.865", "right")],
  [td("ContactGAT"), tdb("0.295"), tdb("0.846"), tdb("0.921")],
  [td("ContactGAT, no overlap (129)"), td("0.296", "right"), td("0.841", "right"), td("0.918", "right")],
], { x: 6.15, y: 1.65, w: 6.58, colW: [3.28, 1.1, 1.1, 1.1], rowH: 0.42, fontSize: 15, border: { type: "solid", pt: 0.75, color: "D3D9E0" }, margin: [3, 8, 3, 8], objectName: name("exp-table") });
card(s, 6.15, 3.6, 6.58, 1.65, C.background1);
cardText(s, 6.15, 3.6, 6.58, 1.65, "Bigger gain than on simulations", "MAE 0.42 → 0.30 nm vs length alone. The 22 orange sequences sit inside training chains; dropping them changes almost nothing.");
card(s, 6.15, 5.45, 6.58, 1.25, C.background1);
cardText(s, 6.15, 5.45, 6.58, 1.25, "Error is 3× the simulated test (0.30 vs 0.10 nm)", "We inherit the simulation model’s gap to experiment.");
s.addNotes(notes("resexp"));

// ---------- 13 limitations ----------
pres.addSection({ title: "Wrap-up" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
head(s, "LIMITATIONS & NEXT STEPS", "What we still need to fix");
[["Prior counted on all chains", "The contact table used all 28,058 trajectories, including validation and test. ", "Rebuild it from training chains only, as planned."],
 ["Prior has no distance bands", "f(a,b) is one 20 × 20 table, so dividing by p(band) mostly picks the farthest residues. ", "A band-resolved p(a,b,d)."],
 ["Ablations not run yet", "Only the length-only baseline so far, and one seed. ", "Local-chain GAT, prior-free graph, fixed aggregation; 3 seeds."],
 ["Which edges matter?", "No attention or edge-removal analysis yet. ", "Delete top-ranked vs random non-local edges and measure the change in Rg."],
].forEach(([h, b, nx], i) => {
  const x = 0.6 + (i % 2) * 6.18;
  const y = 1.7 + Math.floor(i / 2) * 2.6;
  card(s, x, y, 5.95, 2.4);
  s.addShape(S.OVAL, { x: x + 0.25, y: y + 0.25, w: 0.5, h: 0.5, fill: { color: C.accent3 }, line: { color: C.accent3 }, objectName: name("badge") });
  txt(s, String(i + 1), { x: x + 0.25, y: y + 0.25, w: 0.5, h: 0.5, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", paraSpaceAfter: 0 });
  txt(s, h, { x: x + 0.95, y: y + 0.3, w: 4.75, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
  txt(s, [{ text: b }, { text: "Next: ", options: { bold: true, color: C.text1 } }, { text: nx }], { x: x + 0.25, y: y + 0.95, w: 5.45, h: 1.3 });
});
s.addNotes(notes("limits"));

// ---------- 14 close ----------
s = pres.addSlide({ masterName: "Statement", sectionTitle: "Wrap-up" });
head(s, "TAKEAWAYS", "Putting residue pairs into the graph works, with a small model");
[["1", "Physics as input", "Simulation contacts become a 12 KB table that sets the graph’s edges and edge features. No simulation at prediction time."],
 ["2", "Small and accurate", "18.7k parameters: test MAE 0.10 nm (R² 0.98); experimental MAE 0.30 nm, down from 0.42 nm with length alone."],
 ["3", "Next", "Training-only, band-resolved prior, then the controlled ablations to show which graph choices help."],
].forEach(([n, h, b], i) => {
  const x = 0.6 + i * 4.125;
  card(s, x, 1.75, 3.88, 3.2, C.accent5);
  txt(s, [
    { text: n, options: { fontSize: 28, bold: true, color: C.accent4, breakLine: true, paraSpaceAfter: 4 } },
    { text: h, options: { fontSize: 18, bold: true, color: C.background1, breakLine: true, paraSpaceAfter: 6 } },
    { text: b, options: { fontSize: 15, color: C.background2 } },
  ], { x: x + 0.25, y: 1.95, w: 3.38, h: 2.8 });
});
txt(s, "Thank you — questions?", { x: 0.6, y: 5.45, w: 12.1, h: 0.7, fontSize: 32, bold: true, color: C.background1 });
s.addNotes(notes("close"));

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
