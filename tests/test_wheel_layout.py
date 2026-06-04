"""SDK wheel must not bundle koraku_cloud (PyPI publish guard)."""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_sdk_wheel_excludes_koraku_cloud_package(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "build"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=root,
        check=True,
        capture_output=True,
    )
    wheels = list(dist.glob("koraku-*.whl"))
    assert wheels, "expected koraku wheel in dist/"
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    cloud_entries = [n for n in names if n.startswith("koraku_cloud/")]
    assert not cloud_entries, f"wheel must not contain koraku_cloud/: {cloud_entries[:5]}"
