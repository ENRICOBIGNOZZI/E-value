"""Physical storage controls: no simulated markets and no changed logical bytes."""
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import compress_verified_json_storage as storage


@pytest.fixture
def source(tmp_path):
    path=tmp_path/'original.json';path.write_text('{"known": "immutable"}\n')
    staging=tmp_path/'staging';staging.mkdir()
    return path,staging


def smaller_copy(source,monkeypatch):
    original_inode=source.stat().st_ino
    monkeypatch.setattr(storage,'physical_bytes',
                        lambda p:10000 if p.stat().st_ino==original_inode else 100)


def test_atomic_smaller_copy_keeps_exact_bytes_timestamp_permissions(source,monkeypatch):
    path,staging=source;before=path.stat();contents=path.read_bytes()
    smaller_copy(path,monkeypatch)
    result=storage.compress_file(path,staging,copier=shutil.copy2)
    assert result['allocated_before']==10000 and result['allocated_after']==100
    assert path.read_bytes()==contents and path.stat().st_ino!=before.st_ino
    assert path.stat().st_mtime_ns==before.st_mtime_ns and path.stat().st_mode==before.st_mode
    assert not list(staging.iterdir())


def test_no_allocated_saving_leaves_original_inode(source):
    path,staging=source;before=path.stat().st_ino
    assert storage.compress_file(path,staging,copier=shutil.copy2) is None
    assert path.stat().st_ino==before and not list(staging.iterdir())


def test_corrupt_copy_never_replaces_source(source,monkeypatch):
    path,staging=source;before=path.read_bytes();inode=path.stat().st_ino
    smaller_copy(path,monkeypatch)
    def corrupt(src,dst):
        shutil.copy2(src,dst);dst.write_text('corrupt')
    with pytest.raises(ValueError,match='Byte'):
        storage.compress_file(path,staging,copier=corrupt)
    assert path.read_bytes()==before and path.stat().st_ino==inode and not list(staging.iterdir())


def test_concurrent_writer_is_detected_without_overwriting_its_update(source):
    path,staging=source
    def writer(src,dst):
        shutil.copy2(src,dst);src.write_text('new external writer')
    with pytest.raises(ValueError,match='Byte'):
        storage.compress_file(path,staging,copier=writer)
    assert path.read_text()=='new external writer' and not list(staging.iterdir())


def test_partial_copy_failure_preserves_source_and_removes_only_candidate(source):
    path,staging=source;before=path.read_bytes()
    def fail(src,dst):
        dst.write_text('partial');raise OSError('copy failed')
    with pytest.raises(OSError,match='copy failed'):
        storage.compress_file(path,staging,copier=fail)
    assert path.read_bytes()==before and not list(staging.iterdir())


def test_timestamp_loss_is_rejected(source,monkeypatch):
    path,staging=source;before=path.read_bytes()
    smaller_copy(path,monkeypatch)
    def bad_metadata(src,dst):
        shutil.copy2(src,dst)
        import os
        os.utime(dst,ns=(1,1))
    with pytest.raises(ValueError,match='timestamp'):
        storage.compress_file(path,staging,copier=bad_metadata)
    assert path.read_bytes()==before and not list(staging.iterdir())


def test_symlinks_and_preexisting_staging_are_not_replaced(source,tmp_path):
    path,staging=source;link=tmp_path/'link.json';link.symlink_to(path)
    with pytest.raises(ValueError,match='symlink'):
        storage.compress_file(link,staging,copier=shutil.copy2)
    (staging/'candidate').write_text('existing')
    with pytest.raises(ValueError,match='already exists'):
        storage.compress_file(path,staging,copier=shutil.copy2)
    assert (staging/'candidate').read_text()=='existing'


@pytest.fixture
def workflow(tmp_path,monkeypatch):
    directory=tmp_path/'outputs/park_revive_full_v3/pilot/seed_50001'
    directory.mkdir(parents=True)
    (directory/'large.json').write_text('{"large":"'+('repeated '*3000)+'"}')
    freeze=dict(pilot_pool=[50001,50100],final_pool=[60001,60500],
                pilot_config={'frozen':1},final_config={'frozen':2},scientific_source_hash='fixture-source')
    monkeypatch.setattr(storage,'validate_freezes',lambda root:({},freeze,None))
    calls=[]
    def validate(*args):
        calls.append(args)
        return [dict(seed=50001,input_digest='fixture-digest')]
    monkeypatch.setattr(storage,'validate_snapshot',validate)
    monkeypatch.setattr(storage.sys,'platform','darwin')
    return tmp_path,directory,calls


def test_dry_run_revalidates_twice_and_never_copies(workflow,monkeypatch):
    root,directory,calls=workflow;before=(directory/'large.json').read_bytes()
    def unexpected(*args,**kwargs):raise AssertionError('Dry run copied a file')
    monkeypatch.setattr(storage,'compress_file',unexpected)
    result=storage.compress(root,'pilot',1,root/'report.json')
    assert len(calls)==2 and result['all_current_input_digests_preserved']
    assert result['candidate_files']==1 and not result['applied']
    assert (directory/'large.json').read_bytes()==before


def test_stale_replay_rejected_before_copy_or_report(workflow,monkeypatch):
    root,directory,calls=workflow
    def stale(*args):raise ValueError('stale replay')
    monkeypatch.setattr(storage,'validate_snapshot',stale)
    with pytest.raises(ValueError,match='stale replay'):
        storage.compress(root,'pilot',1,root/'report.json',True)
    assert not (root/'report.json').exists()


def test_post_compression_fingerprint_drift_cannot_publish_success(workflow,monkeypatch):
    root,directory,calls=workflow
    def drift(*args):
        calls.append(args)
        return [dict(seed=50001,input_digest='first' if len(calls)==1 else 'changed')]
    monkeypatch.setattr(storage,'validate_snapshot',drift)
    monkeypatch.setattr(storage,'compress_file',lambda *args:None)
    with pytest.raises(ValueError,match='fingerprints changed'):
        storage.compress(root,'pilot',1,root/'report.json',True)
    assert len(calls)==2 and not (root/'report.json').exists()
    assert not list(directory.parent.parent.glob('.json-compression-*'))


@pytest.mark.parametrize('where',['evidence','paper','data','existing'])
def test_report_cannot_overwrite_evidence_or_existing_files(workflow,where):
    root,directory,calls=workflow
    report={'evidence':directory/'report.json','paper':root/'paper/report.json',
            'data':root/'data/report.json','existing':root/'existing.json'}[where]
    if where=='existing':report.write_text('existing')
    with pytest.raises(ValueError,match='Report must be new'):
        storage.compress(root,'pilot',1,report)
    assert not calls
    if where=='existing':assert report.read_text()=='existing'
