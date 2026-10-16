"""Generate the separately frozen constant-power companion table from its audit."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import pandas as pd


def generate(root):
    results = root/'reports/lambda_constant_results'
    audit = json.loads((results/'verification.json').read_text())
    frozen = json.loads((results/'protocol_frozen.json').read_text())
    manifest = json.loads((results/'model_manifest.json').read_text())
    cfg = manifest['config']
    if not audit['all_model_calibrations_pass'] or not audit['study_source_matches_freeze']:
        raise ValueError('Unresolved companion audit')
    for name in ('summary.csv', 'status.json', 'model_manifest.json'):
        if hashlib.sha256((results/name).read_bytes()).hexdigest() != audit['inputs'][name]:
            raise ValueError(f'Changed audited input: {name}')
    if hashlib.sha256((results/'model_manifest.json').read_bytes()).hexdigest() != frozen['model_files']['model_manifest.json']:
        raise ValueError('Working-model selection changed after freeze')
    table = pd.read_csv(results/'summary.csv')
    paired = pd.read_csv(results/'paired_comparisons.csv')
    refinement_bound = Decimal(str(manifest['maximum_refinement_power_difference'])).quantize(
        Decimal('.000001'), rounding=ROUND_CEILING)

    def row(kind, mean, horizon, version='primary'):
        name = f'{kind} {version} H={horizon}'
        return table[table.method.eq(name) & table['mean'].eq(mean) & table.observations.eq(horizon)].iloc[0]

    def percent(record):
        return str((Decimal(int(record.crossings))*100/Decimal(int(record.replications))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

    lines = [r'\subsection{A fresh comparison with a deadline-optimized constant}',
        'The first experiment compares the Bellman rule with certificate and '
        'log-growth bets, which target different objectives. To separate '
        'deadline calibration from adaptation to evidence, a new companion '
        'experiment chooses the best constant stake on each existing action '
        'grid for each deadline. It maximizes working-model probability of '
        'crossing at a review, using a constant-action recursion rather than '
        'the Bellman maximum at each state. Stake selection and source hashes '
        'are frozen before drawing the fresh seed-450001 stream. This is an '
        'explicitly subsequent comparison, not an additional arm fitted to the '
        'first experiment or extra replications of its paths.',
        r'Writing $W_0^\lambda=V_0$, the constant-action recursion is '
        r'$W_k^\lambda(\ell)=1$ for $\ell\ge b_\alpha$, and '
        r'$W_k^\lambda(\ell)=\int W_{k-1}^\lambda(\ell+z)Q_\lambda(dz)$ '
        r'otherwise. The selected constant maximizes $W_H^\lambda(0)$ over '
        r'the grid actions, rather than taking a new maximum at every state.',
        'Both grids select the same three constant bets. Their predicted '
        f'maximum powers differ by at most {refinement_bound}. '
        'The fixed-arm simulation holds its stake until crossing or its own '
        'deadline, including below the computational lower boundary; absorption '
        'there is only a numerical approximation in its value calculation. '
        'All twelve predicted-versus-observed DP/constant design-power checks '
        'pass the same declared numerical-plus-Monte-Carlo tolerance.',
        r'\begin{table}[H]\centering\small',
        r'\begin{tabular}{rrrrrl}\toprule',
        r'Deadline & Constant $\lambda$ & Constant (\%) & Horizon DP (\%) & Gain (pp) & 95\% MC interval \\\midrule']
    for j, blocks in enumerate(cfg['horizon_blocks']):
        horizon = blocks*cfg['block']
        constant = row('Constant', .1, horizon); dp = row('DP', .1, horizon)
        comparison = paired[paired['mean'].eq(.1) & paired.observations.eq(horizon) & paired.model.eq('primary')].iloc[0]
        gain = (Decimal(int(dp.crossings)-int(constant.crossings))*100/Decimal(int(dp.replications))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        lines.append(f'{horizon} & {manifest["models"]["primary"]["best_bets"][j]:.5f} & '
            f'{percent(constant)} & {percent(dp)} & {gain} & '
            f'[{100*comparison.ci_low:.2f}, {100*comparison.ci_high:.2f}] \\\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Fresh companion comparison at actual mean .1, with 20,000 paired paths, the unchanged nominal individual 5\% bound, and the common betting/review calendar. Constants maximize horizon power on the declared working-model action grid. Each deadline uses its own two policies. Gain intervals are pointwise paired normal-approximation Monte Carlo intervals, unadjusted across comparisons; this is not matched-actual-size inference.}\label{tab:constant-power}\end{table}']
    primary = row('DP', .1, 400); constant = row('Constant', .1, 400)
    null_dp = row('DP', 0., 400); null_constant = row('Constant', 0., 400)
    lines.append(f'At 400 observations the counts are {int(primary.crossings)}/20000 '
        f'for horizon DP and {int(constant.crossings)}/20000 for the optimized constant. '
        f'The corresponding null fractions are {percent(null_dp)}\\% and {percent(null_constant)}\\%. '
        'Thus the gain is beyond selecting one better constant at the common '
        'nominal level; actual null rejection probabilities remain different. '
        'Both numerical resolutions, the unchanged earlier comparators and '
        'actual means .2 and .3 are retained in the report. Original and '
        'companion powers are reported separately and are not pooled.')
    lines.append(f'The independent companion audit reconstructs every DP/fixed '
        f'stake and every first crossing ({audit["scalar_checks"]:,} scalar checks). '
        f'Direct multiplicative score replay covers sixteen paths per law and '
        f'has maximum log-capital discrepancy {audit["max_prefix_log_capital_error"]:.2e}; '
        'it is not a replay of every score path. This comparison supplies '
        'neither a continuous-action global optimum nor a financial performance claim.')
    (root/'paper/generated_lambda_constant_results.tex').write_text('\n\n'.join(lines)+'\n')


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1])
