#!/usr/bin/env python3
"""Fresh comparison of deadline-adaptive bets and model-selected constant bets."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd
from scipy.fft import irfft, next_fast_len, rfft

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('frozen_lambda_base', ROOT/'scripts/lambda_power_study.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    return {name: digest(ROOT/name) for name in
            ('scripts/lambda_constant_study.py', 'scripts/lambda_power_study.py',
             'configs/lambda_constant.json', 'configs/lambda_power.json',
             'reports/lambda_constant_protocol.md')}


def fixed_model(cfg, model):
    """All constant actions' hitting probabilities on the declared state grid."""
    states = model['states']; actions = model['actions']; step = float(model['step'])
    kernels, audit = base.block_kernels(cfg, actions, step)
    radius = (kernels.shape[1]-1)//2
    length = len(states)
    fft_length = next_fast_len(length+4*radius)
    transform = rfft(kernels[:, ::-1], fft_length, axis=1)
    values = np.zeros((len(actions), length))
    values[:, -1] = 1.
    powers = []; selected = []; maxima = []
    left = np.zeros((len(actions), radius)); right = np.ones((len(actions), radius))
    for remaining in range(1, max(cfg['horizon_blocks'])+1):
        padded = np.concatenate((left, values, right), axis=1)
        values = irfft(transform*rfft(padded, fft_length, axis=1), fft_length,
                       axis=1)[:, 2*radius:2*radius+length]
        values = np.clip(values, 0., 1.); values[:, -1] = 1.
        if remaining in cfg['horizon_blocks']:
            initial = np.array([np.interp(0., states, row) for row in values])
            best = int(np.argmax(initial))
            dp_initial = float(np.interp(0., states, model['values'][remaining]))
            if float(initial[best]) > dp_initial+1e-10:
                raise ArithmeticError('Fixed policy exceeds its full Bellman class')
            powers.append(initial); selected.append(best); maxima.append(initial[best])
    return dict(actions=actions, horizons=np.array(cfg['horizon_blocks'])*cfg['block'],
                power=np.array(powers), best_indices=np.array(selected),
                best_bets=actions[np.array(selected)], initial_power=np.array(maxima)), audit


