"""Reproduce the labeled first-twenty pilot graphics in a NEW destination."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import build_final_diagnostics as graphics
from continue_full_study import validate_freezes
from seal_full_snapshot import sha256, validate_snapshot


def reproduce(destination):
    if destination.exists():
        raise ValueError('Preview destination must not exist')
    snapshot = ROOT/'reports/full_v3_snapshots/pilot_020'
    output = ROOT/'outputs/park_revive_full_v3/pilot'
    if any(destination.resolve().is_relative_to(path.resolve())
           for path in (snapshot, output, ROOT/'paper')):
        raise ValueError('Preview cannot be written inside evidence or manuscript')
    _, freeze, _ = validate_freezes(ROOT)
    seal_path = snapshot/'snapshot_seal.json'
    seal = json.loads(seal_path.read_text())
    seeds = list(range(50001,50021))
    assert seal['seeds'] == seeds
    sealed_hash = sha256(seal_path)

    def check():
        assert sha256(seal_path) == sealed_hash
        for name, expected in seal['files_sha256'].items():
            path = (snapshot/name).resolve()
            assert path.is_relative_to(snapshot.resolve())
            assert sha256(path) == expected, name
        return validate_snapshot(output, seeds, freeze['scientific_source_hash'],
                                 freeze['pilot_config'], ROOT/'scripts/verify_full_strategy.py')

    before = check()
    paper_hash = sha256(ROOT/'paper/main.pdf')
    consumed = [output/f'seed_{seed}'/'runtime.csv' for seed in seeds]
    daily_path = output/'seed_50001/daily_ledger.parquet'
    consumed.append(daily_path)
    inputs = {str(path.relative_to(ROOT)):sha256(path) for path in consumed}
    data = graphics.prepare(
        pd.read_csv(snapshot/'metrics_by_seed.csv'),
        pd.read_csv(snapshot/'deployments.csv'),
        pd.read_csv(snapshot/'details/economic_opportunities.csv.gz'),
        pd.read_csv(snapshot/'opportunity_rates.csv'),
        pd.read_parquet(daily_path, columns=['seed','method','day','equity','n_active','support']),
        pd.concat([pd.read_csv(path) for path in consumed[:-1]],ignore_index=True),
        seeds, freeze['pilot_config'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    names = graphics.render(data,destination,'PILOT PREVIEW — 20 markets; representative seed 50001')
    assert before == check()
    assert paper_hash == sha256(ROOT/'paper/main.pdf')
    assert all(sha256(ROOT/path)==expected for path,expected in inputs.items())
    record = dict(complete=True,kind='sealed_pilot_graphics_preview',markets=20,seeds=seeds,
        representative_seed=50001,snapshot_seal_sha256=sealed_hash,
        raw_consumed_sha256=inputs,
        source_sha256={str(path.relative_to(ROOT)):sha256(path) for path in
            (Path(__file__),ROOT/'scripts/build_final_diagnostics.py',ROOT/'scripts/seal_full_snapshot.py')},
        outputs_sha256={path.name:sha256(path) for path in sorted(destination.iterdir()) if path.is_file()},
        paper_pdf_sha256=paper_hash,paper_pdf_unchanged=True,
        scope='Existing sealed twenty-market pilot outcomes only. No additional markets, arithmetic replay counts, final evidence, manuscript promotion or visual-QA claim.')
    (destination/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({key:value for key,value in record.items()
                      if key not in ('raw_consumed_sha256','outputs_sha256','seeds')},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    reproduce(parser.parse_args().destination)
