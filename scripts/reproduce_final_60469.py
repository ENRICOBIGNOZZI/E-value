"""Reproduce the numerically amended final market from training, not a checkpoint.

Uses the unchanged frozen learner and the declared exact-problem initialization.
Writes a new isolated tmp directory and runs the original independent replayer.
The continuation lock prevents concurrent production/fresh-market computation.
"""
import argparse
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src'), str(ROOT/'research')]
import numpy as np
from threadpoolctl import threadpool_limits
from continue_full_study import exclusive_controller, sha256, validate_freezes, write_immutable
from qp_initialization_60469 import (captured_problem, initialize_known_problem,
                                   problem_fingerprint, validate_iterates)
from park_revive.config import Config
from run_full_strategy import run_one

PROFILE_SHA256 = '41ca8a9d801729ce491d76e802c8147fb3d7170f131578e49e2d048ee5fb4fa8'


def destination(root, output):
    """Never reuse, resume, or write into a canonical study or source directory."""
    output = Path(output).resolve()
    temporary = (root/'tmp').resolve()
    if output == temporary or not output.is_relative_to(temporary):
        raise ValueError('Reproduction requires a new isolated directory under tmp/')
    if output.exists():
        raise ValueError('Reproduction destination already exists; choose a new directory')
    return output


def approved_profile(root, profile_path=None):
    folder = root/'reports/full_v3_recovery_20261018/qp_60469'
    path = Path(profile_path) if profile_path is not None else folder/'profile.json'
    if sha256(path) != PROFILE_SHA256:
        raise ValueError('Initialization profile differs from the disclosed amendment')
    profile = json.loads(path.read_text())
    for path, digest in [
        (root/'scripts/qp_initialization_60469.py', profile['initializer_sha256']),
        (root/'configs/full_main.json', profile['base_config_sha256']),
        (folder/'failed_problem.npz', profile['captured_problem_sha256']),
        (folder/'successful_iterates.npz', profile['successful_iterates_sha256']),
    ]:
        if sha256(path) != digest:
            raise ValueError('Declared initialization source/configuration/cache changed')
    with np.load(folder/'failed_problem.npz') as capture:
        problem = captured_problem(dict(capture), Config.read(root/'configs/full_main.json'))
    if problem_fingerprint(problem) != profile['known_problem_sha256']:
        raise ValueError('Captured problem differs from declared initialization')
    validate_iterates(problem, profile)
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    output = destination(ROOT, args.output)
    _, freeze, _ = validate_freezes(ROOT)
    profile = approved_profile(ROOT)
    if args.check_only:
        print(json.dumps(dict(complete=True, checks_only=True, output=str(output),
                             profile_sha256=PROFILE_SHA256,
                             scientific_source_hash=freeze['scientific_source_hash'])))
        return
    with exclusive_controller(ROOT/'outputs/park_revive_full_v3/.continuation.lock'):
        if shutil.disk_usage(ROOT).free < 2*2**30:
            raise OSError('Original 2 GiB disk reserve required before reproduction')
        output.mkdir(parents=True, exist_ok=False)
        record = dict(seed=60469, original_scientific_source_hash=freeze['scientific_source_hash'],
                      profile_sha256=PROFILE_SHA256, driver_sha256=sha256(Path(__file__)),
                      python=platform.python_version(), platform=platform.platform(),
                      numpy=np.__version__, checkpoint_loaded=False,
                      scope='Same declared final-market seed regenerated from the initial training year; '
                      'not a new independent replication. Exact-problem cached primal/dual initialization '
                      'is the disclosed post-freeze numerical supplement; statistical settings unchanged.')
        write_immutable(output/'reproduction_request.json', record)
        with threadpool_limits(limits=1), initialize_known_problem(profile) as calls:
            result = run_one((Config.read(ROOT/'configs/full_main.json'), 60469,
                              output, False, None, True, 2.))
        if not result.get('complete') or len(calls) != 1:
            raise RuntimeError('Fresh market did not complete with the exact declared initialization; outputs retained')
        metadata = dict(record, calls=calls, disclosure=profile['disclosure'],
                        intervention=profile['intervention'])
        write_immutable(output/'seed_60469/numerical_initialization.json', metadata)
        subprocess.run([sys.executable, str(ROOT/'scripts/verify_full_strategy.py'),
                        '--output', str(output), '--seeds', '60469'], check=True, cwd=ROOT)
        replays = json.loads((output/'arithmetic_verification.json').read_text())
        if len(replays) != 1 or not replays[0]['complete'] or replays[0]['seed'] != 60469:
            raise RuntimeError('Fresh market independent replay unresolved')
        validate_freezes(ROOT)
        write_immutable(output/'reproduction_verification.json', dict(
            record, complete=True, calls=calls, independent_replay=replays[0],
            initialized_problem_sha256=profile['known_problem_sha256']))


if __name__ == '__main__':
    main()
