"""Explicitly exploratory: portfolio architecture and 13-theme aggregation.

Added after the 153-factor market-anchored replay showed zero certified switches.
No specification is selected for a favorable result.
"""
from pathlib import Path
from dataclasses import replace,asdict
import sys,json
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from empirical import prepare,read_official,evaluate,ROOT,Settings

def main():
    out=ROOT/'results/jkp_diagnostics';out.mkdir(exist_ok=True)
    raw=ROOT/'data/raw';panel,audit=prepare(raw);summaries=[];records=[]
    themes=read_official(raw/'all_themes.zip').reindex(panel.index)
    if themes.isna().any().any():raise ValueError('Theme panel contains gaps.')
    themes.insert(0,'core',panel.core)
    designs=[('factor_book',panel,Settings(core_weight=0.,satellite_weight=1.)),
             ('theme_book',themes,Settings(core_weight=0.,satellite_weight=1.)),
             ('theme_market_core',themes,Settings())]
    for name,p,cfg in designs:
        r,a,s=evaluate(p,cfg,cfg.fee,cfg.switch_cost)
        for row in r:row['design']=name
        for row in s:row['design']=name
        summaries.extend(s);records.extend(r)
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    pd.DataFrame(records).to_csv(out/'monthly.csv',index=False)
    (out/'manifest.json').write_text(json.dumps({'executed':True,'exploratory':True,
        'reason':'Architecture and multiplicity diagnostics added after zero-switch main replay; not confirmatory validation',
        'designs':[{'name':n,'m':p.shape[1]-1,'settings':asdict(c)} for n,p,c in designs]},indent=2))
    print(pd.DataFrame(summaries).to_string(index=False))
if __name__=='__main__':main()
