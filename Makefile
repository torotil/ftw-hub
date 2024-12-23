.PHONY: help bootstrap lint test requirements

VENV?=.venv
PYTHON?=python3
PYTHONNOUSERSITE?=1
TOUCH?=touch -d "+1 seconds"
PIP_SYNC=$(VENV)/bin/pip-sync
BUILD?=development

help:
	@echo
	@echo "make install         -- setup production environment"
	@echo
	@echo "make development     -- setup development environment"
	@echo "make test            -- run full test suite"
	@echo "make lint            -- run all linters on the code base"
	@echo
	@echo "make requirements    -- only compile the requirements*.txt files"
	@echo "make .venv           -- bootstrap the virtualenv."
	@echo

install: $(VENV)/.pip-installed-production

development: $(VENV)/.pip-installed-development .git/hooks/pre-commit

lint: $(BUILD)
	hatch fmt

test: $(BUILD)
	$(VENV)/bin/pytest

requirements: requirements.txt requirements-dev.txt

# Actual files/directories
################################################################################

requirements.txt: pyproject.toml $(PIP_SYNC)
	$(VENV)/bin/pip-compile -v --output-file=$@ --extra=hosting $<

requirements-dev.txt: pyproject.toml $(PIP_SYNC)
	$(VENV)/bin/pip-compile -v --output-file=$@ --extra=dev $<

# Create this directory as a symbolic link to an existing virtualenv, if you want to use that.
$(VENV):
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(TOUCH) $(VENV)

$(PIP_SYNC): $(VENV)
	PYTHONNOUSERSITE=$(PYTHONNOUSERSITE) $(VENV)/bin/pip install --upgrade pip pip-tools wheel && $(TOUCH) $@

$(VENV)/.pip-installed-production: requirements.txt $(PIP_SYNC)
	PYTHONNOUSERSITE=$(PYTHONNOUSERSITE) $(PIP_SYNC) $< && $(TOUCH) $@

$(VENV)/.pip-installed-development: requirements-dev.txt $(PIP_SYNC)
	PYTHONNOUSERSITE=$(PYTHONNOUSERSITE) $(PIP_SYNC) $< && $(TOUCH) $@

.git/hooks/pre-commit: $(VENV)
	$(VENV)/bin/pre-commit install
	$(TOUCH) .git/hooks/pre-commit
