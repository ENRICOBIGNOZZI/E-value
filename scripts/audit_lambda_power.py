#!/usr/bin/env python3
"""Replay lambda-study artifacts and summarize paired finite-horizon rejection rates."""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lookup(model,remaining,capital):
    grid=model['states'];midpoints=(grid[:-1]+grid[1:])/2
    index=np.searchsorted(midpoints,capital,side='left')
    index=np.where(capital<grid[-1],np.minimum(index,len(grid)-2),index)
    result=model['actions'][model['policy'][remaining,index]]
    return np.where(capital<grid[0],0.,result)


def main():
    output=ROOT/'outputs/lambda_power_v2';destination=ROOT/'reports/lambda_power_v2_results'
    destination.mkdir(exist_ok=True)
    status=json.loads((output/'status.json').read_text());cfg=status['config'];block=cfg['block'];reps=cfg['replications']
    frozen=json.loads((destination/'protocol_frozen.json').read_text())
    assert status['source_sha256']==digest(ROOT/'scripts/lambda_power_study.py')==frozen['source_files']['scripts/lambda_power_study.py']
    assert cfg==json.loads((ROOT/'configs/lambda_power.json').read_text())
    manifest=json.loads((output/'model_manifest.json').read_text());models={}
    for name in cfg['models']:
        path=output/f'model_{name}.npz';assert digest(path)==frozen['model_files'][path.name]
        with np.load(path) as z:models[name]={key:z[key] for key in z.files}
    summary=pd.read_csv(output/'summary.csv');checks=0;max_error=0.;paired=[];calibration=[]
    for mean in cfg['score_means']:
        with np.load(output/f'mean_{mean:g}.npz') as z:arrays={key:z[key] for key in z.files}
        logs=arrays['log_capital'];stakes=arrays['stakes'];names=list(arrays['methods']);first=arrays['first_crossings'];prefix=cfg['audit_path_prefix']
        assert np.all((stakes>=0)&(stakes<=cfg['cap_multiplier']/np.sqrt(cfg['public_second'])+1e-15))
        boundary=np.log(1/cfg['alpha']);hits=logs[1:]>=boundary
        inferred=np.where(hits.any(axis=0),(np.argmax(hits,axis=0)+1)*block,-1)
        np.testing.assert_array_equal(inferred,first);checks+=first.size
        total_y=np.zeros(prefix);capital=np.zeros((len(names),prefix))
        for k in range(len(stakes)):
            earlier=np.any(hits[:k],axis=0) if k else np.zeros((len(names),reps),bool)
            for j,name in enumerate(names):
                expected=None
                if name=='Fixed certificate':expected=np.full(reps,cfg['design_mean']/(2*cfg['public_second']))
                if name=='Fixed log growth':expected=np.full(reps,manifest['log_growth_bet'])
                if name=='One-block power':expected=lookup(models['primary'],1,logs[k,j])
                if name.startswith('DP '):
                    model_name=name.split()[1];horizon=int(name.split('H=')[1])//block
                    expected=lookup(models[model_name],horizon-k,logs[k,j]) if k<horizon else np.zeros(reps)
                if expected is not None:
                    expected=np.where(earlier[j],0.,expected)
                    np.testing.assert_array_equal(expected,stakes[k,j]);checks+=reps
                else:
                    signal=np.full(prefix,cfg['initial_gain']) if not k else np.maximum(0.,total_y/(k*block))
                    expected=np.minimum(signal/(2*cfg['public_second']),cfg['cap_multiplier']/np.sqrt(cfg['public_second']))
                    np.testing.assert_allclose(np.where(earlier[j,:prefix],0.,expected),stakes[k,j,:prefix],atol=1e-14);checks+=prefix
                lam=stakes[k,j,:prefix]
                product=np.ones(prefix)
                for y in arrays['audit_scores'][k*block:(k+1)*block]:
                    x=lam*y;base=1+np.abs(x)+x*x/2
                    product*=np.where(x>=0,base,1/base)*np.exp(-lam*lam*cfg['public_second']/2)
                capital[j]+=np.log(product)
                error=float(np.max(np.abs(capital[j]-logs[k+1,j,:prefix])));max_error=max(max_error,error)
                np.testing.assert_allclose(capital[j],logs[k+1,j,:prefix],atol=2e-11,rtol=1e-10);checks+=prefix
            total_y+=arrays['audit_scores'][k*block:(k+1)*block].sum(axis=0)
        for h in cfg['horizon_blocks']:
            observations=h*block
            for j,name in enumerate(names):
                row=summary[(summary['mean']==mean)&summary.method.eq(name)&summary.observations.eq(observations)]
                if row.empty:continue
                success=(first[j]>0)&(first[j]<=observations)
                assert int(row.iloc[0].crossings)==int(success.sum());checks+=1
            for version in ['primary','refinement']:
                j=names.index(f'DP {version} H={observations}');success=(first[j]>0)&(first[j]<=observations)
                if mean==cfg['design_mean']:
                    predicted=manifest['initial_power'][version][str(observations)]
                    observed=float(success.mean());se=np.sqrt(observed*(1-observed)/reps)
                    calibration.append(dict(model=version,observations=observations,predicted=predicted,observed=observed,
                        discrepancy=observed-predicted,mc_se=se,within_declared_numerical_plus_MC_tolerance=abs(observed-predicted)<=cfg['numerical_power_tolerance']+5*se))
                for reference in ['Past-mean certificate','Fixed certificate','Fixed log growth','One-block power']:
                    r=names.index(reference);other=(first[r]>0)&(first[r]<=observations)
                    differences=success.astype(float)-other.astype(float);delta=float(differences.mean());se=float(differences.std(ddof=1)/np.sqrt(reps))
                    paired.append(dict(mean=mean,observations=observations,model=version,reference=reference,
                        paired_difference=delta,mc_se=se,ci_low=delta-1.959963984540054*se,ci_high=delta+1.959963984540054*se))
        print('audited mean',mean,flush=True)
    pd.DataFrame(paired).to_csv(destination/'paired_comparisons.csv',index=False)
    pd.DataFrame(calibration).to_csv(destination/'predicted_observed_power.csv',index=False)
    for name in ['summary.csv','status.json','model_manifest.json','model_primary.npz']:shutil.copyfile(output/name,destination/name)
    result=dict(study_source_matches_freeze=True,scalar_checks=checks,max_prefix_log_capital_error=max_error,
        all_stake_bounds_checked=True,all_DP_and_fixed_stakes_reconstructed=True,all_first_crossings_replayed=True,
        multiplicative_score_replay_paths_per_law=prefix,all_model_calibrations_pass=all(x['within_declared_numerical_plus_MC_tolerance'] for x in calibration),
        inputs={p.name:digest(p) for p in output.iterdir() if p.is_file()},
        scope='Every DP/fixed stake and first crossing checked. Score multiplication and past-mean stake checks cover the declared sixteen-path prefix per law, not every score path. Each rule has individual nominal 5% validity; actual null crossing rates differ. No financial performance claim.')
    (destination/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
