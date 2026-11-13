"""Renders every example into a temporary folder and checks each SVG is well formed and not empty.

    python tests/test_examples.py
"""
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


def main():
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        runs = [("sigilant_scenes.py", d / "scenes"), ("sigilant_hero.py", d / "hero"),
                ("cisoai_case_study.py", d / "case.svg")]
        for script, out in runs:
            subprocess.run([sys.executable, str(EX / script), str(out)], check=True, cwd=EX,
                           capture_output=True)
        svgs = sorted(d.rglob("*.svg"))
        assert len(svgs) == 9, [p.name for p in svgs]
        for p in svgs:
            root = ET.parse(p).getroot()
            assert root.tag.endswith("svg"), p
            assert p.stat().st_size > 5000, p
        print(f"ok: {len(svgs)} SVGs")


if __name__ == "__main__":
    main()
