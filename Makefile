.PHONY: install
default: install

install: .venv/last-modified

.venv/last-modified:
	test -d .venv || virtualenv .venv --python=python3.9
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install maubot\[encryption\]
	touch .venv/last-modified
