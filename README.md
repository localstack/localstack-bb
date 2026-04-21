# LocalStack Framework Skeleton

Minimal host-mode-runnable framework skeleton of LocalStack, retaining the Transfer service as the reference provider.

## Start

```bash
pip install -e ".[runtime]"
python -m localstack.runtime.main
```

## Adding a new service provider

1. Create `localstack-core/localstack/services/<name>/provider.py` implementing the service API class.
2. Register it in `localstack-core/localstack/services/providers.py`.
3. Add the entry point to `plux.ini` under `[localstack.aws.provider]`.

Use `localstack/services/transfer/provider.py` as the reference implementation.

## Run Transfer tests

```bash
pytest tests/aws/services/transfer/ -x -q
```

## License

Copyright (c) 2017-2026 LocalStack maintainers and contributors.

This version of LocalStack is released under the Apache License, Version 2.0.
