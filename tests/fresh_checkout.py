"""Check a separate temporary source copy, without credentials or network."""
import os,shutil,subprocess,sys,tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='.checkout-check-',dir=root) as temporary:
    target=Path(temporary)
    for name in ('residentbench','experiments','evaluations','tests'):
        shutil.copytree(root/name,target/name,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('README.md','pyproject.toml','LICENSE'):
        shutil.copyfile(root/name,target/name)
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','OPENROUTER_API_KEY','OPENROUTER_ENV_FILE')}
    subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s','tests'],cwd=target,env=env,check=True)
    subprocess.run([sys.executable,'-X','utf8','-m','residentbench','summarize'],cwd=target,env=env,check=True)
print('Clean source checkout passed without key folder, private paths or network.')
