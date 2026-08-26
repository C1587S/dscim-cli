# format python files
format:
	uv run --group tests ruff format src tests

# lint python files, fixing what can be fixed
lint:
	uv run --group tests ruff check --fix src tests

# run tests
test:
	uv run --group tests pytest --color=yes tests

# run format, linting, testing checks
validate: format lint test