def simulate(cfg, mean, stream, models, fixed):
    # The original arms use precisely their frozen implementation. Regenerating
    # the same independent score stream shares every score with the new arms.
    original, rows = base.simulate(cfg, mean, stream, models)
    targets = [(name, h, float(model['best_bets'][j])) for name, model in fixed.items()
               for j, h in enumerate(cfg['horizon_blocks'])]
    names = [f'Constant {name} H={h*cfg["block"]}' for name, h, _ in targets]
    reps = cfg['replications']; block = cfg['block']; maximum = max(cfg['horizon_blocks'])
    capital = np.zeros((len(names), reps)); first = np.full_like(capital, -1, dtype=int)
    logs = [capital.copy()]; stakes = []; prefix = []; rng = np.random.default_rng(stream)
    boundary = np.log(1/cfg['alpha']); bound = cfg['public_second']
    for k in range(maximum):
        bets = np.array([np.full(reps, lam if k < h else 0.) for _, h, lam in targets])
        bets = np.where(first > 0, 0., bets)
        y = mean+cfg['score_sd']*rng.normal(size=(block, reps))
        prefix.append(y[:, :cfg['audit_path_prefix']].copy()); stakes.append(bets.copy())
        for j, lam in enumerate(bets):
            capital[j] += base.phi(y*lam[None, :]).sum(axis=0)-block*lam*lam*bound/2
            hit = (first[j] < 0) & (capital[j] >= boundary)
            first[j, hit] = (k+1)*block
        logs.append(capital.copy())
        if k+1 in cfg['horizon_blocks']:
            for j, name in enumerate(names):
                if targets[j][1] != k+1:
                    continue
                success = first[j] > 0; p = float(success.mean()); z = 1.959963984540054
                center = (p+z*z/(2*reps))/(1+z*z/reps)
                radius = z*np.sqrt(p*(1-p)/reps+z*z/(4*reps**2))/(1+z*z/reps)
                rows.append(dict(mean=mean, method=name, observations=(k+1)*block,
                    replications=reps, crossings=int(success.sum()), power=p,
                    wilson_low=max(0., center-radius), wilson_high=min(1., center+radius),
                    mean_log_capital=float(capital[j].mean())))
    np.testing.assert_array_equal(np.concatenate(prefix), original['audit_scores'])
    original['methods'] = np.concatenate((original['methods'], np.array(names)))
    original['log_capital'] = np.concatenate((original['log_capital'], np.stack(logs)), axis=1)
    original['stakes'] = np.concatenate((original['stakes'], np.stack(stakes)), axis=1)
    original['first_crossings'] = np.concatenate((original['first_crossings'], first), axis=0)
    return original, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('build', 'evaluate'))
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/lambda_constant_v1')
    args = parser.parse_args(); output = args.output; output.mkdir(parents=True, exist_ok=True)
    if (output/'status.json').exists():
        raise FileExistsError('Completed companion study retained; no overwrite')
    companion = json.loads((ROOT/'configs/lambda_constant.json').read_text())
    cfg = json.loads((ROOT/companion['base_config']).read_text())
    cfg.update({k: companion[k] for k in ('label', 'seed', 'replications', 'audit_path_prefix')})
    sources = source_hashes(); started = time.perf_counter()
    original_freeze = json.loads((ROOT/'reports/lambda_power_v2_results/protocol_frozen.json').read_text())
    for path in ('scripts/lambda_power_study.py', 'configs/lambda_power.json'):
        if sources[path] != original_freeze['source_files'][path]:
            raise ValueError('The original controlled experiment changed')
    if args.stage == 'build':
        entries = {}; audits = {}
        for name in cfg['models']:
            source = ROOT/companion['base_models']/f'model_{name}.npz'
            if digest(source) != original_freeze['model_files'][source.name]:
                raise ValueError('Original Bellman model no longer matches its freeze')
            shutil.copyfile(source, output/f'dp_model_{name}.npz')
            with np.load(source) as file:
                model = {k: file[k] for k in file.files}
            fixed, audit = fixed_model(cfg, model)
            np.savez_compressed(output/f'constant_model_{name}.npz', **fixed)
            entries[name] = {'best_bets': fixed['best_bets'].tolist(),
                             'initial_power': fixed['initial_power'].tolist(),
                             'dp_initial_power': [float(np.interp(0., model['states'], model['values'][h]))
                                                  for h in cfg['horizon_blocks']]}
            audits[name] = audit
            print(name, entries[name], flush=True)
        difference = max(abs(a-b) for a,b in zip(entries['primary']['initial_power'],
                                                 entries['refinement']['initial_power']))
        if difference > cfg['numerical_power_tolerance']:
            raise ArithmeticError('Fixed-policy power refinement failed before evaluation')
        manifest = dict(config=cfg, source_files=sources, models=entries, kernel_audits=audits,
            maximum_refinement_power_difference=difference,
            log_growth_bet=base.log_growth_bet(cfg),
            model_files={p.name: digest(p) for p in output.glob('*_model_*.npz')})
        (output/'model_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    else:
        manifest = json.loads((output/'model_manifest.json').read_text())
        frozen = json.loads((ROOT/'reports/lambda_constant_results/protocol_frozen.json').read_text())
        if manifest['config'] != cfg or manifest['source_files'] != sources or frozen['source_files'] != sources:
            raise ValueError('Source/configuration does not match the pre-evaluation freeze')
        for name, expected in frozen['model_files'].items():
            if digest(output/name) != expected:
                raise ValueError(f'Changed frozen working model: {name}')
        models = {}; fixed = {}
        for name in cfg['models']:
            with np.load(output/f'dp_model_{name}.npz') as file:
                models[name] = {k: file[k] for k in file.files}
            with np.load(output/f'constant_model_{name}.npz') as file:
                fixed[name] = {k: file[k] for k in file.files}
        rows = []
        streams = np.random.SeedSequence(cfg['seed']).spawn(len(cfg['score_means']))
        for mean, stream in zip(cfg['score_means'], streams):
            arrays, summary = simulate(cfg, mean, stream, models, fixed)
            rows.extend(summary)
            np.savez_compressed(output/f'mean_{mean:g}.npz', **arrays)
            pd.DataFrame(rows).to_csv(output/'summary.csv', index=False)
            print('evaluated mean', mean, flush=True)
        if source_hashes() != sources:
            raise RuntimeError('Scientific companion source changed during evaluation')
        (output/'status.json').write_text(json.dumps(dict(complete=True, config=cfg,
            source_files=sources, seconds=time.perf_counter()-started,
            scope='Fresh separate companion stream; no pooling with the original study. Fixed bets maximize the declared discretized working-model horizon power, not power under every law. No financial implementation or performance claim.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
