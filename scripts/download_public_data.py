"""Download the pinned CC0 OpenNeuro T1w subset used by the public track."""

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "public_dataset.json"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "public")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_config(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def t1w_url(config, participant):
    relative = f"{participant}/anat/{participant}_T1w.nii"
    return f"{config['download_base'].rstrip('/')}/{relative}"


def download(url, destination, overwrite=False):
    if destination.exists() and not overwrite:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = parse_args()
    config = load_config(args.config)
    records = []
    for participant in config["participants"]:
        destination = args.output_dir / participant / "anat" / f"{participant}_T1w.nii"
        url = t1w_url(config, participant)
        changed = download(url, destination, args.overwrite)
        actual_sha256 = sha256(destination)
        expected_sha256 = config["sha256"][participant]
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Checksum mismatch for {participant}: expected {expected_sha256}, "
                f"received {actual_sha256}"
            )
        records.append(
            {
                "participant": participant,
                "source_url": url,
                "relative_path": str(destination.relative_to(args.output_dir)),
                "bytes": destination.stat().st_size,
                "sha256": actual_sha256,
            }
        )
        print(f"{'Downloaded' if changed else 'Present'}: {destination}")

    manifest = args.output_dir / "download_manifest.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote local manifest: {manifest}")


if __name__ == "__main__":
    main()
