"""Storage scheduling controls; never starts a simulation or controller."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import maintain_final_storage as maintenance


@pytest.mark.parametrize('prefix,last,expected',[
    (0,0,None),(10,0,None),(40,0,None),(50,0,50),(90,50,None),
    (100,50,100),(500,490,500),(500,500,None)
])
def test_only_verified_fifty_market_increments_or_terminal_prefix(prefix,last,expected):
    assert maintenance.eligible_prefix(prefix,last)==expected


@pytest.mark.parametrize('prefix,last',[(30,50),(501,450),(50.5,0),(True,0)])
def test_invalid_or_backward_prefix_is_rejected(prefix,last):
    with pytest.raises(ValueError):maintenance.eligible_prefix(prefix,last)


def test_progress_requires_exact_final_stage_and_pool_size(tmp_path):
    assert maintenance.ready_prefix(tmp_path)==0
    path=tmp_path/'outputs/park_revive_full_v3/main/stage_progress.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dict(stage='pilot',requested_count=500,prefix_completed_and_replayed=50)))
    with pytest.raises(ValueError):maintenance.ready_prefix(tmp_path)
    path.write_text(json.dumps(dict(stage='main',requested_count=100,prefix_completed_and_replayed=50)))
    with pytest.raises(ValueError):maintenance.ready_prefix(tmp_path)
    path.write_text(json.dumps(dict(stage='main',requested_count=500,prefix_completed_and_replayed=50)))
    assert maintenance.ready_prefix(tmp_path)==50


def test_new_storage_record_uses_completed_main_prefix_only(tmp_path,monkeypatch):
    calls=[]
    def compress(root,stage,count,report,apply):
        calls.append((root,stage,count,report,apply));return {'complete':True}
    monkeypatch.setattr(maintenance.storage,'compress',compress)
    folder=tmp_path/'maintenance';folder.mkdir()
    assert maintenance.maintain_prefix(tmp_path,50,folder)=={'complete':True}
    assert calls==[(tmp_path,'main',50,folder/'main_050.json',True)]
