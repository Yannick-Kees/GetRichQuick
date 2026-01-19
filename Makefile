REQUIREMENTS = requirements.txt
REGISTRY = registry.github.com
PYTHON_VERSION = $(shell cat .python-version)
DOCKERFILE = Dockerfile
TAG = $(shell date +"%Y%m%d_%H%M")
VENV = .venv/bin/activate

# Help message
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make install   - Create virtual environment and install requirements"
	@echo "  make run       - Run the script using the virtual environment"
	@echo "  make build     - Build the Docker container"
	@echo "  make clean     - Remove the virtual environment"
	@echo "  make help      - Display this help message"

# Default target
.PHONY: all
all: install


# Create conda environment and install requirements
install:
	@echo "Installing dependencies with uv..."
	@if ! command -v uv &> /dev/null; then \
		echo "uv is not installed. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@echo "Installing dependencies..."
	uv run uv pip install -e .


install-dev:
	@echo "Installing with development dependencies..."
	@if ! command -v uv &> /dev/null; then \
		echo "uv is not installed. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@echo "Installing dependencies with dev extras..."
	uv pip install -e ".[dev]"


# Run the script using the conda environment
.PHONY: run
run:
	uv run src/main.py


# Push to gitlab
# git remote add origin git@gitlab.de:group/project.git
# git remote remove origin
.PHONY: push
push:
	git init
	git add .
	git commit -m $(TAG)
	git push origin main
		

# Update requirements.txt using pipreqs
.PHONY: update
update:

format:
	@echo "Formatting code..."
	@find src -type f -name "*.py" -exec uvx reuse annotate --license MIT --copyright "Yannick Kees" {} +
	@uvx black src/
	@uvx ruff check src/ --fix
	@uvx isort src/
	@uvx docformatter --in-place --recursive src/
	@echo "Format complete!"

lint:
	@echo "Linting code with ruff..."
	@uvx ruff check src/ --select ALL --ignore T201,D203,D213
	@uvx codespell src/
	@echo "Lint check complete!"


# Add header and licence information
.PHONY: header
.header:
	@$(ACTIVATE_ENV) && python Tests/header.py


# Print git Stats
.PHONY: stats
stats:
	@echo "-- Conda Channels --"
	@conda config --show channels
	@echo "-- Current Branch --"
	@git branch --show-current
	@echo "-- Git Origin --"
	@git remote -v


# Build the Docker container
# docker build -t $(IMAGE_NAME) -f $(DOCKERFILE) .
.PHONY: build
build:
	@echo "Updating Container-Tag"
	@sed -i "s|image:.*|image: ${REGISTRY}:v${TAG}|" docker-compose.yaml


# Test via PyTest
.PHONY: test
test:
	uvx pytest


# Clean the virtual environment
.PHONY: clean
clean:
	@echo "Removing conda environment '$(ENV_NAME)' and cleaning up..."
	. $(shell conda info --base)/etc/profile.d/conda.sh && conda env remove -n $(ENV_NAME)