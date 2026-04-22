install:              ## Install dependencies
	pip install -e ".[runtime,test]"

start:                ## Start LocalStack in host mode
	python3 -m localstack.runtime.main

test-transfer:        ## Run Transfer service tests
	pytest tests/aws/services/transfer/ -x -q

clean:                ## Remove pyc files, .filesystem, .mypy_cache, and .egg-info
	find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -empty -delete
	rm -rf .filesystem localstack-core/.filesystem .mypy_cache
	find . -name "*.egg-info" -type d -exec rm -rf {} +

.PHONY: install start test-transfer clean
