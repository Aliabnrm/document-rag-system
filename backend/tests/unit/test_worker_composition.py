import os
import subprocess
import sys
from pathlib import Path


def test_worker_entrypoint_loads_complete_resolvable_database_metadata() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    environment = {
        **os.environ,
        "PYTHONPATH": str(backend_root / "src"),
    }
    script = """
import app.entrypoints.worker
from app.platform.database.session import Database

table_names = {table.name for table in Database.metadata.sorted_tables}
assert "users" in table_names
assert "deletion_cleanup_jobs" in table_names
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
