"""Keep routine compilation from silently reverting the financial evidence."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_paper as builder


@pytest.fixture
def manuscript(tmp_path,monkeypatch):
    (tmp_path/'paper/figures').mkdir(parents=True)
    (tmp_path/'scripts').mkdir()
    (tmp_path/'reports').mkdir()
    files={'paper/main.tex':b'current hundred-market source',
           'paper/generated_full_results.tex':b'current hundred-market pilot table',
           'paper/figures/full_strategy_paths.png':b'current sealed pilot figure',
           'reports/metrics.csv':b'preserved historical data'}
    for name,value in files.items():(tmp_path/name).write_bytes(value)
    monkeypatch.setattr(builder,'__file__',str(tmp_path/'scripts/build_paper.py'))
    monkeypatch.setattr(builder.shutil,'which',lambda name:'/fake/tectonic')
    return tmp_path,files


def unchanged(root,files):
    assert {name:(root/name).read_bytes() for name in files}==files


def test_default_build_compiles_current_sources_without_legacy_regeneration(manuscript,monkeypatch):
    root,files=manuscript;calls=[]
    def forbidden(*args,**kwargs):raise AssertionError('Default build entered legacy regeneration')
    monkeypatch.setattr(builder,'legacy_main',forbidden)
    monkeypatch.setattr(builder.subprocess,'run',lambda command,**kwargs:calls.append((command,kwargs)))
    builder.main([])
    assert calls==[(['/fake/tectonic','-X','compile','main.tex','--keep-logs'],dict(cwd=root/'paper',check=True))]
    unchanged(root,files)


@pytest.mark.parametrize('arguments',[['--full-pilot-count','10'],['--results','old'],['--full-results','old']])
def test_legacy_options_cannot_implicitly_replace_current_paper(manuscript,monkeypatch,arguments):
    root,files=manuscript
    monkeypatch.setattr(builder.subprocess,'run',lambda *a,**k:pytest.fail('Compilation started before argument validation'))
    with pytest.raises(SystemExit) as error:builder.main(arguments)
    assert error.value.code==2
    unchanged(root,files)


def test_explicit_legacy_mode_passes_its_options(monkeypatch):
    calls=[]
    monkeypatch.setattr(builder,'legacy_main',lambda argv:calls.append(argv))
    builder.main(['legacy','--full-pilot-count','10'])
    assert calls==[['--full-pilot-count','10']]


def test_failed_compilation_preserves_inputs_and_propagates_failure(manuscript,monkeypatch):
    root,files=manuscript
    def failure(command,**kwargs):raise subprocess.CalledProcessError(1,command)
    monkeypatch.setattr(builder.subprocess,'run',failure)
    with pytest.raises(subprocess.CalledProcessError):builder.main([])
    unchanged(root,files)


def test_missing_compiler_preserves_inputs(manuscript,monkeypatch):
    root,files=manuscript
    monkeypatch.setattr(builder.shutil,'which',lambda name:None)
    with pytest.raises(RuntimeError,match='Tectonic'):builder.main([])
    unchanged(root,files)


def test_help_does_not_compile_or_change_inputs(manuscript,monkeypatch):
    root,files=manuscript
    monkeypatch.setattr(builder.subprocess,'run',lambda *a,**k:pytest.fail('Help compiled the manuscript'))
    with pytest.raises(SystemExit) as error:builder.main(['--help'])
    assert error.value.code==0
    unchanged(root,files)
