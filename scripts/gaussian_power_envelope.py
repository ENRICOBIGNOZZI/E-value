"""Post-hoc Gaussian power bounds: audited counts, no simulation or retuning."""
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path

from scipy.integrate import quad
from scipy.stats import beta, norm

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def envelope(size, shift):
    """NP power against a standardized nonnegative Gaussian mean shift."""
    if not math.isfinite(size) or not 0 <= size <= 1:
        raise ValueError('Size must be a probability')
    if not math.isfinite(shift) or shift < 0:
        raise ValueError('Shift must be finite and nonnegative')
    if size in (0, 1):
        return float(size)
    return float(norm.cdf(shift + norm.ppf(size)))


def binomial_bounds(count, total, tail):
    """One-sided exact binomial limits, each with noncoverage at most tail."""
    if type(count) is not int or type(total) is not int or not 0 <= count <= total or total < 1:
        raise ValueError('Invalid binomial count')
    if not 0 < tail < 1:
        raise ValueError('Invalid tail probability')
    lower = 0. if count == 0 else float(beta.ppf(tail, count, total-count+1))
    upper = 1. if count == total else float(beta.isf(tail, count+1, total-count))
    return lower, upper


def selected_counts(rows, config):
    """Require the complete existing DP/constant by grid/deadline panel."""
    horizons = [int(h*config['block']) for h in config['horizon_blocks']]
    methods = [(f'{kind} {grid} H={h}', h) for grid in config['models']
               for h in horizons for kind in ('DP', 'Constant')]
    expected = {(float(mean), method, h) for mean in config['score_means']
                for method, h in methods}
    selected = {}
    for row in rows:
        key = (float(row['mean']), row['method'], int(row['observations']))
        if key not in expected:
            continue  # Other original comparators are outside this diagnostic.
        if key in selected:
            raise ValueError('Duplicate companion row')
        count, total = int(row['crossings']), int(row['replications'])
        if total != config['replications'] or not 0 <= count <= total:
            raise ValueError('Wrong sample size or crossing count')
        if not math.isclose(float(row['power']), count/total, rel_tol=0., abs_tol=1e-14):
            raise ValueError('Stored power does not match its count')
        selected[key] = (count, total)
    if set(selected) != expected:
        raise ValueError('Missing declared companion row')
    return selected, methods


def calculate(rows, config):
    selected, methods = selected_counts(rows, config)
    means = [float(mean) for mean in config['score_means'] if mean > 0]
    if 0. not in config['score_means'] or not means or config['score_sd'] <= 0:
        raise ValueError('Gaussian null, positive alternatives and positive scale required')
    family = len(methods)*(1+len(means))
    tail = .05/family
    output = []
    for method, horizon in methods:
        null_count, total = selected[(0., method, horizon)]
        _, null_upper = binomial_bounds(null_count, total, tail)
        for mean in means:
            count, n = selected[(mean, method, horizon)]
            power_lower, _ = binomial_bounds(count, n, tail)
            shift = mean*math.sqrt(horizon)/config['score_sd']
            upper = envelope(null_upper, shift)
            output.append(dict(method=method, observations=horizon, alternative_mean=mean,
                replications=n, null_crossings=null_count, alternative_crossings=count,
                observed_null_fraction=null_count/total, observed_power=count/n,
                nominal_size_envelope=envelope(config['alpha'], shift),
                empirical_size_plugin_envelope=envelope(null_count/total, shift),
                simultaneous_null_size_upper=null_upper, simultaneous_power_lower=power_lower,
                simultaneous_power_envelope_upper=upper,
                compatible_with_simultaneous_envelope=bool(power_lower <= upper)))
    return dict(rows=output, simultaneous_coverage_at_least=.95,
                one_sided_binomial_bounds_in_family=family, per_bound_noncoverage=tail)


