"""Runs generated tests in Docker (no network, limited CPU/memory). Falls back to local only if allowed."""
import shutil
import subprocess
import sys
from pathlib import Path

import config

PYTEST_ARGS = ["-m", "pytest", "-q", "-x", "--tb=short", "-p", "no:cacheprovider"]


def check_available() -> tuple[bool, str]:
    """Return (ok, message). Called BEFORE any tester call so no quota is wasted."""
    if shutil.which("docker"):
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=20)
        except Exception:  # noqa: BLE001
            r = None
        if r is not None and r.returncode == 0:
            return True, "docker"
        if config.ALLOW_LOCAL_EXEC:
            return True, "local"
        return False, ("Docker is installed but not running. Open Docker Desktop, wait until it says "
                       "'running', then press Retry. (No Docker? set ALLOW_LOCAL_EXEC=1 in .env.)")
    if config.ALLOW_LOCAL_EXEC:
        return True, "local"
    return False, ("Docker was not found. Install Docker Desktop and press Retry, or set "
                   "ALLOW_LOCAL_EXEC=1 in .env to run the generated tests on your own machine.")


def _ensure_image() -> str | None:
    check = subprocess.run(["docker", "image", "inspect", config.DOCKER_IMAGE], capture_output=True)
    if check.returncode == 0:
        return None
    build = subprocess.run(
        ["docker", "build", "-t", config.DOCKER_IMAGE, str(Path(__file__).parent)],
        capture_output=True, text=True,
    )
    return None if build.returncode == 0 else "Docker image build failed:\n" + build.stderr[-1500:]


def run_tests(project_dir: Path) -> dict:
    ok, mode = check_available()
    if not ok:
        return {"passed": False, "infra": True, "log": mode}

    if mode == "docker":
        err = _ensure_image()
        if err:
            return {"passed": False, "infra": True, "log": err}
        cmd = [
            "docker", "run", "--rm", "--network", "none", "--memory", "512m", "--cpus", "1",
            "-v", f"{project_dir.resolve()}:/app", "-w", "/app",
            config.DOCKER_IMAGE, "python", *PYTEST_ARGS,
        ]
        cwd = None
    else:  # local (user opted in)
        cmd, cwd = [sys.executable, *PYTEST_ARGS], str(project_dir)

    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=config.SANDBOX_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"passed": False, "log": f"Tests timed out after {config.SANDBOX_TIMEOUT}s."}
    return {"passed": p.returncode == 0, "log": (p.stdout + p.stderr)[-6000:]}
