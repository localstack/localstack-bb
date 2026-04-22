install:
	pip install -e ".[runtime,test]"

start:
	python3 -m localstack.runtime.main

test:
	pytest tests/

clean:
	find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -empty -delete
	rm -rf .filesystem localstack-core/.filesystem .mypy_cache
	rm requirements.txt

requirements.txt:
	uv pip compile pyproject.toml -o requirements.txt --extra runtime,test,dev

.PHONY: install start test clean
