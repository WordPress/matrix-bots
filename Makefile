.PHONY: install
default: install

install: build .venv/last-modified

build:
	mkdir -p build

.venv/last-modified:
	test -d .venv || virtualenv .venv --python=python3.9
	.venv/bin/python -m pip install --upgrade pip maubot
	touch .venv/last-modified
