"""Run the read-only browser consumer's dependency-free Node contract tests.

Node >=20 is required for this optional web module's development/test toolchain.
No npm install, source transport, production workflow or model invocation.
"""
from pathlib import Path
import shutil
import os
import re
import subprocess


def test_workbench_reading_contracts():
    root = Path(__file__).resolve().parents[1]
    assert "--test-reporter" not in os.environ.get("NODE_OPTIONS", ""), (
        "Remove the temporary --test-reporter override from NODE_OPTIONS; "
        "this test selects TAP explicitly and does not change the parent environment"
    )
    node = shutil.which("node")
    assert node, "Node >=20 required for workbench web tests; missing tool is not PASS"
    version = subprocess.run([node, "--version"], capture_output=True, text=True,
                             check=True, timeout=10).stdout.strip()
    assert int(version.lstrip("v").split(".")[0]) >= 20
    for name in ("app.mjs", "reading.mjs", "presentation.mjs", "product.mjs"):
        syntax = subprocess.run([node, "--check", str(root / "workbench" / name)],
                                capture_output=True, text=True, timeout=10)
        assert syntax.returncode == 0, syntax.stdout + syntax.stderr
    result = subprocess.run([node, "--test", "--test-reporter=tap",
                             str(root / "workbench" / "reading.test.mjs"),
                             str(root / "workbench" / "environment.test.mjs"),
                             str(root / "workbench" / "app.test.mjs"),
                             str(root / "workbench" / "product.test.mjs")],
                            cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    # Node 23+ defaults to spec even with piped stdout. Select TAP explicitly.
    count = re.search(r"^# tests (\d+)$", result.stdout, re.MULTILINE)
    assert count and int(count.group(1)) > 0, "No browser contract cases executed"
    for field in ("fail", "cancelled", "skipped", "todo"):
        assert re.search(rf"^# {field} 0$", result.stdout, re.MULTILINE), result.stdout
