"""Build the scalar cash-PARK manuscript diagnostic from retained audited CSVs."""
import hashlib
import json
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import shutil

import pandas as pd


def generate(root):
    results = root / 'reports/vanishing_gain_results'
    paper = root / 'paper'
    cfg = json.loads((results / 'config_frozen.json').read_text())
    verification = json.loads((results / 'verification.json').read_text())
    status = json.loads((results / 'status.json').read_text())
    if not verification['study_source_matches_frozen']:
        raise ValueError('The scalar study does not match its frozen source')
    actual_source = hashlib.sha256((root / 'scripts/vanishing_gain_study.py').read_bytes()).hexdigest()
    frozen = json.loads((root / 'reports/vanishing_gain_frozen.json').read_text())
    if cfg != status['config'] or cfg != json.loads((root / 'configs/vanishing_gain.json').read_text()):
        raise ValueError('The retained scalar configuration does not match its run')
    for name in ('config_frozen.json', 'status.json'):
        if hashlib.sha256((results / name).read_bytes()).hexdigest() != verification['input_sha256'][name]:
            raise ValueError(f'The audited scalar input changed: {name}')
    if actual_source != frozen['files']['scripts/vanishing_gain_study.py']:
        raise ValueError('Scientific scalar source changed after its frozen run')
    trajectory = pd.read_csv(results / 'trajectory_summary.csv')
    endpoint = pd.read_csv(results / 'endpoint_summary.csv')
    expected = trajectory[trajectory.observations.eq(cfg['observations'])].reset_index(drop=True)
    pd.testing.assert_frame_equal(expected, endpoint.reset_index(drop=True))
    alt = endpoint[endpoint.law.eq('gaussian_alternative') & endpoint.alpha.eq(.05)]
    null = endpoint[endpoint.law.eq('gaussian_feedback_null') & endpoint.alpha.eq(.05)]
    if len(alt) != 4 or len(null) != 4 or not alt.replications.eq(cfg['replications']).all():
        raise ValueError('Incomplete scalar diagnostic')
    if endpoint[endpoint.law.eq('gaussian_feedback_null')].crossings.sum() != 0:
        raise ValueError('The zero null-count description no longer matches')
    if endpoint[endpoint.law.eq('gaussian_alternative') & endpoint.alpha.lt(.05)].crossings.sum() != 0:
        raise ValueError('The smaller-level alternative-count description no longer matches')
    methods = [('Linear cash-PARK', 'Linear cash-PARK'),
               ('Catoni geometry fixed', 'Catoni, geometry, fixed'),
               ('Catoni uniform fixed', 'Catoni, uniform, fixed'),
               ('Catoni uniform past-mean', 'Catoni, uniform, past mean')]
    lines = [
        f'The separately frozen scalar experiment uses {cfg["replications"]:,} paths under '
        f'each of two laws, {cfg["observations"]:,} evaluated observations and '
        f'{cfg["training"]} training observations. It fixes $\\gamma=\\sigma=1$, '
        '$L=.5$, $r=0$, and public bounds $M_2=1$, $M_4=6$. '
        'The alternative is the iid Gaussian law of Theorem~\\ref{thm:vanishing}; '
        'the boundary null is \\eqref{eq:vanishing-null}. All four rules see '
        'the same return path within each law. The linear and two fixed Catoni '
        'stakes are $\\gamma/2$; the original uniform-bound past-mean stake '
        'updates every 252 observations. No positive minimum-effect filter is applied.',
        r'\begin{table}[H]\centering\small',
        r'\begin{tabular}{lrrrr}\toprule',
        r'& \multicolumn{2}{c}{Crossings / 4096} & \multicolumn{2}{c}{Alternative final log capital} \\',
        r'Rule & Alternative & Null & Mean & MC SE \\\midrule'
    ]
    for name, label in methods:
        a = alt[alt.method.eq(name)].iloc[0]
        q = null[null.method.eq(name)].iloc[0]
        lines.append(f'{label} & {int(a.crossings)} & {int(q.crossings)} & '
                     f'{a.mean_log_capital:.5f} & {a.mc_se_log_capital:.5f} \\\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Controlled scalar cash-PARK diagnostic at individual level 5\%. Crossings are over all evaluated dates, not just the last date. The 252-date review counts happen to coincide with these counts at this horizon. These are statistical paths, not financial market replications.}\label{tab:vanishing}\end{table}']
    if not (alt.crossings.to_numpy() == alt.annual_crossings.to_numpy()).all():
        raise ValueError('The annual-review statement no longer matches the retained results')
    checks = sum(item['scalar_checks'] for item in verification['replay'].values())
    prefix = min(item['replayed_path_prefix'] for item in verification['replay'].values())
    error = max(item['max_absolute_error'] for item in verification['replay'].values())
    linear = alt[alt.method.eq('Linear cash-PARK')].iloc[0]
    geometry = alt[alt.method.eq('Catoni geometry fixed')].iloc[0]
    realized_path = results/'realized_benefit_summary.csv'
    if realized_path.exists():
        realized_audit = json.loads((results/'realized_benefit_verification.json').read_text())
        if hashlib.sha256(realized_path.read_bytes()).hexdigest() != realized_audit['summary_sha256']:
            raise ValueError('Saved realized-utility summary changed after verification')
        if realized_audit['input_sha256'] != {name:verification['input_sha256'][name]
                                              for name in realized_audit['input_sha256']}:
            raise ValueError('Realized-utility summary uses a different saved path archive')
        realized = pd.read_csv(realized_path)
        realized = realized[realized.law.eq('gaussian_alternative')].iloc[0]
        if (realized.paths != cfg['replications'] or realized.observations != cfg['observations']
                or abs(realized.mean_conditional_benefit-linear.mean_conditional_benefit)>1e-10):
            raise ValueError('Realized utility does not refer to the reported scalar horizon')
        lines.append(f'A subsequent summary of the same saved paths gives mean realized cumulative '
            f'cash advantage $J_n={realized.mean_realized_benefit:.5f}$ '
            f'(MC SE {realized.mc_se_realized_benefit:.5f}); '
            f'{int(realized.negative_realized_paths)} of {int(realized.paths):,} realized sums are negative. '
            'This is a post-hoc fixed-horizon description, not another experiment, '
            'a stopped-cost estimate or a verification of the almost-sure limit.')
    family_path = results/'uniform_family_bound.json'
    if family_path.exists():
        family = json.loads(family_path.read_text())
        if not family['complete'] or family['config_sha256'] != verification['input_sha256']['config_frozen.json']:
            raise ValueError('Uniform-family bound uses a different scalar configuration')
        for name,digest in family['source_sha256'].items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Uniform-family bound derivation changed after audit')
        ceiling = next(r for r in family['bounds'] if r['alpha']==.05)['ever_power_upper_bound']
        percent = (Decimal(str(ceiling))*100).quantize(Decimal('0.01'),rounding=ROUND_CEILING)
        lines.append(f'For the same toy configuration, Proposition~\\ref{{prop:vanishing-uniform}} '
            f'gives an upper bound of {percent}\\% on ever rejecting at level 5\\% '
            'for every predictable constant-certificate Catoni bet policy, including '
            'level-dependent choices. This is a deterministic upper bound over an '
            'unlimited horizon, not an observed crossing fraction or a finite-horizon '
            'ranking against the linear rule. The inequality uses an explicit '
            'conservative expectation bound for the compensator.')
    lines += [
        f'The linear crossing fraction is {linear.crossing_fraction:.6f} '
        f'(Wilson 95\\% interval [{linear.wilson_low:.6f}, {linear.wilson_high:.6f}]); '
        f'the geometric fraction is {geometry.crossing_fraction:.6f} '
        f'([{geometry.wilson_low:.6f}, {geometry.wilson_high:.6f}]). '
        'Three versus one crossing does not establish a finite-sample power ranking. '
        'All rules have zero observed alternative crossings at the separately declared '
        '1\\% and .1\\% levels. Every null count is zero at all three levels; '
        'the Wilson 95\\% upper bound for each zero count is .000937. '
        'Zero observed crossings do not establish zero probability.',
        f'The mean integrated squared target is {linear.mean_sum_w2:.5f}, and the '
        f'mean cumulative conditional cash benefit is {linear.mean_conditional_benefit:.5f} '
        'in the toy utility units. These are unstopped-horizon means, not expected '
        'benefits at rejection or calibrated financial returns. '
        f'The mean evaluator log likelihood ratio is {linear.mean_log_lr:.5f}; '
        f'the linear rule has mean absolute log discrepancy {linear.mean_absolute_log_lr_difference:.5f}. '
        'The finite-horizon diagnostics do not establish the asymptotic bounds by themselves.',
        f'Independent replay checks {checks:,} scalar checkpoint values using direct '
        'multiplication of factors and separate Gaussian density calculations. '
        f'It covers a fixed prefix of {prefix} paths per law, not all simulated paths; '
        f'the maximum absolute discrepancy is {error:.2e}. '
        'All declared paths and failed-to-cross outcomes are retained. '
        'No horizon, bound, bet or seed was retuned after observing low power.',
        r'\begin{figure}[H]\centering',
        r'\includegraphics[width=\linewidth]{figures/vanishing_gain.png}',
        r'\caption{Scalar vanishing-gain diagnostic. Left: mean log capital with pointwise 95\% Monte Carlo intervals; the uniform fixed-bet rule is omitted from this panel because its large negative values obscure the other series. The $1/8$ line is a slope guide, not an exact finite-horizon formula. Right: all-date crossing fractions at level 5\% with pointwise Wilson intervals. Bands are not simultaneous over time.}\label{fig:vanishing}\end{figure}',
        'Eventual crossing and a sharp confidence exponent can coexist with very low '
        'finite-horizon power. The experiment supplies no financial performance '
        'improvement or adaptation theorem for changing regimes.'
    ]
    shutil.copyfile(results / 'vanishing_gain.png', paper / 'figures/vanishing_gain.png')
    (paper / 'generated_vanishing_results.tex').write_text('\n\n'.join(lines) + '\n')


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1])
