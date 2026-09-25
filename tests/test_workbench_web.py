"""Run the read-only browser consumer's dependency-free Node contract tests.

Node >=20 is required for this optional web module's development/test toolchain.
No npm install, source transport, production workflow or model invocation.
"""
from pathlib import Path
import shutil
import re
import subprocess


def test_workbench_reading_contracts():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    assert node, "Node >=20 required for workbench web tests; missing tool is not PASS"
    version = subprocess.run([node, "--version"], capture_output=True, text=True,
                             check=True, timeout=10).stdout.strip()
    assert int(version.lstrip("v").split(".")[0]) >= 20
    for name in ("app.mjs", "reading.mjs"):
        syntax = subprocess.run([node, "--check", str(root / "workbench" / name)],
                                capture_output=True, text=True, timeout=10)
        assert syntax.returncode == 0, syntax.stdout + syntax.stderr
    result = subprocess.run([node, "--test", str(root / "workbench" / "reading.test.mjs")],
                            cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    count = re.search(r"# tests (\d+)", result.stdout)
    assert count and int(count.group(1)) > 0, "No browser contract cases executed"
    assert "# fail 0" in result.stdout
