"""Build the manuscript from completed simulation results, then compile with Tectonic."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
import pandas as pd


def tex_escape(s):
    return str(s).replace('_',r'\_').replace('%',r'\%')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',default='outputs/park_revive_v1/pilot')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    results=(root/args.results).resolve()
    cfg=json.loads((results/'config_frozen.json').read_text())
    metrics=pd.read_csv(results/'metrics_by_seed.csv')
    events=pd.read_parquet(results/'comparison_events.parquet')
    count=metrics.seed.nunique()
    lines=[f'The executed full-dimension pilot contains {count} independent seeds, with '
        f'$N={cfg["n_assets"]}$, $p=100$, $h={cfg["block"]}$ and {cfg["years"]} years per seed. '
        'These are pilot results, not the planned 500-seed final evaluation. '
        'Three separate reduced-dimension smoke seeds exercise the software only.',
        r'\begin{table}[ht]\centering\small',r'\begin{tabular}{lrrrr}',r'\toprule',
        r'Method & Utility$\times h$ & Net Sharpe & Moves & Inactive \\',r'\midrule']
    summary=metrics.groupby('method',sort=False).agg(u=('annual_scaled_utility','mean'),sr=('sharpe','mean'),moves=('moves','mean'),idle=('inactive_fraction','mean'))
    for name,r in summary.iterrows():
        sr=f'{r.sr:.3f}' if pd.notna(r.sr) else 'NA'
        lines.append(f'{tex_escape(name)} & {r.u:.5f} & {sr} & {r.moves:.2f} & {r.idle:.3f} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',r'\caption{Means across executed pilot seeds. Utility is mean daily utility rescaled by $h$, not an annual certainty equivalent. Inactive paths have undefined Sharpe.}\end{table}']
    e=events[events.method.eq('E-process')]
    lines += [f'The public bound is $\\nu^2={e.nu2.iloc[0]:.7f}$. '
        f'The largest current annual log evidence is {e.log_e.max():.6f}, '
        f'compared with $\\log20={__import__("math").log(20):.6f}$. '
        'The small number of seeds is insufficient for a reliable ranking of methods. '
        'The conservative certificate and annual opportunity cost must be assessed before '
        'any assertion of economic advantage.']
    study=results/'statistical_study.csv'
    if study.exists():
        s=pd.read_csv(study);null=s[s.delta.eq(0)].iloc[-1]
        lines += [f'Separate controlled statistical diagnostics use {int(null.replications):,} replications '
            f'and {int(null.n)} observations. Under a predictable heteroskedastic conditional-mean-zero law, '
            f'the adaptive e-process crosses at rate {null.adaptive_crossing:.4f} '
            f'(Wilson interval [{null.ci_low:.4f}, {null.ci_high:.4f}]). '
            'This is an individual-episode calibration experiment, not a financial-market performance result. '
            'Positive constant-mean experiments compare observed power and certificate regret with T2 bounds.']
    for filename,caption in [('equity_quantiles','Net wealth median and 10--90 percent quantiles across the executed seeds. Each method uses identical market observations within a seed.'),
        ('activity_evidence','Selected support size and largest current annual E-process evidence. The threshold is individual; the search has no global 5 percent guarantee.'),
        ('stationary_power','Controlled constant-mean statistical experiments: empirical adaptive power and certificate regret (solid), and theoretical bounds (dashed). These experiments satisfy T2 rather than the regime-changing financial model.')]:
        if (results/'figures'/f'{filename}.png').exists():
            destination=root/'paper/figures';destination.mkdir(exist_ok=True)
            shutil.copy2(results/'figures'/f'{filename}.png',destination/f'{filename}.png')
            rel=Path('figures')/f'{filename}.png'
            lines += [r'\begin{figure}[ht]\centering',f'\\includegraphics[width=.97\\linewidth]{{{rel}}}',f'\\caption{{{caption}}}',r'\end{figure}']
    lines += [r'\clearpage']
    (root/'paper/generated_results.tex').write_text('\n\n'.join(lines)+'\n')
    snapshots=root/'reports/results';snapshots.mkdir(exist_ok=True)
    for name in ('metrics_by_seed.csv','paired_comparisons.csv','statistical_study.csv','config_frozen.json','seed_manifest.json','provenance.json'):
        if (results/name).exists():shutil.copy2(results/name,snapshots/name)
    engine=shutil.which('tectonic') or '/opt/homebrew/bin/tectonic'
    subprocess.run([engine,'--keep-logs','main.tex'],cwd=root/'paper',check=True)
    print(root/'paper/main.pdf')


if __name__=='__main__':main()
