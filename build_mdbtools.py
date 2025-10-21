"""Build and bundle mdbtools binaries for Linux/macOS.

Follows official build guide: https://github.com/mdbtools/mdbtools
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
BIN_DIR = ROOT / "src" / "polars_access_mdbtools" / "bin"
if not BIN_DIR.is_dir():
    msg = f"Expected bin dir at {BIN_DIR}"
    raise RuntimeError(msg)

BUILD_DIR = ROOT / "build-mdbtools"
REPO_URL = "https://github.com/mdbtools/mdbtools.git"

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
    run(["git", "clone", "--depth=1", REPO_URL, str(BUILD_DIR)])

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

    # Generate configure script if building from git
    run(["autoreconf", "-i", "-f"], cwd=BUILD_DIR)

    # Configure
    configure_args = [
        "./configure",
        "--disable-glib",  # to avoid system GLib dependency
        "--disable-shared",
        "--enable-static",
    ]
    run(configure_args, cwd=BUILD_DIR, env=env)

    # Build
    run(["make", "-j"], cwd=BUILD_DIR)

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
