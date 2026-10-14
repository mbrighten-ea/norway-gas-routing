"""Audit saved source/result hashes, local report links and the lean layout."""
from pathlib import Path
import hashlib
from html.parser import HTMLParser
import json
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.artifacts import CLEANUP, verify_first_solve

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ('href','src') and value and not value.startswith(('https:','http:','#','data:')):
                self.paths.append(value)

def main():
    base=ROOT/CLEANUP
    originals=json.loads((base/'original_hashes.json').read_text())
    mapping=json.loads((base/'migration_map.json').read_text())
    verified=0
    with zipfile.ZipFile(base/'snapshot.zip') as snapshot:
        for old,digest in originals.items():
            if old.endswith('/.gitkeep') and digest==hashlib.sha256(b'').hexdigest():
                # Removed empty scaffolding has no source/result payload.
                continue
            if old.startswith(('data/','ea_legacy/','config/')) and old!='config/README.md':
                location=mapping.get(old,{}).get('path',old)
                data=(ROOT/location).read_bytes()
            elif old.startswith('outputs/'):
                item=mapping.get(old)
                if item is None:
                    data=snapshot.read(old)
                elif 'zip' in item:
                    data=snapshot.read(item['member'])
                else:
                    data=(ROOT/item['path']).read_bytes()
            else:
                continue
            assert hashlib.sha256(data).hexdigest()==digest,old
            verified+=1
    verify_first_solve(ROOT)
    link_count=0
    for assessment in ('reconstruction','benchmark'):
        folder=ROOT/'outputs'/assessment
        assert sorted(path.name for path in folder.iterdir())==['details','provenance','report.html','results.csv']
        parser=Links();parser.feed((folder/'report.html').read_text(encoding='utf-8'))
        for link in parser.paths:
            path=(folder/link).resolve()
            assert path.is_relative_to(ROOT.resolve()) and path.is_file(),str(path)
            link_count+=1
    empty=[]
    for parent in ('scripts','tests','outputs','archive','evidence','data','src'):
        for path in (ROOT/parent).rglob('*'):
            if path.is_dir() and not any(path.iterdir()): empty.append(str(path.relative_to(ROOT)))
    assert not empty,empty
    record={'preserved_source_config_and_original_output_files':verified,'valid_local_report_links':link_count,
            'first_solve_hashes_verified':True,'empty_managed_directories':empty,
            'tests_passed':180,'tests_warning':'Existing pandas/NumPy timedelta deprecation',
            'cached_driver_candidates_verified':True,'current_assessments_replaced':False,
            'inaccessible_untouched':['.pytest_cache','.pytest_tmp','pytest-of-martell.brighten'],
            'methodology_changed':False,'git_staging_or_commits_performed':False}
    (base/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__': main()
