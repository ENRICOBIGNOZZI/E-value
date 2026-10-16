#!/usr/bin/env python3
"""Independent stake/crossing replay for the fresh constant-power comparison."""
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from audit_lambda_power import lookup

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = ROOT/'outputs/lambda_constant_v1'
    destination = ROOT/'reports/lambda_constant_results'
    status = json.loads((output/'status.json').read_text())
    frozen = json.loads((destination/'protocol_frozen.json').read_text())
    cfg = status['config']; block = cfg['block']; reps = cfg['replications']
    assert status['complete'] and cfg == frozen['config']
    for path, expected in frozen['source_files'].items():
        assert digest(ROOT/path) == expected == status['source_files'][path], path
    for path, expected in frozen['model_files'].items():
        assert digest(output/path) == expected, path
    manifest = json.loads((output/'model_manifest.json').read_text())
    models = {}; constants = {}
    for name in cfg['models']:
        with np.load(output/f'dp_model_{name}.npz') as z:
            models[name] = {key: z[key] for key in z.files}
        with np.load(output/f'constant_model_{name}.npz') as z:
            constants[name] = {key: z[key] for key in z.files}
        c = constants[name]
        np.testing.assert_array_equal(c['best_indices'], np.argmax(c['power'], axis=1))
        np.testing.assert_array_equal(c['best_bets'], c['actions'][c['best_indices']])
    summary = pd.read_csv(output/'summary.csv')
    checks = 0; max_error = 0.; paired = []; calibration = []
    for mean in cfg['score_means']:
        with np.load(output/f'mean_{mean:g}.npz') as z:
            arrays = {key: z[key] for key in z.files}
        names = list(arrays['methods']); logs = arrays['log_capital']; stakes = arrays['stakes']
        first = arrays['first_crossings']; prefix = cfg['audit_path_prefix']
        assert np.all((stakes >= 0) & (stakes <= cfg['cap_multiplier']/np.sqrt(cfg['public_second'])+1e-15))
        hits = logs[1:] >= np.log(1/cfg['alpha'])
        inferred = np.where(hits.any(axis=0), (np.argmax(hits, axis=0)+1)*block, -1)
        np.testing.assert_array_equal(inferred, first); checks += first.size
        total_y = np.zeros(prefix); capital = np.zeros((len(names), prefix))
        for k in range(len(stakes)):
            earlier = np.any(hits[:k], axis=0) if k else np.zeros((len(names), reps), bool)
            for j, name in enumerate(names):
                expected = None
                if name == 'Fixed certificate':
                    expected = np.full(reps, cfg['design_mean']/(2*cfg['public_second']))
                elif name == 'Fixed log growth':
                    expected = np.full(reps, manifest['log_growth_bet'])
                elif name == 'One-block power':
                    expected = lookup(models['primary'], 1, logs[k, j])
                elif name.startswith('DP '):
                    model_name = name.split()[1]; horizon = int(name.split('H=')[1])//block
                    expected = lookup(models[model_name], horizon-k, logs[k, j]) if k < horizon else np.zeros(reps)
                elif name.startswith('Constant '):
                    model_name = name.split()[1]; horizon = int(name.split('H=')[1])//block
                    index = cfg['horizon_blocks'].index(horizon)
                    lam = float(constants[model_name]['best_bets'][index])
                    expected = np.full(reps, lam if k < horizon else 0.)
                if expected is not None:
                    expected = np.where(earlier[j], 0., expected)
                    np.testing.assert_array_equal(expected, stakes[k, j]); checks += reps
                else:
                    assert name == 'Past-mean certificate'
                    signal = np.full(prefix, cfg['initial_gain']) if not k else np.maximum(0., total_y/(k*block))
                    expected = np.minimum(signal/(2*cfg['public_second']), cfg['cap_multiplier']/np.sqrt(cfg['public_second']))
                    np.testing.assert_allclose(np.where(earlier[j, :prefix], 0., expected), stakes[k, j, :prefix], atol=1e-14)
                    checks += prefix
                lam = stakes[k, j, :prefix]; product = np.ones(prefix)
                for y in arrays['audit_scores'][k*block:(k+1)*block]:
                    x = lam*y; envelope = 1+abs(x)+x*x/2
                    product *= np.where(x >= 0, envelope, 1/envelope)*np.exp(-lam*lam*cfg['public_second']/2)
                capital[j] += np.log(product)
                max_error = max(max_error, float(np.max(abs(capital[j]-logs[k+1, j, :prefix]))))
                np.testing.assert_allclose(capital[j], logs[k+1, j, :prefix], atol=2e-11, rtol=1e-10)
                checks += prefix
            total_y += arrays['audit_scores'][k*block:(k+1)*block].sum(axis=0)
        for h in cfg['horizon_blocks']:
            observations = h*block
            for j, name in enumerate(names):
                row = summary[summary['mean'].eq(mean) & summary.method.eq(name) & summary.observations.eq(observations)]
                if row.empty:
                    continue
                success = (first[j] > 0) & (first[j] <= observations)
                assert int(row.iloc[0].crossings) == int(success.sum()); checks += 1
            for version in cfg['models']:
                target_index = cfg['horizon_blocks'].index(h)
                indices = {kind: names.index(f'{kind} {version} H={observations}') for kind in ('DP', 'Constant')}
                successes = {kind: (first[j] > 0) & (first[j] <= observations) for kind, j in indices.items()}
                difference = successes['DP'].astype(float)-successes['Constant'].astype(float)
                delta = float(difference.mean()); se = float(difference.std(ddof=1)/np.sqrt(reps))
                paired.append(dict(mean=mean, observations=observations, model=version,
                    reference='Deadline-optimal constant', paired_difference=delta, mc_se=se,
                    ci_low=delta-1.959963984540054*se, ci_high=delta+1.959963984540054*se))
                if mean == cfg['design_mean']:
                    for kind, success in successes.items():
                        predicted = (manifest['models'][version]['dp_initial_power'][target_index]
                                     if kind == 'DP' else manifest['models'][version]['initial_power'][target_index])
                        observed = float(success.mean()); se = np.sqrt(observed*(1-observed)/reps)
                        calibration.append(dict(model=version, rule=kind, observations=observations,
                            predicted=predicted, observed=observed, discrepancy=observed-predicted, mc_se=se,
                            within_declared_numerical_plus_MC_tolerance=abs(observed-predicted) <= cfg['numerical_power_tolerance']+5*se))
        print('audited companion mean', mean, flush=True)
    pd.DataFrame(paired).to_csv(destination/'paired_comparisons.csv', index=False)
    pd.DataFrame(calibration).to_csv(destination/'predicted_observed_power.csv', index=False)
    for name in ('summary.csv', 'status.json', 'model_manifest.json',
                 'constant_model_primary.npz', 'constant_model_refinement.npz',
                 'dp_model_primary.npz', 'dp_model_refinement.npz'):
        shutil.copyfile(output/name, destination/name)
    verification = dict(study_source_matches_freeze=True, source_freeze_commit='c73e713',
        scalar_checks=checks, max_prefix_log_capital_error=max_error,
        every_fixed_and_DP_stake_reconstructed=True, every_first_crossing_replayed=True,
        multiplicative_score_replay_paths_per_law=prefix,
        all_model_calibrations_pass=all(x['within_declared_numerical_plus_MC_tolerance'] for x in calibration),
        inputs={p.name: digest(p) for p in output.iterdir() if p.is_file()},
        audit_sources={str(p.relative_to(ROOT)): digest(p) for p in (Path(__file__), ROOT/'scripts/audit_lambda_power.py')},
        scope='Fresh companion only. Every fixed/DP stake and crossing checked; score-factor and past-mean reconstruction cover sixteen paths/law. Nominal individual level is common; actual null rates differ. No pooling, continuous-control optimality or financial performance claim.')
    (destination/'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
    print(json.dumps({k: v for k,v in verification.items() if k not in ('inputs','audit_sources')}, indent=2), flush=True)
    if not verification['all_model_calibrations_pass']:
        raise ArithmeticError('Unresolved working-model power discrepancy')


if __name__ == '__main__':
    main()
