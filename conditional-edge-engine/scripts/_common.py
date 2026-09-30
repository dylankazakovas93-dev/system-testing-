import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.trial_registry import Workspace  # noqa: E402


def workspace(arg: str | None) -> Workspace:
    return Workspace(Path(arg) if arg else ROOT).init()
