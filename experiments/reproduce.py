"""One-command full replication. No live trading and no fabricated data fallback."""
from pathlib import Path
import subprocess,sys,argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
def run(*args):
    print('RUN',*args,flush=True);subprocess.run([sys.executable,*args],cwd=ROOT,check=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--download',action='store_true');ap.add_argument('--pdf',action='store_true');args=ap.parse_args()
    run('-m','pytest','-q')
    run('experiments/run.py','--name','main','--reps','200','--periods','1800','--noises','gaussian,student')
    run('experiments/run.py','--task','null','--name','null','--reps','2000','--periods','720','--m','5')
    run('experiments/run.py','--name','dependence','--reps','100','--periods','1200','--noises','garch,ar','--scenarios','revival,negative_hedge,positive_redundant,correlation_revival')
    for m in [20,50,100,150]:
        run('experiments/run.py','--name',f'scale_{m}','--reps','30','--periods','900','--m',str(m),'--noises','gaussian','--scenarios','correlation_revival','--methods','always_on,rolling_portfolio,e_restart')
    run('experiments/run.py','--name','weak_signal','--reps','200','--periods','720','--noises','gaussian','--scenarios','correlation_revival','--strength','.25')
    run('experiments/delay.py')
    if args.download:run('experiments/fetch_jkp.py')
    if not (ROOT/'data/raw/mkt.zip').exists():
        raise FileNotFoundError('Official JKP files absent. Rerun with --download or supply audited source archives. Simulations completed.')
    run('experiments/empirical.py');run('experiments/empirical_diagnostics.py');run('experiments/report.py')
    if args.pdf:
        if not shutil.which('pdflatex'):raise RuntimeError('Install a TeX distribution with pdflatex to build the manuscript.')
        for _ in range(2):subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/'paper',check=True)
if __name__=='__main__':main()
