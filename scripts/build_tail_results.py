"""Numerically reproduce the extension section, including terminal-entry caveats."""
from pathlib import Path
import hashlib
import json
import shutil
import pandas as pd


def generate(root,results):
    root=Path(root);results=Path(results)
    protocol=json.loads((results/'protocol_frozen.json').read_text())
    summary=pd.read_csv(results/'summary_by_seed.csv')
    table=pd.read_csv(results/'entry_summary.csv')
    entries=pd.read_csv(results/'first_entries.csv')
    n=summary.seed.nunique();cfg=protocol['config'];horizon=cfg['years']*cfg['block']
    assert not summary.duplicated(['seed','arm']).any()
    assert set(summary.arm)==set(protocol['arms'])
    assert (summary.groupby('arm').seed.nunique()==n).all()
    lines=[r'\subsection{Executed first-entry mechanism study}',
        f'The executed mechanism study contains {n} fresh markets from seeds 40001--40020, using '
        f'$N={cfg["n_assets"]}$, $p=100$ and the {cfg["years"]}-year DGP of the baseline. '
        'The four arms share every candidate shadow policy and every realized utility score. '
        'All 100 comparisons remain under observation to the common horizon, including after crossing. '
        'These are fixed-reference mechanism experiments, not twenty new full-strategy backtests.',
        r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrr}',r'\toprule',
        r'Arm & Entry markets & Before end & Median year & Max. log E \\',r'\midrule']
    terminal=[]
    for arm in protocol['arms']:
        row=table[table.arm.eq(arm)].iloc[0];g=summary[summary.arm.eq(arm)]
        nonterminal=int(((g.first_entry_day>=0)&(g.first_entry_day<horizon)).sum())
        at_end=int(g.first_entry_day.eq(horizon).sum())
        terminal.append(dict(arm=arm,seeds=n,nonterminal_entry_markets=nonterminal,
            terminal_first_entries=at_end,censored_test_entries=int(g.first_entry_day.lt(0).sum())))
        median=f'{row.median_first_entry_oos_year:.1f}' if pd.notna(row.median_first_entry_oos_year) else 'NA'
        label=arm.replace('-','--')
        lines.append(f'{label} & {int(row.markets_with_entry)}/{n} & {nonterminal}/{n} & {median} & {row.max_annual_log_e:.3f} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r"\caption{Annual eligible first-entry events. ``Before end'' excludes a first crossing at the terminal revision. Median year is conditional on crossing; censored markets remain in the entry-rate denominator. No actual post-entry fund path is simulated.}\end{table}"]
    geom=table[table.arm.eq('Tail-geometry')].iloc[0]
    geometry_terminal=next(item for item in terminal if item['arm']=='Tail-geometry')
    terminal_count=geometry_terminal['terminal_first_entries']
    terminal_statement=('One first certification occurs only at the terminal revision; ' if terminal_count==1
                        else f'{terminal_count} first certifications occur only at the terminal revision; ')
    lines += [f'The corrected-tail geometric arm has {int(geom.markets_with_entry)} entry markets out of {n}; '
        f'the Wilson 95\\% interval for this market-level fraction is '
        f'[{max(0,geom.wilson_low):.3f}, {min(1,geom.wilson_high):.3f}]. '
        'It is a search outcome over 100 candidates, not an individual-test power estimate '
        'or a globally controlled rejection probability. '
        f'{terminal_statement}'
        f'{geometry_terminal["nonterminal_entry_markets"]} markets have any remaining market observations after certification. '
        'Neither geometric Catoni nor uniform-moment corrected-tail betting alone produces an entry '
        f'in these {n} markets. The combined change improves statistical feasibility but does '
        'not remove the substantial cost of waiting.']
    proxies=entries.signal.str[1:].astype(int).ge(85)
    positive=(entries.loc[proxies,'true_current_mean']>0).all()
    if proxies.any():
        lines += [f'{int(proxies.sum())} selected first policies use structural proxies whose own coefficient '
            'is fixed at zero in the generator. '+
            ('Their conditional shadow gains are positive on the last evaluated date before selection. ' if positive else '')+
            'This illustrates the distinction between structural and economic relevance; it is not '
            'a false-discovery calibration result. These conditional gains refer to the shadow state, '
            'not a claim that the fund can acquire the shadow positions without paying its actual entry cost.']
    deployment_path=results/'deployment_audit.csv'
    if deployment_path.exists():
        deployment=pd.read_csv(deployment_path)
        within=deployment[~deployment.terminal]
        positives=int(within.actual_entry_gain_positive.sum())
        lines += [f'An additional post-hoc action audit replays all selected histories, '
            'refits with then-available observations and computes a hypothetical next-period '
            'entry from the fund\'s actual zero allocation. It values that action with true '
            'current model moments after selection, without drawing the next return. '
            f'{positives} of {len(within)} nonterminal entries have positive conditional utility '
            f'after actual entry costs. The mean is {10000*within.actual_entry_conditional_gain.mean():.3f} '
            'basis points of daily utility, compared with '
            f'{10000*within.next_shadow_conditional_gain.mean():.3f} for the continuing shadow; '
            f'the actual entry cost is {10000*within.actual_entry_cost.mean():.3f} basis points. '
            'This conditional action valuation is descriptive and supplies no post-entry fund '
            'path or new guarantee of current profitability.']
    controls=pd.read_csv(results/'controlled_tail_study.csv')
    null=controls[controls.delta.eq(0)].iloc[-1]
    lines += [f'Separate predictable skew-null diagnostics use {int(null.replications):,} independent paths '
        f'and {int(null.observations):,} observations. The corrected mixture crosses at rate '
        f'{null.corrected_crossing:.4f} (Wilson interval [{null.ci_low:.4f}, {null.ci_high:.4f}]). '
        'An invalid single bettor ($B_t=V_{4,t}^{1/4}$, fraction $.75$) without '
        f'bias correction crosses at rate {null.naive_uncorrected_crossing:.4f}. '
        'This is an invalidity demonstration; its configuration differs from the mixture, '
        'so it is not a matched power comparison.']
    for name,caption in (
        ('first_entry_feasibility','First-entry feasibility across twenty complete fresh markets. Every arm uses the same scores. Curves include terminal test events, with no claim of post-entry trading performance.'),
        ('controlled_tail_calibration','Controlled statistical experiment under a predictable skewed null and two positive-mean alternatives. The invalid negative control is a single uncorrected bettor; it is not a matched power comparison with the corrected mixture. Shading shows Wilson intervals across independent paths.')):
        dest=root/'paper/figures'/f'{name}.png';dest.parent.mkdir(exist_ok=True)
        shutil.copy2(results/'figures'/f'{name}.png',dest)
        lines += [r'\begin{figure}[H]\centering',f'\\includegraphics[width=.97\\linewidth]{{figures/{name}.png}}',
            f'\\caption{{{caption}}}',r'\end{figure}']
    lines += [r'\FloatBarrier']
    (root/'paper/generated_tail_results.tex').write_text('\n\n'.join(lines)+'\n')
    snapshots=root/'reports/tail_results';snapshots.mkdir(exist_ok=True)
    for name in ('summary_by_seed.csv','entry_summary.csv','first_entries.csv','controlled_tail_study.csv',
                 'protocol_frozen.json','controlled_protocol.json'):
        shutil.copy2(results/name,snapshots/name)
    for name in ('deployment_audit.csv','deployment_audit_protocol.json','evidence_replay_verification.json'):
        if (results/name).exists():shutil.copy2(results/name,snapshots/name)
    pd.DataFrame(terminal).to_csv(snapshots/'terminal_entry_audit.csv',index=False)
    source=json.loads((results/'seed_40001/source_manifest.json').read_text())
    (snapshots/'source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    control_metadata=json.loads((results/'controlled_protocol.json').read_text())
    assert control_metadata['script_sha256']==hashlib.sha256((root/'scripts/tail_study.py').read_bytes()).hexdigest()
    return dict(markets=n,entry_markets=int(geom.markets_with_entry),
                median_entry_year=geom.median_first_entry_oos_year,terminal_audit=terminal)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--results',default='outputs/park_revive_tail_v1/first_entry')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    print(generate(root,(root/args.results).resolve()))
