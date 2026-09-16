"""
Runs the whole data pipeline in order.

    python3 tools/build.py            # extract + export (offline, fast)
    python3 tools/build.py --network  # also refresh from OpenStreetMap

Stages, in order:

  1. extract.py       source zip -> data/network/*.csv      (offline)
  2. osm_stages.py    OSM stage list -> data/sources/       (network)
  3. osm_geometry.py  OSM route lines -> data/network/shapes.csv (network)
  4. export.py        human-readable CSVs -> data/views/    (offline)

Steps 2 and 3 hit Overpass, which is slow and sometimes down, so they're
opt-in. The offline path is enough to rebuild a working feed from source.
"""
import argparse
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(TOOLS)


def run(script: str) -> None:
    print(f"\n{'=' * 60}\n  {script}\n{'=' * 60}")
    result = subprocess.run([sys.executable, os.path.join(TOOLS, script)], cwd=BACKEND)
    if result.returncode != 0:
        raise SystemExit(f"{script} failed with exit code {result.returncode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", action="store_true",
                    help="also refresh stages and geometry from OpenStreetMap")
    args = ap.parse_args()

    run("extract.py")
    if args.network:
        run("osm_stages.py")
        run("osm_geometry.py")
    run("export.py")
    print("\nDone. Restart the backend to pick up the new feed.")


if __name__ == "__main__":
    main()
