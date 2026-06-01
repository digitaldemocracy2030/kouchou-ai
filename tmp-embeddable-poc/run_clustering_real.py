import os, pickle, tempfile, time
import numpy as np
import polars as pl
from analysis_core.steps.hierarchical_clustering import hierarchical_clustering

base = tempfile.mkdtemp(prefix="clu_")
ds = "job1"
d = os.path.join(base, ds)
os.makedirs(d, exist_ok=True)

# synthetic: 3 latent groups, 60 args, 256-dim embeddings
rng = np.random.RandomState(0)
n_per, dim = 20, 256
centers = rng.rand(3, dim)
rows, embs = [], []
k = 0
for g in range(3):
    for _ in range(n_per):
        aid = f"A{k}"
        rows.append({"arg-id": aid, "argument": f"opinion {k} about topic {g}"})
        embs.append({"arg-id": aid, "embedding": (centers[g] + rng.rand(dim)*0.3).tolist()})
        k += 1

pl.DataFrame(rows).write_csv(os.path.join(d, "args.csv"))
with open(os.path.join(d, "embeddings.pkl"), "wb") as f:
    pickle.dump(embs, f)

config = {
    "output_dir": ds,
    "_output_base_dir": base,
    "hierarchical_clustering": {"cluster_nums": [3, 9]},
}

t0 = time.time()
hierarchical_clustering(config)
dt = time.time() - t0

out = pl.read_csv(os.path.join(d, "hierarchical_clusters.csv"))
print(f"clustering completed in {dt:.1f}s")
print("columns:", out.columns)
print("rows:", out.height)
print("level-1 clusters:", sorted(out['cluster-level-1-id'].unique().to_list()))
print("level-2 clusters:", sorted(out['cluster-level-2-id'].unique().to_list()))
print("=== REAL CLUSTERING STEP PASSED UNDER EMBEDDABLE ===")
