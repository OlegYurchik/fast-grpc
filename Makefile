publish:


lint:
	pylint .

test:
	pytest tests

docs:
	python -m mkdocs serve
