"""Render a Markdown document as a paginated PDF.

The feasibility note is asked for as a document of eight to ten pages, so it has
to exist as a paginated file and not only as Markdown. The conversion happens in
two steps, with tools that are already on the machine:

    1. Pandoc turns the Markdown into an HTML fragment (tables included);
    2. Chrome, in headless mode, prints that HTML to PDF.

The Mermaid diagrams are drawn by the browser before printing, so the schemas
appear as pictures rather than as blocks of code.

Usage (from the ``backend/`` folder)::

    python -m scripts.build_pdf ../docs/feasibility_video_analysis.md
    python -m scripts.build_pdf ../docs/architecture.md --title "Architecture"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404 - only fixed, local commands are run
import sys
import tempfile
from pathlib import Path

from chess_coach.figure_style import PALETTE

# Where Chrome usually sits on Windows and on Linux. CHROME_BIN wins when set.
CHEMINS_CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

#: The document stylesheet, filled from the vendored palette.
#:
#: A PDF is read on paper and on a screen, and a printed page is the one surface where a
#: colour chosen by hand shows next to the figures of the same document. The nine values this
#: file used to write — a near-black blue for the headings, a sand for the quotations, an ochre
#: rule — belonged to nothing: they were not the palette, and they did not match the figures
#: the document embeds. Each one below is a token, and the day the palette moves this page
#: moves with it.
STYLESHEET = """
@page {{ size: A4; margin: 18mm 16mm; }}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: {ink};
  margin: 0;
}}

h1 {{ font-size: 20pt; color: {primary}; margin: 0 0 0.4em; }}
h2 {{
  font-size: 14pt;
  color: {primary};
  margin-top: 1.6em;
  padding-bottom: 0.25em;
  border-bottom: 2px solid {secondary};
  break-after: avoid;
}}
h3 {{ font-size: 11.5pt; color: {primary}; margin-top: 1.2em; break-after: avoid; }}
h4 {{ font-size: 10.5pt; color: {primary}; break-after: avoid; }}

p, li {{ orphans: 3; widows: 3; }}

blockquote {{
  margin: 0 0 1.2em;
  padding: 0.6em 1em;
  background: {surface};
  border-left: 3px solid {secondary};
  color: {muted};
}}

table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0.8em 0 1.2em;
  font-size: 9pt;
  break-inside: avoid;
}}
th, td {{ border: 1px solid {grid}; padding: 5px 8px; text-align: left; vertical-align: top; }}
th {{ background: {primary}; color: {paper}; font-weight: 600; }}
tr:nth-child(even) td {{ background: {surface}; }}

code {{
  font-family: 'Cascadia Mono', Consolas, monospace;
  font-size: 9pt;
  background: {surface};
  padding: 1px 4px;
  border-radius: 3px;
}}

pre.mermaid {{
  break-inside: avoid;
  text-align: center;
  margin: 1.2em 0;
  background: none;
}}

hr {{ border: 0; border-top: 1px solid {grid}; margin: 1.8em 0; }}
""".format(**PALETTE)

#: What Mermaid paints a diagram with. Left to itself it uses its own greys and lavenders,
#: which land beside figures drawn from the palette in the same document.
MERMAID_THEME = {
    "primaryColor": PALETTE["surface"],
    "primaryTextColor": PALETTE["ink"],
    "primaryBorderColor": PALETTE["primary"],
    "lineColor": PALETTE["muted"],
    "secondaryColor": PALETTE["paper"],
    "tertiaryColor": PALETTE["paper"],
    "fontFamily": "Segoe UI, system-ui, Helvetica, Arial, sans-serif",
}

TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
{body}
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'base', themeVariables: {theme} }});
</script>
</body>
</html>
"""


def trouver_chrome() -> str:
    """Return the path of a Chromium-based browser, or fail with a clear message."""

    candidats = [os.environ.get("CHROME_BIN", ""), *CHEMINS_CHROME]
    for chemin in candidats:
        if chemin and Path(chemin).exists():
            return chemin
    raise SystemExit("Chrome introuvable. Renseigne la variable CHROME_BIN.")


def markdown_to_html(source: Path) -> str:
    """Convert the Markdown into an HTML fragment with Pandoc."""

    if shutil.which("pandoc") is None:
        raise SystemExit("Pandoc introuvable. Installe-le : https://pandoc.org/install.html")

    resultat = subprocess.run(  # nosec B603 B607 - fixed command, local file
        ["pandoc", "--from=gfm", "--to=html5", str(source)],
        capture_output=True,
        check=True,
    )
    body = resultat.stdout.decode("utf-8")

    # Pandoc wraps a fenced block in <pre><code>. Mermaid wants the text
    # directly inside an element carrying the "mermaid" class.
    return re.sub(
        r'<pre class="mermaid"><code>(.*?)</code></pre>',
        lambda bloc: '<pre class="mermaid">' + bloc.group(1) + "</pre>",
        body,
        flags=re.S,
    )


def html_to_pdf(html: str, output: Path) -> None:
    """Print the HTML page to PDF with headless Chrome."""

    chrome = trouver_chrome()
    with tempfile.TemporaryDirectory() as dossier:
        page = Path(dossier) / "document.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(  # nosec B603 - fixed command, local files
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                # Give Mermaid time to draw the diagrams before printing.
                "--virtual-time-budget=20000",
                f"--print-to-pdf={output}",
                page.as_uri(),
            ],
            capture_output=True,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convertit un document Markdown en PDF.")
    parser.add_argument("source", type=Path, help="the Markdown file to convert")
    parser.add_argument("--output", type=Path, help="the PDF to write (default: the same name)")
    parser.add_argument("--title", default=None, help="title de la page HTML")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"File not found: {source}")
    output = (args.output or source.with_suffix(".pdf")).resolve()

    print(f"Converting {source.name}...")
    body = markdown_to_html(source)
    html = TEMPLATE.format(
        title=args.title or source.stem,
        style=STYLESHEET,
        body=body,
        theme=json.dumps(MERMAID_THEME),
    )
    html_to_pdf(html, output)

    if not output.exists():
        raise SystemExit("Conversion failed: no PDF was produced.")
    print(f"PDF written: {output} ({output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
