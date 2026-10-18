"""Output isolation and disclosed-profile binding, without new market draws."""
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from reproduce_final_60469 import destination, approved_profile


def test_reproduction_refuses_canonical_outputs_and_workspace(tmp_path):
    root = tmp_path/'workspace'
    root.mkdir()
    for target in [root, root/'data/new', root/'paper/new',
                   root/'outputs/park_revive_full_v3/main', root/'tmp']:
        with pytest.raises(ValueError, match='isolated'):
            destination(root, target)
    assert not (root/'outputs').exists()


def test_reproduction_refuses_existing_output_without_mutation(tmp_path):
    root = tmp_path/'workspace'
    old = root/'tmp/retained'
    old.mkdir(parents=True)
    marker = old/'ledger'
    marker.write_bytes(b'preserved data')
    with pytest.raises(ValueError, match='already exists'):
        destination(root, old)
    assert marker.read_bytes() == b'preserved data'


def test_reproduction_refuses_symlink_escape(tmp_path):
    root = tmp_path/'workspace'
    (root/'tmp').mkdir(parents=True)
    protected = root/'data'
    protected.mkdir()
    (root/'tmp/link').symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError, match='isolated'):
        destination(root, root/'tmp/link/new')
    assert not (protected/'new').exists()


def test_readonly_destination_does_not_create_output(tmp_path):
    root = tmp_path/'workspace'
    target = root/'tmp/fresh'
    assert destination(root, target) == target.resolve()
    assert not target.exists()


def test_approved_disclosed_profile_passes_kkt_binding():
    profile = approved_profile(ROOT)
    assert profile['seed'] == 60469


def test_modified_initialization_refused_before_market_run(tmp_path):
    profile = json.loads((ROOT/'reports/full_v3_recovery_20261018/qp_60469/profile.json').read_text())
    profile['initial_x'][0] += .01
    altered = tmp_path/'altered.json'
    altered.write_text(json.dumps(profile))
    with pytest.raises(ValueError, match='disclosed amendment'):
        approved_profile(ROOT, altered)
