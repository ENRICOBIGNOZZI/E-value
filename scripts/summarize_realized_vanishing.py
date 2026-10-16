#!/usr/bin/env python3
"""Summarize already saved realized utilities; generate no new observations."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    output = ROOT/'outputs/vanishing_gain_v1'
    reports = ROOT/'reports/vanishing_gain_results'
    audit = json.loads((reports/'verification.json').read_text())
    if not audit['study_source_matches_frozen']:
        raise ValueError('Original scalar study lacks its frozen-source audit')
    for name in ('config_frozen.json', 'status.json'):
        if sha256(output/name) != audit['input_sha256'][name]:
            raise ValueError(f'Original scalar provenance changed: {name}')
    config = json.loads((output/'config_frozen.json').read_text())
    freeze = json.loads((ROOT/'reports/vanishing_gain_frozen.json').read_text())
    if sha256(ROOT/'scripts/vanishing_gain_study.py') != freeze['files']['scripts/vanishing_gain_study.py']:
        raise ValueError('Scientific source differs from original freeze')
    rows = []
    inputs = {}
    for law in config['laws']:
        path = output/f'{law}.npz'
        inputs[path.name] = sha256(path)
        if inputs[path.name] != audit['input_sha256'][path.name]:
            raise ValueError('Original saved archive differs from independent audit')
        with np.load(path) as archive:
            if int(archive['times'][-1]) != config['observations']:
                raise ValueError('Incomplete saved observation horizon')
            conditional = archive['conditional_benefit'][-1]
            realized = archive['realized_benefit'][-1]
            if law == 'gaussian_alternative':
                np.testing.assert_allclose(conditional,
                    config['gamma']*config['sigma']**2*archive['sum_w2'][-1]/2,
                    atol=2e-11, rtol=1e-11)
        n = config['replications']
        if conditional.shape != (n,) or realized.shape != (n,):
            raise ValueError('Wrong retained path membership')
        difference = realized-conditional
        negative = int((realized<0).sum())
        rate = negative/n
        z = 1.959963984540054
        center = (rate+z*z/(2*n))/(1+z*z/n)
        radius = z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
        rows.append(dict(law=law, observations=config['observations'], paths=n,
            mean_conditional_benefit=float(conditional.mean()),
            mc_se_conditional_benefit=float(conditional.std(ddof=1)/np.sqrt(n)),
            mean_realized_benefit=float(realized.mean()),
            mc_se_realized_benefit=float(realized.std(ddof=1)/np.sqrt(n)),
            mean_realized_minus_conditional=float(difference.mean()),
            paired_mc_se_difference=float(difference.std(ddof=1)/np.sqrt(n)),
            negative_realized_paths=negative, negative_realized_fraction=rate,
            negative_fraction_wilson_low=max(0.,float(center-radius)),
            negative_fraction_wilson_high=min(1.,float(center+radius))))
    table = reports/'realized_benefit_summary.csv'
    with table.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    verification = dict(complete=True, scientific_source_freeze='57752eb',
        summary_source_sha256=sha256(Path(__file__)), input_sha256=inputs,
        summary_sha256=sha256(table), original_saved_paths_unchanged=True,
        scope='Post-hoc deterministic summary of saved fixed-horizon conditional and realized utility on the original 4096 paths/law. No new paths, stopping-cost estimate, asymptotic verification or extension of the original eight-path/law independent score replay.')
    (reports/'realized_benefit_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__ == '__main__':
    main()
