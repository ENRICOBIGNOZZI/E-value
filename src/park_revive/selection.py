"""Learner-only search. Receives public estimates, IDs and realized score series."""
from dataclasses import dataclass, field
import numpy as np
from .comparisons import Comparison
from .eprocess import Evidence
from .policies import Policy
from .pvalues import hac_pvalue


@dataclass
class Selector:
    name: str
    cfg: object
    ids: tuple
    nu2: float
    actual: Policy
    reference: Policy = None
    comparisons: dict = field(default_factory=dict)
    episode: int = 0
    parked: set = field(default_factory=set)

    def refresh(self, day, optimizer, reset=False):
        s = self.actual.support
        if reset or self.reference is None:
            self.reference = Policy(s,self.actual.previous.copy())
        excluded = sorted(set(range(len(self.ids)))-set(s),key=lambda j:self.ids[j])
        v0 = optimizer.solve(s,self.actual.previous).value
        ranking = [(optimizer.solve(tuple(sorted((*s,j))),self.actual.previous).value-v0,j) for j in excluded]
        ranking.sort(key=lambda z:(-z[0],self.ids[z[1]]))
        shortlist = [j for _,j in ranking[:self.cfg.swap_top]]
        proposals = []
        for j in excluded:
            proposals.append(('forward',j,-1,tuple(sorted((*s,j)))))
        for i in sorted(s,key=lambda j:self.ids[j]):
            proposals.append(('backward',-1,i,tuple(j for j in s if j != i)))
            for j in shortlist:
                proposals.append(('swap',j,i,tuple(sorted((set(s)-{i})|{j}))))
        old = {} if reset else self.comparisons
        current = {}
        closed = []
        for move,add,remove,b in proposals:
            key = (move,add,remove)
            if key in old:
                comp = old[key]
            else:
                self.episode += 1
                cid = f'{self.name}:{self.episode:06d}:{day}'
                comp = Comparison(cid,day,s,b,move,add,remove,Policy(b,self.actual.previous.copy()),Evidence(self.nu2,self.cfg.delta0))
            comp.evidence.start_block()
            current[key] = comp
        for key,comp in self.comparisons.items():
            if reset or key not in current:
                closed.append(comp.comparison_id)
        self.comparisons = current
        return shortlist,closed

    def choose(self):
        for kind in ('forward','backward','swap'):
            eligible = []
            for c in self.comparisons.values():
                if c.move != kind or c.evidence.mean <= 0:
                    continue
                if self.name == 'E-process':
                    passed = c.evidence.log_e >= np.log(1/self.cfg.alpha)
                elif self.name == 'Repeated-HAC-p':
                    passed = hac_pvalue(c.scores) <= self.cfg.alpha
                else:
                    passed = True
                if passed:
                    eligible.append(c)
            if eligible:
                return min(eligible,key=lambda c:(-c.evidence.mean,
                    self.ids[c.added] if c.added >= 0 else '',self.ids[c.removed] if c.removed >= 0 else ''))
        return None

    def apply(self, chosen):
        before = set(self.actual.support)
        self.actual.support = chosen.candidate
        self.parked |= before-set(chosen.candidate)
        revived = chosen.added in self.parked
        if chosen.added >= 0:
            self.parked.discard(chosen.added)
        return revived
