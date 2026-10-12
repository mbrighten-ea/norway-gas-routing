"""Small local file helpers for experiments, saved assessments and frozen evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

FIRST_SOLVE = 'archive/20261008-01_first-solve'
CLEANUP = 'archive/20261009-01_repository-cleanup'


def new_experiment(root, description, date=None):
    """Reserve a unique descriptive directory; never overwrite an experiment."""
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', description):
        raise ValueError('Use a short lowercase description of what changed or was tested')
    date = date or datetime.now(timezone.utc).strftime('%Y%m%d')
    if not re.fullmatch(r'\d{8}', date):
        raise ValueError('Date must be YYYYMMDD')
    runs = Path(root) / '.scratch/runs'
    runs.mkdir(parents=True, exist_ok=True)
    used = []
    for parent in (runs, Path(root) / 'archive'):
        if parent.exists():
            for path in parent.iterdir():
                match = re.match(rf'{date}-(\d+)_', path.name)
                if match:
                    used.append(int(match[1]))
    number = max(used, default=0) + 1
    while True:
        path = runs / f'{date}-{number:02d}_{description}'
        try:
            path.mkdir()
            return path
        except FileExistsError:
            number += 1


def first_solve_file(root, original):
    base = Path(root) / FIRST_SOLVE
    files = json.loads((base / 'manifest.json').read_text())['files']
    return base / files[str(original).replace('\\', '/')]['path']


def verify_first_solve(root):
    base = Path(root) / FIRST_SOLVE
    files = json.loads((base / 'manifest.json').read_text())['files']
    with zipfile.ZipFile(base / 'snapshot.zip') as snapshot:
        original = json.loads(snapshot.read('archive_sha256.json'))
        assert {key.replace('\\', '/'): value for key, value in original.items()} == {
            key: value['sha256'] for key, value in files.items()}
        for name, entry in files.items():
            data = (base / entry['path']).read_bytes() if 'path' in entry else snapshot.read(entry['zip_member'])
            assert hashlib.sha256(data).hexdigest() == entry['sha256'], name


def original_bytes(root, original):
    """Resolve historical identities without rewriting old manifests or raw data."""
    name = str(original).replace('\\', '/')
    if name.startswith('outputs/poc/'):
        return first_solve_file(root, name).read_bytes()
    if name.startswith('ea_legacy/'):
        return (Path(root) / 'data/raw/legacy' / name.removeprefix('ea_legacy/')).read_bytes()
    with zipfile.ZipFile(Path(root) / CLEANUP / 'snapshot.zip') as snapshot:
        return snapshot.read(name)


def publish_assessment(root, candidate, assessment):
    """Promote a checked complete candidate; preserve the previous result in scratch."""
    root, candidate = Path(root).resolve(), Path(candidate).resolve()
    if not candidate.is_relative_to(root / '.scratch/runs'):
        raise ValueError('Candidate must be a repository-local temporary experiment')
    if not re.fullmatch(r'[a-z][a-z0-9-]*', assessment):
        raise ValueError('Invalid assessment name')
    manifest = json.loads((candidate / 'provenance/run_manifest.json').read_text())
    if manifest.get('status') != 'OPTIMAL':
        raise ValueError('Incomplete/failed assessment cannot replace a successful result')
    for name in ('report.html', 'results.csv'):
        if not (candidate / name).is_file():
            raise ValueError(f'Candidate is missing {name}')
    from .evaluation import validate_manifest, validate_result_dates
    import pandas as pd
    validate_manifest(manifest)
    validate_result_dates(pd.read_csv(candidate / 'results.csv'), manifest)
    current = root / 'outputs' / assessment
    current.parent.mkdir(exist_ok=True)
    previous = None
    if current.exists():
        previous = new_experiment(root, 'replaced-' + assessment) / 'assessment'
        current.rename(previous)
    try:
        candidate.rename(current)
    except OSError:
        if previous is not None:
            previous.rename(current)
        raise
    return current
