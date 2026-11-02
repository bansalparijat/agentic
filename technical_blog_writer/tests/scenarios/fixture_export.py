"""SYNTHETIC export boundary: exercise blog.export without a browser or network.

HTML/PDF here are test doubles, NOT real publication rendering. Never use this
adapter, its fake Google Doc URL, or fixture attestations for an actual article.
"""
import html
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import blog


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    if not (root / "outputs/data/SYNTHETIC-TEST-ONLY").is_file():
        raise SystemExit("Refusing export fixture outside an explicitly synthetic workspace")
    api = MagicMock()
    page = api.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
    page.pdf.side_effect = lambda **kwargs: Path(kwargs["path"]).write_bytes(b"%PDF-1.7\nSYNTHETIC TEST DOUBLE - NOT A RENDERED PUBLICATION\n")
    def markup(_root, text, title):
        return '<!doctype html><title>SYNTHETIC TEST DOUBLE</title><pre>' + html.escape(text) + '</pre>'
    with patch.object(blog, "render_html", side_effect=markup), patch.dict(sys.modules, {"playwright.sync_api": api}):
        blog.run(blog.parser().parse_args(["--root", str(root), "export"]))
    page.route.assert_called_once()
    page.pdf.assert_called_once()
