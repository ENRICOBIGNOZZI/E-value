#!/usr/bin/env python3
"""Independently replay a fixed path prefix and report the declared scalar study."""
import hashlib
import argparse
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def replay(cfg,law,stream,archive,count=8):
    rng=np.random.default_rng(stream);n0=cfg['training'];reps=cfg['replications']
    training=rng.normal(0,cfg['sigma'],(n0,reps))[:,:count]
    sums=training.sum(axis=0);squares=(training**2).sum(axis=0)
    gamma=cfg['gamma'];sigma=cfg['sigma'];limit=cfg['leverage'];lam=gamma/2
    bound=(limit*np.sqrt(cfg['public_second'])+gamma*limit**2*np.sqrt(cfg['public_fourth'])/2)**2
    logs=np.zeros((4,count));products=np.ones_like(logs);total_y=np.zeros(count);squared_targets=np.zeros(count)
    lr=np.zeros(count);benefit=np.zeros(count);first=np.full((4,len(cfg['levels']),count),-1,dtype=int)
    annual=first.copy();threshold=np.log(1/np.array(cfg['levels']))
    indices={int(t):j for j,t in enumerate(archive['times'])};checks=0;max_error=0.
    def compare(observed,expected):
        nonlocal checks,max_error
        np.testing.assert_allclose(observed,expected,atol=2e-8,rtol=1e-9)
        max_error=max(max_error,float(np.max(np.abs(observed-expected))));checks+=np.size(observed)
    for t in range(1,cfg['observations']+1):
        past=n0+t-1
        w=np.maximum(-limit,np.minimum(limit,(sums/past)/(gamma*(squares/past+cfg['ridge']))))
        if (t-1)%cfg['review_block']==0:
            signal=np.full(count,cfg['initial_gain']) if t==1 else np.maximum(0.,total_y/(t-1))
            bet=np.minimum(signal/(2*bound),1/(2*np.sqrt(bound)))
        feedback=gamma*sigma*w/2
        qm=feedback*sigma/(1+feedback**2);qs=sigma/(1+feedback**2)
        z=rng.normal(size=reps)[:count]
        if law=='gaussian_alternative':mean=np.zeros(count);sd=sigma
        else:mean=qm;sd=qs
        returns=mean+sd*z;risky=w*returns
        y=-(risky-gamma*risky**2/2)
        local=(np.sqrt(cfg['public_second'])*np.abs(w)+gamma*w*w*np.sqrt(cfg['public_fourth'])/2)**2
        for k,(stake,cap) in enumerate(((lam,local),(lam,bound),(bet,bound)),start=1):
            x=stake*y;envelope=1+np.abs(x)+x*x/2
            products[k]*=np.where(x>=0,envelope,1/envelope)*np.exp(-stake*stake*cap/2)
        products[0]*=1+lam*y
        current=logs+np.log(products)
        crossing=current[:,None,:]>=threshold[None,:,None]
        first[(first<0)&crossing]=t
        if t%cfg['review_block']==0:annual[(annual<0)&crossing]=t
        lr+=(-np.log(sigma)-(returns/sigma)**2/2)-(-np.log(qs)-((returns-qm)/qs)**2/2)
        squared_targets+=w*w;total_y+=y
        benefit+=-w*mean+gamma*w*w*(mean*mean+sd*sd)/2
        if t in indices:
            j=indices[t]
            for key,value in [('log_capital',current),('log_likelihood_ratio',lr),('sum_w2',squared_targets),
                              ('conditional_benefit',benefit),('realized_benefit',total_y),('past_mean_bet',bet)]:
                expected=archive[key][j,...,:count];compare(value,expected)
            logs=current;products.fill(1.)
        sums+=returns;squares+=returns*returns
    np.testing.assert_array_equal(first,archive['first_crossings'][...,:count])
    np.testing.assert_array_equal(annual,archive['annual_first_crossings'][...,:count])
    return dict(replayed_path_prefix=count,scalar_checks=checks,max_absolute_error=max_error,
                compounding='direct multiplicative factors, reset at saved checkpoints; not the study log-increment code')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-only',action='store_true',help='Render the retained summary; does not rerun scientific paths or replay')
    args=parser.parse_args()
    output=ROOT/'outputs/vanishing_gain_v1';destination=ROOT/'reports/vanishing_gain_results'
    destination.mkdir(exist_ok=True)
    cfg=json.loads((output/'config_frozen.json').read_text());status=json.loads((output/'status.json').read_text())
    freeze=json.loads((ROOT/'reports/vanishing_gain_frozen.json').read_text())
    script_hash=hashlib.sha256((ROOT/'scripts/vanishing_gain_study.py').read_bytes()).hexdigest()
    assert status['script_sha256']==script_hash==freeze['files']['scripts/vanishing_gain_study.py']
    assert cfg==status['config']==json.loads((ROOT/'configs/vanishing_gain.json').read_text())
    if args.plot_only:
        plot_results(pd.read_csv(destination/'trajectory_summary.csv'),cfg,destination)
        return
    streams=np.random.SeedSequence(cfg['seed']).spawn(len(cfg['laws']));audits={}
    for law,stream in zip(cfg['laws'],streams):
        # NpzFile does not cache decompressed arrays on repeated indexing.
        with np.load(output/f'{law}.npz') as archive:arrays={key:archive[key] for key in archive.files}
        audits[law]=replay(cfg,law,stream,arrays)
        print(law,audits[law],flush=True)
    table=pd.read_csv(output/'summary.csv');endpoint=table[table.observations.eq(cfg['observations'])]
    table.to_csv(destination/'trajectory_summary.csv',index=False);endpoint.to_csv(destination/'endpoint_summary.csv',index=False)
    for name in ('config_frozen.json','status.json'):shutil.copyfile(output/name,destination/name)
    verification=dict(study_source_matches_frozen=True,source_commit='57752eb',replay=audits,
        replay_function_sha256=hashlib.sha256(inspect.getsource(replay).encode()).hexdigest(),
        input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()},
        scope='Fixed eight-path prefix independently replayed under each law; 4096 paths/law summarized. Not a replay of every path, an asymptotic proof or extra financial market replication.')
    (destination/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    plot_results(table,cfg,destination)


def plot_results(table,cfg,destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    alt=table[table.law.eq('gaussian_alternative')&table.alpha.eq(.05)]
    fig,axes=plt.subplots(1,2,figsize=(10.5,3.8))
    colors={name:f'C{j}' for j,name in enumerate(alt.method.unique())}
    for method,group in alt.groupby('method',sort=False):
        if method!='Catoni uniform fixed':
            x=np.log((cfg['training']+group.observations)/cfg['training'])
            line=axes[0].plot(x,group.mean_log_capital,label=method,color=colors[method])[0]
            axes[0].fill_between(x,group.mean_log_capital-1.96*group.mc_se_log_capital,
                group.mean_log_capital+1.96*group.mc_se_log_capital,color=line.get_color(),alpha=.1)
        axes[1].step(group.observations,group.crossing_fraction,label=method,color=colors[method],where='post')
        axes[1].fill_between(group.observations,group.wilson_low,group.wilson_high,
                            color=colors[method],alpha=.08,step='post')
    last=alt[alt.method.eq('Linear cash-PARK')]
    x=np.log((cfg['training']+last.observations)/cfg['training'])
    axes[0].plot(x,x/8,'--',color='black',label='Slope 1/8 guide')
    axes[0].set(xlabel='log((training + observations) / training)',ylabel='Mean log capital')
    axes[1].set(xlabel='Evaluated observations',ylabel='Anytime crossing fraction (alpha = .05)',xscale='log')
    for ax in axes:ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(destination/'vanishing_gain.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
