TEST_PATH=./

.PHONY: clean-pyc
clean-pyc:
		find . -name '__pycache__' -type d -exec rm -r {} +
		find . -name '*.pyc' -exec rm --force {} +
		find . -name '*.pyo' -exec rm --force {} +
		find . -name '*~' -exec rm --force  {} +

.PHONY: clean-build
clean-build:
		rm --force --recursive build/
		rm --force --recursive dist/
		rm --force --recursive *.egg-info
		rm --force --recursive src/

lint:
		flake8 tools/ regseg/

.PHONY: test
test: clean-pyc
		py.test --ignore=src/ --verbose $(TEST_PATH)

dist: clean-build clean-pyc
		python setup.py sdist


.PHONY: release
release: clean-build clean-pyc
		python setup.py sdist
		twine upload dist/*
