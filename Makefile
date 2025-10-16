PYTHON ?= python3

.PHONY: install download-models run run-web docker-build docker-run

install:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

download-models:
	$(PYTHON) scripts/download_models.py

run:
        $(PYTHON) app.py

run-web:
        $(PYTHON) web_app.py --host 0.0.0.0 --port 7860

docker-build:
	docker build -t openpdf2voice .

docker-run:
        docker run \
          --rm \
          -p 7860:7860 \
          -v "$$PWD/models:/models" \
          openpdf2voice python web_app.py --host 0.0.0.0 --port 7860
