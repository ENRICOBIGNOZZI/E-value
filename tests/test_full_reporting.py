"""Adversarial controls for excluding incomplete or altered research evidence."""
import copy
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from seal_full_snapshot import (METHODS, canonical_hash, requested_seeds,
                                sha256, validate_snapshot)
from verify_full_strategy import input_digest


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


@pytest.fixture
def evidence(tmp_path):
    """Tiny stand-in ledgers; never counted as financial simulation markets."""
    config = {'years': 3, 'label': 'fixture'}
    source = {'src/frozen.py': 'example source digest'}
    fingerprint = canonical_hash(source)
    verifier = tmp_path / 'verifier.py'
    verifier.write_text('# independent verifier fixture\n')
    output = tmp_path / 'pilot'
    output.mkdir()
    records = []
    for seed in (50001, 50002):
        directory = output / f'seed_{seed}'
        directory.mkdir()
        write_json(directory / 'status.json', dict(seed=seed, complete=True,
                   completed_blocks=2, total_blocks=2, source_hash=fingerprint))
        write_json(directory / 'config_frozen.json', config)
        write_json(directory / 'source_manifest.json', source)
        pd.DataFrame([dict(seed=seed, method=m) for m in sorted(METHODS)]).to_csv(
            directory / 'metrics_by_seed.csv', index=False)
        (directory / 'score.dat').write_bytes(b'original saved score data')
        records.append(dict(seed=seed, complete=True, checks=100,
            scientific_source_hash=fingerprint, config_hash=canonical_hash(config),
            verifier_sha256=sha256(verifier), input_digest=input_digest(directory)))
    write_json(output / 'arithmetic_verification.json', records)
    return output, [50001, 50002], fingerprint, config, verifier


def test_complete_evidence_keeps_exact_requested_membership(evidence):
    assert [r['seed'] for r in validate_snapshot(*evidence)] == [50001, 50002]
    # A later, unfinished market outside the named snapshot is not silently
    # included and does not invalidate an already complete prefix.
    (evidence[0] / 'seed_50003').mkdir()
    assert len(validate_snapshot(*evidence)) == 2
    with pytest.raises(ValueError, match='not finished'):
        validate_snapshot(evidence[0], [50001, 50002, 50003], *evidence[2:])


@pytest.mark.parametrize('change,reason', [
    ('incomplete', 'incomplete'), ('wrong_source', 'scientific source'),
    ('wrong_config', 'Configuration'), ('source_manifest', 'Source manifest'),
    ('no_replay', 'missing or stale'), ('stale_verifier', 'missing or stale'),
    ('stale_config_replay', 'missing or stale'), ('duplicate_replay', 'Duplicate'),
    ('changed_score', 'changed after'), ('execution_failure', 'execution error'),
    ('duplicate_method', 'method/market'), ('wrong_metric_seed', 'method/market')])
def test_changed_or_unverified_market_cannot_be_published(evidence, change, reason):
    output, seeds, source, config, verifier = evidence
    directory = output / 'seed_50002'
    status = json.loads((directory / 'status.json').read_text())
    records = json.loads((output / 'arithmetic_verification.json').read_text())
    if change == 'incomplete':
        status['complete'] = False
        write_json(directory / 'status.json', status)
    elif change == 'wrong_source':
        status['source_hash'] = 'other-version'
        write_json(directory / 'status.json', status)
    elif change == 'wrong_config':
        write_json(directory / 'config_frozen.json', {**config, 'label': 'changed'})
    elif change == 'source_manifest':
        write_json(directory / 'source_manifest.json', {'src/frozen.py': 'changed'})
    elif change == 'no_replay':
        records.pop()
    elif change == 'stale_verifier':
        verifier.write_text('# changed verifier\n')
    elif change == 'stale_config_replay':
        records[-1]['config_hash'] = 'old-config'
    elif change == 'duplicate_replay':
        records.append(copy.deepcopy(records[-1]))
    elif change == 'changed_score':
        (directory / 'score.dat').write_bytes(b'a changed saved score')
    elif change == 'execution_failure':
        (directory / 'execution_error.txt').write_text('failed')
    elif change in ('duplicate_method', 'wrong_metric_seed'):
        path = directory / 'metrics_by_seed.csv'
        frame = pd.read_csv(path)
        if change == 'duplicate_method':
            frame.loc[0, 'method'] = frame.loc[1, 'method']
        else:
            frame.loc[0, 'seed'] = 99999
        frame.to_csv(path, index=False)
        # Even a byte-current audit cannot make malformed method membership
        # acceptable to the reporting gate.
        records[-1]['input_digest'] = input_digest(directory)
    write_json(output / 'arithmetic_verification.json', records)
    with pytest.raises(ValueError, match=reason):
        validate_snapshot(output, seeds, source, config, verifier)


def test_final_report_cannot_select_favorable_or_incomplete_subset():
    freeze = {'pilot_pool': [50001, 50100], 'final_pool': [60001, 60500]}
    assert requested_seeds(freeze, 'pilot', 20) == list(range(50001, 50021))
    assert requested_seeds(freeze, 'main') == list(range(60001, 60501))
    with pytest.raises(ValueError, match='entire frozen final pool'):
        requested_seeds(freeze, 'main', 499)
    with pytest.raises(ValueError, match='outside'):
        requested_seeds(freeze, 'pilot', 101)
