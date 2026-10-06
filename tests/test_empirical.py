"""Data-contract tests use tiny synthetic CSV fixtures, not empirical results."""
import sys,zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
from empirical import read_official

def archive(tmp_path,text):
    p=tmp_path/'fixture.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('fixture.csv',text)
    return p

def test_official_return_not_double_signed(tmp_path):
    p=archive(tmp_path,'location,name,freq,weighting,direction,date,ret\nusa,example,monthly,vw_cap,-1,2000-01-31,0.01\n')
    assert read_official(p).iloc[0,0]==.01

def test_duplicate_factor_month_rejected(tmp_path):
    row='usa,example,monthly,vw_cap,2000-01-31,0.01\n'
    p=archive(tmp_path,'location,name,freq,weighting,date,ret\n'+row+row)
    with pytest.raises(ValueError,match='Duplicate'):read_official(p)

def test_wrong_geography_rejected(tmp_path):
    p=archive(tmp_path,'location,name,freq,weighting,date,ret\ngbr,example,monthly,vw_cap,2000-01-31,0.01\n')
    with pytest.raises(ValueError,match='Wrong geography'):read_official(p)
