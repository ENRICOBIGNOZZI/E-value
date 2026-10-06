"""Download only official public JKP monthly USA research data; verify TLS."""
from pathlib import Path
import urllib.request,hashlib,json,datetime
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'data/raw';out.mkdir(parents=True,exist_ok=True)
    base='https://jkpfactors-data.s3.amazonaws.com/public/'
    files={'availability.json':base+'availability.json'}
    for name in ['all_factors','mkt','all_themes']:
        files[name+'.zip']=base+'%5Busa%5D_%5B'+name+'%5D_%5Bmonthly%5D_%5Bvw_cap%5D.zip'
    entries=[]
    for name,url in files.items():
        with urllib.request.urlopen(url,timeout=120) as response:content=response.read()
        (out/name).write_bytes(content)
        entries.append({'name':name,'url':url,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
        print(name,len(content),'bytes')
    manifest={'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'license':'CC BY-NC 4.0; noncommercial research only',
        'citation':'Jensen, Kelly and Pedersen (2023), Journal of Finance 78(5), 2465-2518',
        'warning':'Official files can change; compare hashes to data/source_manifest_20261006.json before exact replication.',
        'files':entries}
    (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
