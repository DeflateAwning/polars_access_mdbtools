"""Build and bundle mdbtools binaries for Linux/macOS.

Follows official build guide: https://github.com/mdbtools/mdbtools
"""

import io
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).parent
BIN_DIR = ROOT / "src" / "polars_access_mdbtools" / "bin"
if not BIN_DIR.is_dir():
    msg = f"Expected bin dir at {BIN_DIR}"
    raise RuntimeError(msg)

BUILD_DIR = ROOT / "build-mdbtools"
RELEASE_ZIP_URL = (
    "https://github.com/mdbtools/mdbtools/releases/download/v1.0.1/mdbtools-1.0.1.zip"
)

TARGET_BINARIES = ["mdb-ver", "mdb-export", "mdb-schema", "mdb-tables"]


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """Run a command, printing it first."""
    print(f"[RUN] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def build_mdbtools() -> None:
    """Build mdbtools from source and copy binaries to package."""
    system = platform.system().lower()
    if system not in {"linux", "darwin"}:
        print(f"Skipping mdbtools build: unsupported platform {system}")
        return

    # Clean previous build
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    # Download latest release.
    with requests.get(RELEASE_ZIP_URL, stream=True, timeout=30) as r:
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zip_file:
            zip_file.extractall(BUILD_DIR)

    # Move extracted files up one level.
    extracted_subdir = BUILD_DIR / "mdbtools-1.0.1"
    for item in extracted_subdir.iterdir():
        shutil.move(str(item), BUILD_DIR)
    extracted_subdir.rmdir()

    env = os.environ.copy()
    env.setdefault("CFLAGS", "-O2")

    # Required by mdbtools build
    deps = [
        "autoconf",
        "automake",
        "libtool",
        "pkg-config",
        "bison",
        "flex",
        "gettext",
        "glib2.0-dev",
    ]
    print(f"Ensure build deps installed ({', '.join(deps)}).")

    if system == "darwin":
        # macOS specific env tweaks.
        # Ensure configure script is present.
        # Not present in GitHub files, but present in release zip.
        if not (BUILD_DIR / "configure").exists():
            msg = "Missing configure script after extraction."
            raise RuntimeError(msg)
        (BUILD_DIR / "configure").chmod(0o755)  # Make it executable.
        print("✅ configure script found.")

    elif system == "linux":
        run(["autoreconf", "-f", "-i"], cwd=BUILD_DIR, env=env)
        print("✅ autoreconf completed.")
    else:
        msg = f"Unsupported system: {system}"
        raise RuntimeError(msg)

    # Configure.
    configure_args = [
        "./configure",
        "--disable-glib",  # to avoid system GLib dependency
        "--disable-shared",
        "--disable-man",  # Disable manuals (otherwise it complains).
        "--enable-static",
    ]
    run(configure_args, cwd=BUILD_DIR, env=env)

    # Build.
    run(["make"], cwd=BUILD_DIR)

    # Locate binaries
    built_utils = BUILD_DIR / "src" / "util"
    if not built_utils.exists():
        msg = "Build succeeded but utilities not found at src/util"
        raise RuntimeError(msg)

    dest_dir = BIN_DIR / system
    dest_dir.mkdir(parents=True, exist_ok=True)

    for exe_name in TARGET_BINARIES:
        src = built_utils / exe_name
        if not src.exists():
            msg = f"Expected binary not found: {src}"
            raise FileNotFoundError(msg)
        dst = dest_dir / src.name
        shutil.copy2(src, dst)
        dst.chmod(0o755)
        print(f"Copied {src} -> {dst}")

    print(f"✅ mdbtools successfully built for {system}")


if __name__ == "__main__":
    build_mdbtools()
