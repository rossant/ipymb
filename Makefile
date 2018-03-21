VENV=venv/bin
PIP=$(VENV)/pip
PYTHON=$(VENV)/python

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-venv - remove Python virtual environment"
	@echo "python - create Python virtual environment and install all required packages"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "jupyter - run jupyter notebook in a virtual environment with ipymd"

clean: clean-build clean-pyc clean-venv

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-venv:
	rm -rf venv/

lint: | $(PYTHON)
	$(VENV)/flake8 ipymd setup.py --exclude=ipymd/ext/six.py,ipymd/core/contents_manager.py,ipymd/formats/tests/test_rmarkdown.py --ignore=E226,E265,F401,F403,F811

test: lint | $(PYTHON)
	$(PYTHON) setup.py test

jupyter: | $(PYTHON)
	./venv/bin/jupyter notebook --config=./.jupyter/jupyter_notebook_config.py

################################################################################
# Setup python virtual environment
################################################################################

.PHONY: python
python: $(PYTHON)

venv:
	virtualenv venv -p /usr/bin/python3

$(PIP): | venv
	$(PIP) install --upgrade pip

venv/.installed: requirements-dev.txt | venv
	$(PIP) install -Ur requirements-dev.txt
	$(PIP) install -e .
	$(PYTHON) -c 'import pypandoc; pypandoc.download_pandoc(version="1.19.1")'
	echo "pip install successful" > $@

$(PYTHON): | $(PIP) venv/.installed


