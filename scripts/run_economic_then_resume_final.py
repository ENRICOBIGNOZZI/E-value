#!/usr/bin/env python3
"""Run the compact new study, then recover the terminal disk-guard failure.

No numerical sources, configurations, seed memberships, testing levels or
analysis rules of the original study are changed. Original failures remain
archived; worker count alone is reduced to contain memory/swap demand.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from continue_full_study import (
    exclusive_controller, refuse_existing_final_runner, sha256,
    validate_freezes, verified_seal, write_immutable,
)


def main():
    output = ROOT/'outputs/park_revive_full_v3'
    state_path = output/'recovery_status_20261018.json'
    state = dict(controller_pid=os.getpid(), source_sha256=sha256(Path(__file__)),
                 original_controller_pid=91419, recovery_workers=1,
                 original_guard_gib=2., original_scientific_settings_unchanged=True)
    env = dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')

    def update(phase, **values):
        state.update(phase=phase,updated_at=datetime.now(timezone.utc).isoformat(),**values)
        temporary=state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state,indent=2)+'\n')
        temporary.replace(state_path)

    def run(script, arguments, logfile, phase):
        with logfile.open('a') as stream:
            child=subprocess.Popen([sys.executable,str(ROOT/script),*map(str,arguments)],
                                   cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            update(phase, child_pid=child.pid,child_script=script,child_log=str(logfile))
            result=child.wait()
        if result:
            raise RuntimeError(f'{script} stopped with exit code {result}; see {logfile}')

    with exclusive_controller(output/'.continuation.lock'):
        try:
            validate_freezes(ROOT)
            refuse_existing_final_runner()
            run('extensions/economic_authorization/study.py',[],
                ROOT/'tmp/economic-authorization-v1.log','running_economic_authorization')
            result=json.loads((ROOT/'reports/economic_authorization_v1/status.json').read_text())
            if not result['complete'] or result['seed_pool']!=list(range(70001,70101)):
                raise RuntimeError('New simulation is not the declared complete pool')
            _,freeze,protocol=validate_freezes(ROOT)
            refuse_existing_final_runner()
            if shutil.disk_usage(ROOT).free<3*2**30:
                raise OSError('Recovery requires at least 3 GiB free before retry; original 2 GiB per-seed guard retained')
            audit=json.loads((ROOT/'reports/full_v3_recovery_20261018/storage_stop_audit.json').read_text())
            known={row['original']:row for row in audit['errors_archived']}
            actual={str(p.relative_to(ROOT)) for p in (output/'main').glob('seed_*/execution_error.txt')}
            if actual!=set(known):
                raise RuntimeError('Failure markers differ from the inspected disk-only failures')
            for original,row in known.items():
                if (sha256(ROOT/original)!=row['sha256']
                        or sha256(ROOT/row['archived'])!=row['sha256']):
                    raise RuntimeError('Archived error evidence differs')
            update('retrying_archived_disk_only_failures',free_bytes=shutil.disk_usage(ROOT).free,
                   removed_live_error_markers=list(known))
            for original in known:
                (ROOT/original).unlink()
            run('scripts/run_full_study.py',
                ['main','--count','500','--workers','1','--batch-size','10','--compact-verified-checkpoints'],
                ROOT/'tmp/full-v3-recovered-20261018.log','running_original_final_recovery')
            _,freeze,protocol=validate_freezes(ROOT)
            update('sealing_complete_final')
            snapshot=verified_seal(ROOT,'main',freeze,protocol)
            from audit_full_snapshot import audit as numeric_audit
            from assess_final_study import assess
            write_immutable(ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json',
                            numeric_audit(snapshot,output/'main'))
            write_immutable(ROOT/'reports/full_final_assessment.json',
                            assess(snapshot,ROOT/'reports/final_analysis_plan.json'))
            run('scripts/audit_full_event_adjudication.py',
                ['--snapshot',snapshot,'--output',output/'main','--report',
                 ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json'],
                ROOT/'tmp/full-v3-recovery-final-audits.log','auditing_final_events')
            for script in ['scripts/build_final_manuscript_results.py','scripts/build_final_diagnostics.py']:
                run(script,[],ROOT/'tmp/full-v3-recovery-final-audits.log','building_final_packets')
            update('final_audited_ready_for_manuscript',
                   scope='New economic study still requires independent replay/interpretation; original final manuscript synthesis and review remain.')
        except Exception as error:
            update('stopped_on_error',error=f'{type(error).__name__}: {error}')
            raise


if __name__=='__main__':
    main()
