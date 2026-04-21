install:              ## Install dependencies
	pip install -e ".[runtime,test]"

start:                ## Start LocalStack in host mode
	python3 -m localstack.runtime.main

test-transfer:        ## Run Transfer service tests
	pytest tests/aws/services/transfer/ -x -q

.PHONY: install start test-transfer
