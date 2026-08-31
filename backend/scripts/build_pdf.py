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
    python -m scripts.build_pdf ../docs/architecture.md --titre "Architecture"
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess  # nosec B404 - only fixed, local commands are run
import sys
import tempfile
from pathlib import Path

# Where Chrome usually sits on Windows and on Linux. CHROME_BIN wins when set.
CHEMINS_CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

FEUILLE_DE_STYLE = """
@page { size: A4; margin: 18mm 16mm; }

body {
  font-family: 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1f2933;
  margin: 0;
}

h1 { font-size: 20pt; color: #0d1b2a; margin: 0 0 0.4em; }
h2 {
  font-size: 14pt;
  color: #0d1b2a;
  margin-top: 1.6em;
  padding-bottom: 0.25em;
  border-bottom: 2px solid #c8a04b;
  break-after: avoid;
}
h3 { font-size: 11.5pt; color: #1b263b; margin-top: 1.2em; break-after: avoid; }
h4 { font-size: 10.5pt; color: #1b263b; break-after: avoid; }

p, li { orphans: 3; widows: 3; }

blockquote {
  margin: 0 0 1.2em;
  padding: 0.6em 1em;
  background: #f4f1ea;
  border-left: 3px solid #c8a04b;
  color: #4a5460;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.8em 0 1.2em;
  font-size: 9pt;
  break-inside: avoid;
}
th, td { border: 1px solid #e2ddd2; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #0d1b2a; color: #ffffff; font-weight: 600; }
tr:nth-child(even) td { background: #faf8f3; }

code {
  font-family: 'Cascadia Mono', Consolas, monospace;
  font-size: 9pt;
  background: #f4f1ea;
  padding: 1px 4px;
  border-radius: 3px;
}

pre.mermaid {
  break-inside: avoid;
  text-align: center;
  margin: 1.2em 0;
  background: none;
}

hr { border: 0; border-top: 1px solid #e2ddd2; margin: 1.8em 0; }
"""

GABARIT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{titre}</title>
<style>{style}</style>
</head>
<body>
{corps}
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
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


def markdown_vers_html(source: Path) -> str:
    """Convert the Markdown into an HTML fragment with Pandoc."""

    if shutil.which("pandoc") is None:
        raise SystemExit("Pandoc introuvable. Installe-le : https://pandoc.org/install.html")

    resultat = subprocess.run(  # nosec B603 B607 - fixed command, local file
        ["pandoc", "--from=gfm", "--to=html5", str(source)],
        capture_output=True,
        check=True,
    )
    corps = resultat.stdout.decode("utf-8")

    # Pandoc wraps a fenced block in <pre><code>. Mermaid wants the text
    # directly inside an element carrying the "mermaid" class.
    return re.sub(
        r'<pre class="mermaid"><code>(.*?)</code></pre>',
        lambda bloc: '<pre class="mermaid">' + bloc.group(1) + "</pre>",
        corps,
        flags=re.S,
    )


def html_vers_pdf(html: str, sortie: Path) -> None:
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
                # Laisse le temps à Mermaid de dessiner les schémas.
                "--virtual-time-budget=20000",
                f"--print-to-pdf={sortie}",
                page.as_uri(),
            ],
            capture_output=True,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convertit un document Markdown en PDF.")
    parser.add_argument("source", type=Path, help="fichier Markdown à convertir")
    parser.add_argument("--sortie", type=Path, help="fichier PDF produit (par défaut : même nom)")
    parser.add_argument("--titre", default=None, help="titre de la page HTML")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"Fichier introuvable : {source}")
    sortie = (args.sortie or source.with_suffix(".pdf")).resolve()

    print(f"Conversion de {source.name}...")
    corps = markdown_vers_html(source)
    html = GABARIT.format(titre=args.titre or source.stem, style=FEUILLE_DE_STYLE, corps=corps)
    html_vers_pdf(html, sortie)

    if not sortie.exists():
        raise SystemExit("La conversion a échoué : aucun PDF produit.")
    print(f"PDF écrit : {sortie} ({sortie.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    sys.exit(main())
