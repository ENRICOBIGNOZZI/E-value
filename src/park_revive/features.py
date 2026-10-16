"""Public feature functions. Structural labels live exclusively in dgp truth."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class Function:
    signal_id: str
    kind: str
    indices: tuple
    coefficients: tuple
    parent: int = -1


def make_library(seed):
    rng = np.random.default_rng(seed)
    library = []
    for j in range(100):
        lo, hi = (20, 30) if 45 <= j < 85 else (0, 20)
        idx = tuple(int(v) for v in rng.choice(np.arange(lo, hi), 3, replace=False))
        a = rng.normal(size=3); a /= np.abs(a).sum()
        if j < 45:
            kind = ('linear', 'saturating', 'interaction')[j % 3]
        elif j < 85:
            kind = ('linear', 'square', 'interaction')[j % 3]
        else:
            kind = 'proxy'
        library.append(Function(f's{j:03d}', kind, idx, tuple(a), (j-85)*3 % 45 if j >= 85 else -1))
    return tuple(library)


def evaluate(z, library):
    columns = []
    for j, f in enumerate(library):
        idx = f.indices
        if f.kind == 'linear':
            v = z[:,idx]@f.coefficients
        elif f.kind == 'saturating':
            v = np.tanh(2*(z[:,idx]@f.coefficients))
        elif f.kind == 'interaction':
            v = z[:,idx[0]]*z[:,idx[1]]
        elif f.kind == 'square':
            # Center at the contemporaneous cross-section; |v| <= 1.
            v = z[:,idx[0]]**2
            v = v-v.mean()
        else:
            v = .9*columns[f.parent] + .1*columns[45+(j-85) % 40]
        columns.append(v)
    return np.column_stack(columns)


def serialize_library(library):
    return [asdict(f) for f in library]
