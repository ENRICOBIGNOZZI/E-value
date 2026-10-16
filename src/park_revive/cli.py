import argparse
import hashlib
import json
import subprocess
import sys
import fcntl
from pathlib import Path
from threadpoolctl import threadpool_limits
from .config import Config
from .backtest import simulate_seed, atomic_json


def provenance(cfg,seeds,directory,stage):
    directory.mkdir(parents=True,exist_ok=True)
    config=directory/'config_frozen.json'
    if config.exists() and Config.read(config).digest!=cfg.digest:
        raise ValueError('Output directory already has a different frozen design')
    atomic_json(config,cfg.to_dict())
    seed_path=directory/'seed_manifest.json'
    existing=json.loads(seed_path.read_text()) if seed_path.exists() else {}
    all_seeds=sorted(set(existing.get('requested_seeds',[]))|set(seeds))
    atomic_json(seed_path,dict(stage=stage,requested_seeds=all_seeds,
        representative_seed=existing.get('representative_seed',min(seeds)),
        pools={'smoke':[101,102,103],'calibration':list(range(10001,10021)),
               'pilot':list(range(20001,20101)),'main':list(range(30001,30501))},
        streams={'market':11,'learner':'deterministic','conditional_MC_test':81001,'statistical_diagnostics':910001}))
    freeze=subprocess.check_output([sys.executable,'-m','pip','freeze']).decode()
    (directory/'environment.txt').write_text(f'Python {sys.version}\n'+freeze)
    git=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
    diff=subprocess.check_output(['git','diff','HEAD','--','src','configs','pyproject.toml'])
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src/park_revive').glob('*.py'))}
    atomic_json(directory/'provenance.json',dict(commit=git,working_tree_diff_sha256=hashlib.sha256(diff).hexdigest(),
        source_sha256=sources,config_sha256=cfg.digest))


def main():
    parser=argparse.ArgumentParser(description='PARK/REVIVE: theory and simulations only')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('simulate','resume'):
        p=commands.add_parser(name);p.add_argument('--config',required=True);p.add_argument('--output',required=True)
        p.add_argument('--seeds',type=int,nargs='+',required=True);p.add_argument('--stage',choices=['smoke','pilot','main'],required=True)
        p.add_argument('--stop-after-blocks',type=int)
    p=commands.add_parser('report');p.add_argument('--output',required=True)
    p=commands.add_parser('statistics');p.add_argument('--output',required=True);p.add_argument('--replications',type=int,default=10000)
    commands.add_parser('audit')
    args=parser.parse_args()
    with threadpool_limits(limits=1):
        if args.command in ('simulate','resume'):
            cfg=Config.read(args.config);directory=Path(args.output)
            pool={'smoke':set((101,102,103)),'pilot':set(range(20001,20101)),'main':set(range(30001,30501))}[args.stage]
            if not set(args.seeds)<=pool:raise ValueError('Use the preregistered disjoint stage seed pool')
            if args.stage!='smoke' and (cfg.n_assets,cfg.block,cfg.years)!=(500,252,15):
                raise ValueError('Pilot/main require full design dimensions')
            directory.mkdir(parents=True,exist_ok=True)
            with (directory/'.provenance.lock').open('w') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
                provenance(cfg,args.seeds,directory,args.stage)
            for seed in args.seeds:
                seed_directory=directory/f'seed_{seed}'
                try:
                    simulate_seed(cfg,seed,seed_directory,resume=args.command=='resume',stop_after_blocks=args.stop_after_blocks)
                except Exception as exc:
                    atomic_json(seed_directory/'failure.json',dict(seed=seed,status='failed',error_type=type(exc).__name__,message=str(exc)))
                    raise
        elif args.command=='report':
            from .reporting import report
            print(report(args.output).to_string())
        elif args.command=='statistics':
            from .experiments import statistical_study
            frame=statistical_study(args.output,args.replications)
            print(frame.groupby('delta').tail(1).to_string(index=False))
        else:
            root=Path.cwd();manifest=json.loads((root/'reports/data_preservation_manifest.json').read_text())
            for p in manifest['preserved']:
                record=next(r for r in manifest['files'] if r['path']==p)
                assert hashlib.sha256((root/p).read_bytes()).hexdigest()==record['sha256'],p
            print('Preserved input documentation and acquisition script: all SHA-256 checks pass. Raw archives absent. Empirical work disabled.')


if __name__=='__main__':main()
