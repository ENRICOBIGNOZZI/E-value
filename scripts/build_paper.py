"""Build the manuscript from completed simulation results, then compile with Tectonic."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
import pandas as pd


def refine_figures(results):
    """Publication plots from numeric files; preserve the frozen simulation code."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.dpi':160,'savefig.bbox':'tight'})
    daily=pd.read_parquet(results/'daily_ledger.parquet')
    events=pd.read_parquet(results/'comparison_events.parquet')
    fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
    for name in ('Greedy','Repeated-HAC-p','E-process'):
        g=daily[daily.method.eq(name)]
        axes[0].plot(g.groupby('day').n_active.mean(),label=name)
    axes[0].set(ylabel='Mean selected support size',title='Methods with structural selection')
    axes[0].legend(fontsize=8)
    e=events[events.method.eq('E-process')]
    axes[1].plot(e.groupby('day').log_e.max(),marker='o',label='Largest current log E')
    axes[1].axhline(np.log(20),ls='--',color='black',label='Individual threshold')
    axes[1].set(xlabel='Simulation day',ylabel='Current log evidence');axes[1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(results/'figures/activity_evidence.png');plt.close(fig)
    path=results/'statistical_study.csv'
    if path.exists():
        study=pd.read_csv(path);fig,axes=plt.subplots(1,2,figsize=(10,3.7))
        for delta,g in study[study.delta>0].groupby('delta'):
            line=axes[0].plot(g.n,g.adaptive_crossing,label=f'delta={delta:g}')[0]
            color=line.get_color()
            axes[0].fill_between(g.n,g.ci_low,g.ci_high,color=color,alpha=.12)
            axes[0].plot(g.n,g.adaptive_bound,ls='--',color=color)
            axes[1].plot(g.block,g.mean_certificate_regret,color=color,label=f'delta={delta:g}')
            axes[1].plot(g.block,g.regret_bound,ls='--',color=color)
        axes[0].set(xlabel='Observations',ylabel='Crossing probability / lower bound')
        axes[1].set(xlabel='Block (h = 100)',ylabel='Certificate regret / upper bound')
        for ax in axes:ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(results/'figures/stationary_power.png');plt.close(fig)


def tex_escape(s):
    return str(s).replace('_',r'\_').replace('%',r'\%')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',default='outputs/park_revive_v1/frozen_pilot')
    parser.add_argument('--tail-results',default='outputs/park_revive_tail_v1/first_entry')
    parser.add_argument('--full-results',default='outputs/park_revive_full_v2/pilot')
    parser.add_argument('--full-pilot-count',type=int,help='Freeze the reported snapshot to this predeclared prefix starting at 50001')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    results=(root/args.results).resolve()
    cfg=json.loads((results/'config_frozen.json').read_text())
    metrics=pd.read_csv(results/'metrics_by_seed.csv')
    events=pd.read_parquet(results/'comparison_events.parquet')
    refine_figures(results)
    count=metrics.seed.nunique()
    lines=[f'The executed full-dimension pilot contains {count} independent seeds, with '
        f'$N={cfg["n_assets"]}$, $p=100$, $h={cfg["block"]}$ and {cfg["years"]} years per seed. '
        'These are pilot results, not the planned 500-seed final evaluation. '
        'Three separate reduced-dimension smoke seeds exercise the software only.',
        r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrr}',r'\toprule',
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
            f'The repeated uncorrected Bartlett-HAC normal test crosses at rate {null.repeated_hac_crossing:.4f}. '
            'The latter combines finite-sample approximation with repeated testing; '
            'these procedures therefore do not have matched overall type-I error. '
            'This is an individual-episode calibration experiment, not a financial-market performance result. '
            'Positive constant-mean experiments compare observed power and certificate regret with T2 bounds.']
    for filename,caption in [('equity_quantiles','Net wealth median and 10--90 percent quantiles across the executed seeds. Each method uses identical market observations within a seed.'),
        ('activity_evidence','Selected support size for the three search methods and largest current annual E-process evidence. All Signals and Oracle always permit all 100 signals. The threshold is individual; the search has no global 5 percent guarantee.'),
        ('stationary_power','Controlled constant-mean statistical experiments: empirical adaptive power and certificate regret (solid), and theoretical bounds (dashed). These experiments satisfy T2 rather than the regime-changing financial model.')]:
        if (results/'figures'/f'{filename}.png').exists():
            destination=root/'paper/figures';destination.mkdir(exist_ok=True)
            shutil.copy2(results/'figures'/f'{filename}.png',destination/f'{filename}.png')
            rel=Path('figures')/f'{filename}.png'
            lines += [r'\begin{figure}[H]\centering',f'\\includegraphics[width=.97\\linewidth]{{{rel}}}',f'\\caption{{{caption}}}',r'\end{figure}']
    lines += [r'\FloatBarrier']
    (root/'paper/generated_results.tex').write_text('\n\n'.join(lines)+'\n')
    snapshots=root/'reports/results';snapshots.mkdir(exist_ok=True)
    for name in ('metrics_by_seed.csv','paired_comparisons.csv','statistical_study.csv','config_frozen.json','seed_manifest.json','provenance.json'):
        if (results/name).exists():shutil.copy2(results/name,snapshots/name)
    tail_results=(root/args.tail_results).resolve()
    if (tail_results/'entry_summary.csv').exists():
        from build_tail_results import generate
        generate(root,tail_results)
    full_results=(root/args.full_results).resolve()
    if any(json.loads(p.read_text()).get('complete') for p in full_results.glob('seed_*/status.json')):
        from build_full_results import summarize
        snapshot=range(50001,50001+args.full_pilot_count) if args.full_pilot_count is not None else None
        summarize(full_results,root/'reports/full_results',root/'paper',snapshot)
    if (root/'reports/lambda_power_v2_results/verification.json').exists():
        from build_lambda_results import generate as generate_lambda
        generate_lambda(root)
    if (root/'reports/vanishing_gain_results/verification.json').exists():
        from build_vanishing_results import generate as generate_vanishing
        generate_vanishing(root)
    if (root/'reports/lambda_constant_results/verification.json').exists():
        from build_lambda_constant_results import generate as generate_lambda_constant
        generate_lambda_constant(root)
    engine=shutil.which('tectonic') or '/opt/homebrew/bin/tectonic'
    subprocess.run([engine,'--keep-logs','main.tex'],cwd=root/'paper',check=True)
    print(root/'paper/main.pdf')


if __name__=='__main__':main()
