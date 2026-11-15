"""Composition baseline + edge-selection audit. Usage: check_story.py <COMP-5222 dir>"""
import csv, sys
from pathlib import Path
import numpy as np
R = Path(sys.argv[1]); AA = "ACDEFGHIKLMNPQRSTVWY"
rd = lambda p: list(csv.DictReader(open(p), delimiter="\t"))
def feats(seqs):
    X = []
    for s in seqs:
        n = len(s); X.append([1.0, np.log(n)] + [s.count(a) / n for a in AA[:-1]])
    return np.array(X)
def st(y, p):
    e = p - y; return f"MAE {np.abs(e).mean():.3f}  RMSE {np.sqrt((e**2).mean()):.3f}  R2 {1-(e**2).sum()/((y-y.mean())**2).sum():.3f}  r {np.corrcoef(y,p)[0,1]:.3f}"
tr = [r for r in rd(R/"data/processed/idrome_split_train.tsv") if int(r["seq_len"]) <= 512]
te = [r for r in rd(R/"data/processed/idrome_split_test.tsv") if int(r["seq_len"]) <= 512]
ex = rd(R/"data/processed/labels_exp151.tsv")
Xtr = feats([r["sequence"] for r in tr]); ytr = np.log([float(r["rg_nm"]) for r in tr])
lam = 1e-3 * np.eye(Xtr.shape[1]); lam[0, 0] = 0
w = np.linalg.solve(Xtr.T @ Xtr + lam, Xtr.T @ ytr)
for name, rows, key in (("test", te, "rg_nm"), ("exp151", ex, "rg_nm")):
    y = np.array([float(r[key]) for r in rows]); p = np.exp(feats([r["sequence"] for r in rows]) @ w)
    print(f"linear composition+logN  {name:7s} {st(y, p)}")
    if name == "test":
        L = np.polyfit(np.log([float(r['seq_len']) for r in tr]), ytr, 1)
        lp = np.polyval(L, np.log([len(r["sequence"]) for r in rows])); res = np.log(y) - lp
        print(f"  share of length-residual variance captured: {1-((np.log(p)-np.log(y))**2).sum()/((res-res.mean())**2).sum():.3f}")
# edge audit: which band do the chosen non-local partners fall in?
z = np.load(R/"data/processed/aa_contact_table.npz"); c, o = z["counts"], z["opportunities"]
f = np.divide(c, o, out=np.zeros_like(c), where=o > 0); sc, so = z["sep_counts"], z["sep_opps"]
bands = [(1,1),(2,4),(5,8),(9,16),(17,32),(33,511)]
pd_ = np.array([sc[a:b+1].sum()/max(so[a:b+1].sum(),1) for a,b in bands])
print("band mean contact freq p_d:", np.round(pd_, 5).tolist())
print("f(a,b) range:", round(float(f[o>0].min()),5), round(float(f[o>0].max()),5))
rng = np.random.RandomState(0); far_band = tot = same_as_farthest = 0
for r in [te[i] for i in rng.choice(len(te), 300, replace=False)]:
    s = r["sequence"]; n = len(s); a = np.array([AA.index(x) for x in s])
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij"); sep = abs(ii-jj)
    b = np.full(sep.shape, -1)
    for t,(lo,hi) in enumerate(bands): b[(sep>=lo)&(sep<=hi)] = t
    score = f[a[:,None],a[None,:]]/(np.where(b>=0,pd_[np.clip(b,0,5)],0)+1e-8)
    nl = sep > 2; sw = np.where(nl, score, -1e30) - np.arange(n)[None,:]*1e-12
    k = min(8, n); pick = np.argpartition(sw, -k, axis=1)[:, -k:]
    for i in range(n):
        js = [j for j in pick[i] if nl[i, j]]
        if not js: continue
        fb = max(b[i, j] for j in range(n) if nl[i, j])
        tot += len(js); far_band += sum(b[i, j] == fb for j in js)
        # would ranking by distance band alone give the same partner bands?
        nb = sorted((b[i, j] for j in range(n) if nl[i, j]), reverse=True)[:len(js)]
        same_as_farthest += sorted(b[i, j] for j in js) == sorted(nb)
print(f"chosen partners in the farthest available band: {far_band/tot:.3f}")
print(f"residues whose partner *bands* equal 'just take the farthest': {same_as_farthest}")