def run(root):
    directory = root/'reports/lambda_constant_results'
    audit = json.loads((directory/'verification.json').read_text())
    freeze = json.loads((directory/'protocol_frozen.json').read_text())
    manifest = json.loads((directory/'model_manifest.json').read_text())
    if not audit['study_source_matches_freeze'] or not audit['all_model_calibrations_pass']:
        raise ValueError('Companion audit is unresolved')
    for name in ('summary.csv', 'model_manifest.json', 'status.json'):
        if digest(directory/name) != audit['inputs'][name]:
            raise ValueError(f'Changed audited companion input: {name}')
    if digest(directory/'model_manifest.json') != freeze['model_files']['model_manifest.json']:
        raise ValueError('Changed pre-evaluation working model')
    for source, expected in freeze['source_files'].items():
        if digest(root/source) != expected:
            raise ValueError(f'Changed frozen scientific source: {source}')
    for source, expected in audit['audit_sources'].items():
        if digest(root/source) != expected:
            raise ValueError(f'Changed count-audit source: {source}')
    if manifest['config'] != freeze['config']:
        raise ValueError('Changed configuration')
    with (directory/'summary.csv').open(newline='') as handle:
        result = calculate(list(csv.DictReader(handle)), manifest['config'])
    checks = []
    for size in (.001, .01, .05, .2, .5, .9):
        for shift in (.5, 2., 4.):
            direct, error = quad(lambda x: norm.pdf(x-shift), norm.isf(size), math.inf,
                                 epsabs=1e-12, epsrel=1e-12)
            discrepancy = abs(direct-envelope(size, shift))
            if discrepancy > 1e-11:
                raise ArithmeticError('Gaussian envelope quadrature disagreement')
            checks.append(dict(size=size, standardized_shift=shift,
                               discrepancy=discrepancy, quadrature_error=error))
    # Retain even an incompatible diagnostic; a statistical flag must not
    # suppress a report or select which fixed comparisons become visible.
    result.update(complete=True, post_hoc=True, input_sha256={
        str(directory.relative_to(root)/name): digest(directory/name)
        for name in ('verification.json', 'protocol_frozen.json', 'summary.csv',
                     'model_manifest.json', 'status.json')},
        source_sha256={str(path): digest(root/path) for path in (
            Path('scripts/gaussian_power_envelope.py'), Path('reports/gaussian_power_envelope.md'))},
        deterministic_quadrature_checks=checks,
        scope='Classical simple-Gaussian fixed-horizon upper envelope, including early stopping. Empirical-size plug-ins are descriptive, not true-size bounds or matched-size recalibration. Exact-binomial one-sided limits use a union bound over the complete diagnostic panel. No new paths, selected policies, general moment-null power optimum, causal decomposition or financial claim.')
    (directory/'gaussian_power_envelope.json').write_text(json.dumps(result, indent=2)+'\n')

    def percent(value):
        return str((Decimal(str(value))*100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

    config = manifest['config']
    horizons = [int(h*config['block']) for h in config['horizon_blocks']]
    nominal = ', '.join(percent(envelope(config['alpha'], config['design_mean']*math.sqrt(h)/config['score_sd']))+r'\%'
                        for h in horizons)
    plugin = ', '.join(percent(next(row['empirical_size_plugin_envelope'] for row in result['rows']
                                  if row['method'] == f'DP primary H={h}'
                                  and row['alternative_mean'] == config['design_mean']))+r'\%' for h in horizons)
    lines = [r'\paragraph{A Gaussian power envelope.}',
        r'The classical Neyman--Pearson bound \cite{neymanpearson} also applies to '
        r'early rejection by a fixed deadline. For iid $N(0,\sigma^2)$ versus '
        r'$N(\delta,\sigma^2)$, $\delta>0$, any test with actual null rejection '
        r'probability $s$ by $H$ has power at most',
        r'\[B_H(s)=\Phi\!\left(\delta\sqrt H/\sigma+\Phi^{-1}(s)\right).\]',
        r'Indeed, its rejection event is measurable from the first $H$ scores; '
        r'their likelihood ratio is increasing in their sum. A terminal upper-tail '
        r'sum test maximizes power at size $s$, giving the formula. Independent '
        r'test randomization does not improve this bound. This oracle fixes the '
        r'two Gaussian laws: its attaining test need not be valid over the full '
        r'moment null or under unrestricted monitoring.',
        f'At the design alternative, $B_H(.05)$ is {nominal} at the three deadlines. '
        f'Substituting the observed null fractions of the fresh primary DP rules gives '
        f'descriptive values {plugin}. These plug-ins do not determine the true '
        r'null sizes or establish matched-size dominance. The post-hoc report '
        r'retains both grids, both rule classes and all three alternatives, and '
        r'gives simultaneous exact-binomial uncertainty limits. It uses the '
        r'existing audited counts without new paths, threshold changes or policy selection.']
    (root/'paper/generated_gaussian_power_envelope.tex').write_text('\n\n'.join(lines)+'\n')
    return result


if __name__ == '__main__':
    result = run(ROOT)
    print(json.dumps(dict(rows=len(result['rows']),
        one_sided_bounds=result['one_sided_binomial_bounds_in_family'],
        quadrature_checks=len(result['deterministic_quadrature_checks']),
        maximum_quadrature_discrepancy=max(row['discrepancy'] for row in result['deterministic_quadrature_checks']),
        all_simultaneous_checks_compatible=all(row['compatible_with_simultaneous_envelope'] for row in result['rows'])), indent=2))
