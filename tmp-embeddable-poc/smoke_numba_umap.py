import sys, time
print("python:", sys.version)
print("executable:", sys.executable)

t0 = time.time()
import numpy as np
import numba
import llvmlite
import sklearn
import scipy
import umap
print(f"imports ok ({time.time()-t0:.1f}s): numba={numba.__version__} llvmlite={llvmlite.__version__} sklearn={sklearn.__version__} scipy={scipy.__version__} umap={umap.__version__}")

# numba JIT must actually compile (this is the real embeddable risk)
@numba.njit
def _add(a, b):
    return a + b
assert _add(2, 3) == 5
print("numba njit compile+run: OK")

# UMAP fit (exercises numba-compiled internals end to end)
rng = np.random.RandomState(0)
X = rng.rand(200, 50)
t1 = time.time()
emb = umap.UMAP(n_neighbors=15, n_components=2, random_state=0).fit_transform(X)
print(f"UMAP fit_transform: OK shape={emb.shape} ({time.time()-t1:.1f}s)")

# polars (uses its own native runtime)
import polars as pl
df = pl.DataFrame({"a": [1, 2, 3]})
print("polars:", df["a"].sum())

print("=== ALL CRITICAL IMPORTS/FITS PASSED ===")
