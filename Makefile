-include .env
export

publish:
	uv run python -m poetry config pypi-token.pypi ${PYPI_TOKEN}
	uv run python -m poetry publish --build

lint:
	uv run python -m pylint .

test:
	uv run python -m pytest tests

docs:
	uv run python -m mkdocs serve
