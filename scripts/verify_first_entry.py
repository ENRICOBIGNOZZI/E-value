"""Independent batch replay of every annual evidence value from saved score inputs.

Uses no oracle columns, checkpoint objects or TailMixture state/update methods.
The arithmetic is vectorized across each stored annual block.
"""
import argparse
import json
import hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from threadpoolctl import threadpool_limits
from park_revive.config import Config
from park_revive.eprocess import phi,public_envelope
from park_revive_extensions.certificates import PublicRisk,uniform_forward_caps


def verify(root):
    root=Path(root);protocol=json.loads((root/'protocol_frozen.json').read_text())
    cfg=Config(**protocol['config']);risk=PublicRisk(**protocol['risk'])
    uniform2,uniform4=uniform_forward_caps(cfg,risk)
    constant=public_envelope(cfg)['nu2'];checked=0;largest_error=0.
    for seed in protocol['seed_pool']:
        path=root/f'seed_{seed}'
        if not (path/'summary.csv').exists():continue
        total=np.zeros(100);n=0
        catoni=np.zeros(100);geometry=np.zeros(100)
        tail_uniform=np.zeros((9,100));tail_geometry=np.zeros((9,100))
        first_cross={arm:np.full(100,-1,dtype=int) for arm in protocol['arms']}
        for year,block in enumerate(sorted(path.glob('block_*')),start=1):
            frame=pd.read_parquet(block/'score_ledger.parquet',columns=['day','score','geometric_second','geometric_fourth'])
            np.testing.assert_array_equal(frame.day,np.arange(year*cfg.block,(year+1)*cfg.block))
            y=np.stack(frame.score);second=np.stack(frame.geometric_second);fourth=np.stack(frame.geometric_fourth)
            effect=np.full(100,cfg.delta0) if not n else np.maximum(total/n,0.)
            bet=np.minimum(effect/(2*constant),1/(2*np.sqrt(constant)))
            catoni+=np.sum(phi(bet*y)-bet**2*constant/2,axis=0)
            gb=np.zeros_like(second);positive=second>0
            scaled=np.broadcast_to(effect,second.shape)
            gb[positive]=np.minimum(scaled[positive]/(2*second[positive]),1/(2*np.sqrt(second[positive])))
            geometry+=np.sum(phi(gb*y)-gb*gb*second/2,axis=0)
            for components,v2,v4 in ((tail_uniform,np.full_like(second,uniform2),np.full_like(fourth,uniform4)),
                                     (tail_geometry,second,fourth)):
                for index,(scale,fraction) in enumerate((s,f) for s in protocol['mixture_scales'] for f in protocol['fractions']):
                    level=np.where(v4>0,scale*v4**.25,1.)
                    bias=np.minimum(v2/(4*level),27*v4/(256*level**3))
                    fraction_bet=np.where(v4>0,fraction/(level+bias),0.)
                    factor_log=np.log1p(fraction_bet*(np.maximum(y,-level)-bias))
                    components[index]+=np.sum(factor_log,axis=0)
            total+=y.sum(axis=0);n+=len(y)
            replay={'Catoni-baseline':catoni,'Catoni-geometry':geometry,
                    'Tail-uniform':logsumexp(tail_uniform,axis=0)-np.log(9),
                    'Tail-geometry':logsumexp(tail_geometry,axis=0)-np.log(9)}
            events=pd.read_csv(block/'annual_events.csv')
            for arm,values in replay.items():
                recorded=events[events.arm.eq(arm)].sort_values('signal')
                error=float(np.max(np.abs(recorded.log_e.to_numpy()-values)))
                largest_error=max(largest_error,error)
                np.testing.assert_allclose(recorded.log_e,values,rtol=1e-10,atol=5e-10)
                np.testing.assert_allclose(recorded.mean_score,total/n,rtol=1e-10,atol=1e-15)
                eligible=(values>=np.log(1/cfg.alpha))&(total/n>0)
                np.testing.assert_array_equal(recorded.eligible,eligible)
                new=eligible&(first_cross[arm]<0)
                first_cross[arm][new]=(year+1)*cfg.block
                np.testing.assert_array_equal(recorded.first_cross_day,first_cross[arm])
                checked+=len(values)
        reported_summary=pd.read_csv(path/'summary.csv').set_index('arm')
        for arm,first in first_cross.items():
            observed=first[first>=0]
            assert reported_summary.loc[arm,'crossed_signals']==len(observed)
            assert reported_summary.loc[arm,'first_entry_day']==(int(observed.min()) if len(observed) else -1)
        print(f'seed={seed}: annual evidence replayed from score/certificate files only',flush=True)
    result=dict(annual_evidence_values=checked,maximum_absolute_error=largest_error,
                oracle_columns_used=False,checkpoint_objects_used=False,
                first_crossings_and_censoring_verified=True,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                update_implementation='independent vectorized block arithmetic')
    (root/'evidence_replay_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='outputs/park_revive_tail_v1/first_entry')
    args=p.parse_args()
    with threadpool_limits(limits=1):verify(args.output)
