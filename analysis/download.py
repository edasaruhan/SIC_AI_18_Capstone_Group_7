"""Download immutable upstream files; refuse replacement of a locked file."""
import hashlib
import json
import urllib.request
from .config import ROOT, DATA, RAW, COMMIT, prepare_dirs

FILES = {**{f"data/clean/{n}": DATA / n for n in
            ("survey_biweekly.csv.gz", "survey_intake.csv.gz", "steam.csv.gz")},
         **{n: ROOT / "docs/reference/provider" / n for n in
            ("codebook.xlsx", "data-process.qmd", "index.qmd", "LICENSE")},
         "R/helpers.R": ROOT / "docs/reference/provider/helpers.R"}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    prepare_dirs()
    lock_path = ROOT / "data/source_lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {"commit": COMMIT, "files": {}}
    if lock["commit"] != COMMIT:
        raise ValueError("Different commit in source lock")
    for upstream, local in FILES.items():
        old = lock["files"].get(upstream)
        if local.exists():
            digest = sha256(local)
            if old and old["sha256"] != digest:
                raise ValueError(f"Local checksum mismatch; preserved: {local.name}")
        else:
            temporary = local.with_suffix(local.suffix + ".download")
            try:
                with urllib.request.urlopen(RAW + upstream, timeout=90) as response, open(temporary, "wb") as out:
                    while chunk := response.read(1024 * 1024):
                        out.write(chunk)
                digest = sha256(temporary)
                if old and old["sha256"] != digest:
                    raise ValueError(f"Upstream checksum mismatch: {upstream}")
                temporary.replace(local)
            finally:
                temporary.unlink(missing_ok=True)
        lock["files"][upstream] = {"sha256": digest, "bytes": local.stat().st_size, "url": RAW + upstream}
        lock_path.write_text(json.dumps(lock, indent=2) + "\n")
        print(f"verified {local.name}: {digest}", flush=True)

if __name__ == "__main__":
    main()
