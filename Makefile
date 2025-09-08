-include .env
export

publish:
	python -m poetry config pypi-token.pypi ${PYPI_TOKEN}
	python -m poetry publish --build

lint:
	python -m pylint .

test:
	python -m pytest tests

docs:
	python -m mkdocs serve
