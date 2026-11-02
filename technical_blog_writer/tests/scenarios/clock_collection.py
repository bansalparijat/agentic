"""Test-only deterministic clock; never sleeps, fetches sources or resets counters."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import collection

if __name__ == "__main__":
    root, clock = Path(sys.argv[1]).resolve(), float(sys.argv[2])
    if not (root / "outputs/data/SYNTHETIC-TEST-ONLY").is_file():
        raise SystemExit("Refusing simulated clock outside a synthetic workspace")
    try:
        with patch.object(collection.time, "time", return_value=clock):
            collection.run(collection.parser().parse_args(["--root", str(root), *sys.argv[3:]]))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
