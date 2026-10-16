from dataclasses import dataclass,field
import numpy as np
from scipy.special import logsumexp
from park_revive.policies import Policy
from park_revive.pvalues import hac_pvalue


@dataclass
class Episode:
    comparison_id: str
    start: int
    reference_support: tuple
    candidate: tuple
    move: str
    added: int
    removed: int
    lifecycle: str
    shadow: Policy
    scores: list=field(default_factory=list)
    log_e: float=0.
    components: np.ndarray=field(default_factory=lambda:np.zeros(9))
    total: float=0.

    @property
    def mean(self):return self.total/len(self.scores) if self.scores else 0.


def tolerant_order(items,value,identifier,tolerance):
    ordered=sorted(items,key=lambda x:(-value(x),identifier(x)))
    result=[];i=0
    while i<len(ordered):
        j=i+1
        while j<len(ordered) and value(ordered[i])-value(ordered[j])<=tolerance:j+=1
        result.extend(sorted(ordered[i:j],key=identifier));i=j
    return result


class Selector:
    def __init__(self,name,cfg,ids,margin=1e-8,rank_tolerance=1e-9):
        self.name=name;self.cfg=cfg;self.ids=ids;self.margin=margin;self.rank_tolerance=rank_tolerance
        self.actual=Policy((),np.zeros(len(ids)));self.reference=None
        self.comparisons={};self.counter=0;self.parked=set();self.reset=True

    def refresh(self,day,optimizer):
        s=self.actual.support
        if self.reset or self.reference is None:self.reference=Policy(s,self.actual.previous.copy())
        excluded=sorted(set(range(len(self.ids)))-set(s),key=lambda j:self.ids[j])
        base=optimizer.solve(s,self.actual.previous).value
        gains={j:optimizer.solve(tuple(sorted((*s,j))),self.actual.previous).value-base for j in excluded}
        if min(gains.values(),default=0)<-max(1e-8,self.rank_tolerance*10):
            raise ArithmeticError('Estimated forward value violates support monotonicity')
        ranking=tolerant_order(excluded,lambda j:gains[j],lambda j:self.ids[j],self.rank_tolerance)
        shortlist=ranking[:self.cfg.swap_top]
        proposals=[]
        for j in excluded:proposals.append(('forward',j,-1,tuple(sorted((*s,j)))))
        for i in sorted(s,key=lambda j:self.ids[j]):
            proposals.append(('backward',-1,i,tuple(j for j in s if j!=i)))
            for j in shortlist:proposals.append(('swap',j,i,tuple(sorted((set(s)-{i})|{j}))))
        old={} if self.reset else self.comparisons
        active={};opened=[]
        for move,add,remove,b in proposals:
            key=(move,add,remove)
            if key in old:c=old[key]
            else:
                self.counter+=1;cid=f'{self.name}:{self.counter:06d}:{day}'
                lifecycle=('PARK' if move=='backward' else 'SWAP' if move=='swap' else 'REVIVE' if add in self.parked else 'ENTRY')
                c=Episode(cid,day,s,b,move,add,remove,lifecycle,Policy(b,self.actual.previous.copy()))
                opened.append(c)
            active[key]=c
        withdrawn=[c for key,c in self.comparisons.items() if key not in active]
        self.comparisons=active;self.reset=False
        return shortlist,opened,withdrawn

    def eligible(self,c):
        if c.mean<=self.margin:return False
        if self.name in ('Catoni','Tail'):return c.log_e>=np.log(1/self.cfg.alpha)
        if self.name=='HAC':return hac_pvalue(c.scores)<=self.cfg.alpha
        return True

    def choose(self):
        for move in ('forward','backward','swap'):
            candidates=[c for c in self.comparisons.values() if c.move==move and self.eligible(c)]
            if candidates:
                return tolerant_order(candidates,lambda c:c.mean,
                    lambda c:(self.ids[c.added] if c.added>=0 else '',self.ids[c.removed] if c.removed>=0 else ''),self.rank_tolerance)[0]
        return None

    def apply(self,c):
        before=set(self.actual.support);self.actual.support=c.candidate
        self.parked|=before-set(c.candidate)
        revived=c.added in self.parked
        if c.added>=0:self.parked.discard(c.added)
        self.reset=True
        self.comparisons={};self.reference=None
        return revived
