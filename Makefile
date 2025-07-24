-include .env
export

publish:
	python -m poetry publish --build --username=${PYPI_USER} --password=${PYPI_PASSWORD}

lint:
	python -m pylint .

test:
	python -m pytest tests

docs:
	python -m mkdocs serve
