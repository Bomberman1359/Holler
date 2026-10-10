#!/bin/bash
# usage: tools/make_all.sh [quick]
cd "$(dirname "$0")/.."
set -e
python3 tools/make_terrain.py > /dev/null
if [ "$1" != "quick" ]; then
	python3 tools/make_textures.py
	python3 tools/make_trees.py
	python3 tools/make_film.py
	python3 tools/make_decals.py
	python3 tools/make_papers.py
	python3 tools/make_creatures.py
fi
python3 tools/make_sites.py
python3 tools/make_terrain.py > /dev/null
python3 tools/make_water.py
python3 tools/make_cover.py
if [ "$1" != "quick" ]; then
	python3 tools/make_audio.py
fi
echo "made"
