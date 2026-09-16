"""
Filesystem layout, in one place so nothing has to guess at ../.. again.

Three directories, three different jobs:

  sources/  external inputs. The surveyed feed, and stage names fetched from
            OpenStreetMap. Never written by the app, only refreshed by tools.
  network/  what the app loads. Generated from sources by tools/extract.py,
            which rebuilds it from scratch - hand edits here do not survive.
  views/    generated for humans: the same network flattened into one row per
            route and per stage, for reading and checking in a spreadsheet.
            Nothing reads these back; delete them and nothing breaks.
"""
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BACKEND_DIR, "data")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
NETWORK_DIR = os.path.join(DATA_DIR, "network")
VIEWS_DIR = os.path.join(DATA_DIR, "views")

DIGITAL_MATATUS_ZIP = os.path.join(SOURCES_DIR, "digital_matatus_2015.zip")
OSM_STAGES_CSV = os.path.join(SOURCES_DIR, "osm_stages.csv")
