#!/usr/bin/env python3
"""Retain the failed market and continue its identical QP from audited iterates."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'research')]
from continue_full_study import (
    exclusive_controller,process_identity,refuse_existing_final_runner,
    sha256,validate_freezes,verified_seal,write_immutable,
)
from qp_initialization_60469 import initialize_known_problem


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait-verifier-pid',type=int)
    args=parser.parse_args()
    output=ROOT/'outputs/park_revive_full_v3/main'
    folder=ROOT/'reports/full_v3_recovery_20261018/qp_60469'
    profile_path=folder/'profile.json';profile=json.loads(profile_path.read_text())
    state_path=output.parent/'qp_recovery_status_20261018.json'
    state=dict(controller_pid=os.getpid(),source_sha256=sha256(Path(__file__)),
               initialization_profile_sha256=sha256(profile_path),workers=1)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    log=ROOT/'tmp/full-v3-qp-recovery-20261018.log'
    def update(phase,**values):
        state.update(phase=phase,updated_at=datetime.now(timezone.utc).isoformat(),**values)
        temporary=state_path.with_suffix('.tmp');temporary.write_text(json.dumps(state,indent=2)+'\n')
        temporary.replace(state_path)
    def run(script,*arguments):
        with log.open('a') as stream:
            child=subprocess.Popen([sys.executable,str(ROOT/'scripts'/script),*map(str,arguments)],
                                   cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            update('running_'+script,child_pid=child.pid,child_script=script)
            code=child.wait()
        if code:raise RuntimeError(f'{script} stopped with {code}; see {log}')
    with exclusive_controller(output.parent/'.continuation.lock'):
        try:
            _,freeze,protocol=validate_freezes(ROOT)
            refuse_existing_final_runner()
            if args.wait_verifier_pid:
                identity=process_identity(args.wait_verifier_pid)
                if identity and 'verify_full_strategy.py' not in identity[-1]:
                    raise RuntimeError('Supplied verifier handle has another command')
                while identity and process_identity(args.wait_verifier_pid)==identity:
                    update('waiting_for_existing_completed_market_replay',
                           verifier_pid=args.wait_verifier_pid,verifier_identity=identity)
                    time.sleep(30)
            from seal_full_snapshot import validate_snapshot
            complete_seeds=[*range(60001,60469),60470]
            validate_snapshot(output,complete_seeds,freeze['scientific_source_hash'],
                              freeze['final_config'],ROOT/'scripts/verify_full_strategy.py')
            if sha256(ROOT/'scripts/qp_initialization_60469.py')!=profile['initializer_sha256']:
                raise RuntimeError('Initialization source differs from its audited profile')
            if sha256(ROOT/'configs/full_main.json')!=profile['base_config_sha256']:
                raise RuntimeError('Changed original configuration')
            seed_directory=output/'seed_60469'
            if sha256(seed_directory/'execution_error.txt')!=sha256(folder/'execution_error.txt'):
                raise RuntimeError('Live failure differs from its preserved record')
            failure=json.loads((folder/'failure_audit.json').read_text())
            if sha256(seed_directory/'checkpoint.pkl')!=failure['checkpoint_sha256']:
                raise RuntimeError('Failed annual checkpoint changed')
            (seed_directory/'execution_error.txt').unlink()
            update('recovering_exact_failed_qp',recovered_seed=60469,
                   numerical_amendment='Supplementary known-problem primal/dual initialization, declared after the final pool began; no objective, constraints, tolerances, iteration-budget or statistical changes.')
            from park_revive.config import Config
            from run_full_strategy import run_one
            with threadpool_limits(limits=1),initialize_known_problem(profile) as calls:
                result=run_one((Config.read(ROOT/'configs/full_main.json'),60469,output,True,None,True,2.))
            if not result.get('complete') or not calls:
                raise RuntimeError('Exact failed market did not complete with the audited initialization')
            record=dict(complete=True,seed=60469,base_scientific_source_hash=freeze['scientific_source_hash'],
                        initializer_profile=str(profile_path.relative_to(ROOT)),
                        initializer_profile_sha256=sha256(profile_path),
                        initializer_sha256=profile['initializer_sha256'],
                        driver_sha256=sha256(Path(__file__)),calls=calls,
                        disclosure=profile['disclosure'],intervention=profile['intervention'])
            write_immutable(seed_directory/'numerical_initialization.json',record)
            write_immutable(folder/'executed_initialization.json',record)
            run('verify_full_strategy.py','--output',output,'--seeds',60469,'--resume')
            run('compact_full_cache.py','--output',output,'--apply')
            for first in [60471,60481,60491]:
                validate_freezes(ROOT)
                run('run_full_strategy.py','--config',ROOT/'configs/full_main.json','--output',output,
                    '--start-seed',first,'--count',10,'--workers',1,'--resume')
                run('verify_full_strategy.py','--output',output,'--seeds',*range(first,first+10),'--resume')
                run('compact_full_cache.py','--output',output,'--apply')
                (output/'stage_progress.json').write_text(json.dumps(dict(
                    stage='main',requested_count=500,prefix_completed_and_replayed=first+9-60000,batch_size=10),indent=2)+'\n')
            run('build_full_results.py','--output',output,'--destination',ROOT/'reports/full_final_results',
                '--seeds',*range(60001,60501))
            (output/'stage_completion.json').write_text(json.dumps(dict(
                stage='main',requested_seeds=list(range(60001,60501)),all_complete=True,
                arithmetic_replay_complete=True),indent=2)+'\n')
            _,freeze,protocol=validate_freezes(ROOT)
            update('sealing_complete_final')
            snapshot=verified_seal(ROOT,'main',freeze,protocol)
            from audit_full_snapshot import audit
            from assess_final_study import assess
            write_immutable(ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json',audit(snapshot,output))
            write_immutable(ROOT/'reports/full_final_assessment.json',
                            assess(snapshot,ROOT/'reports/final_analysis_plan.json'))
            run('audit_full_event_adjudication.py','--snapshot',snapshot,'--output',output,
                '--report',ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json')
            run('build_final_manuscript_results.py')
            run('build_final_diagnostics.py')
            update('final_audited_ready_for_manuscript',
                   numerical_initialization_amendment=str((folder/'executed_initialization.json').relative_to(ROOT)))
        except Exception as error:
            update('stopped_on_error',error=f'{type(error).__name__}: {error}')
            raise


if __name__=='__main__':
    main()
