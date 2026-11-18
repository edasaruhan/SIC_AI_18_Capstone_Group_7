"""Create a project-local environment, verify the model and launch Streamlit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.venv'
LOCK = ROOT / 'requirements-lock.txt'


def installed_matches(python, expected, environment):
    code = '''import importlib.metadata as m, json, sys
try:
    correct = all(m.version(k) == v for k, v in json.loads(sys.argv[1]).items())
except m.PackageNotFoundError:
    correct = False
sys.exit(0 if correct else 1)
'''
    return subprocess.run([str(python), '-c', code, json.dumps(expected)],
                          cwd=ROOT, env=environment, check=False).returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup-only', action='store_true', help='Prepare and verify without starting a server')
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Python 3.12 is required. Install it and run the launcher again.')
    if not 1024 <= args.port <= 65535:
        raise ValueError('Choose a port between 1024 and 65535.')

    python = ENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        if ENV.exists():
            raise RuntimeError('An incomplete .venv already exists. Rename it before creating a new environment.')
        print('[1/4] Creating the local .venv with Python 3.12...', flush=True)
        venv.EnvBuilder(with_pip=True).create(ENV)
    else:
        print('[1/4] Using the local .venv.', flush=True)

    environment = os.environ.copy()
    environment['PYTHONNOUSERSITE'] = '1'
    environment.setdefault('PIP_CACHE_DIR', str(ENV / 'pip-cache'))
    subprocess.run([str(python), '-c',
                    'import sys; from pathlib import Path; '
                    'assert sys.version_info[:2] == (3, 12), "Existing .venv requires Python 3.12"; '
                    'assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(), "Incorrect virtual environment"', str(ENV)],
                   cwd=ROOT, env=environment, check=True)

    expected = dict(line.strip().split('==', 1) for line in LOCK.read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith('#'))
    marker = ENV / 'openplay-setup.json'
    digest = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    recorded = json.loads(marker.read_text()) if marker.exists() else {}
    if recorded.get('requirements_sha256') != digest or not installed_matches(python, expected, environment):
        print('[2/4] Installing pinned dependencies. Internet is required for this step...', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(LOCK)],
                       cwd=ROOT, env=environment, check=True)
    else:
        print('[2/4] Pinned dependencies are already installed; no download needed.', flush=True)

    print('[3/4] Checking dependencies and the saved research model...', flush=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], cwd=ROOT, env=environment, check=True)
    subprocess.run([str(python), '-c',
                    'from deployment.inference import ResearchModel; '
                    'model=ResearchModel(); '
                    '[model.predict(name) for name in ("example_a", "example_b", "example_c")]; '
                    'print("Saved model and all three synthetic scenarios verified.")'],
                   cwd=ROOT, env=environment, check=True)
    marker.write_text(json.dumps({'requirements_sha256': digest, 'python': '3.12'}, indent=2) + '\n')
    if args.setup_only:
        print('[4/4] Setup complete. The demo can now run without downloading data or retraining.', flush=True)
        return
    print(f'[4/4] Starting the demo at http://127.0.0.1:{args.port} . Stop with Ctrl+C.', flush=True)
    subprocess.run([str(python), '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
                    '--server.address', '127.0.0.1', '--server.port', str(args.port),
                    '--browser.gatherUsageStats', 'false'], cwd=ROOT, env=environment, check=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nDemo stopped.')
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Could not start the demo: {error}', file=sys.stderr)
        sys.exit(1)
