# LocalStack Minimal Framework — Specification (Latest)

## 1. Objective

Reduce the LocalStack codebase to the smallest possible surface that is still:

1. **Runnable in host mode** — `localstack start --host` reaches the `Ready.` state without errors.
2. **Functional with a real service** — the Transfer service is the only registered provider; its full API surface works correctly end-to-end.
3. **Extensible** — a developer can add a new service provider by following the Transfer service as a reference implementation: create a provider module, register it in `providers.py`, and it is immediately reachable via the gateway without touching any other file.

Every component not required to satisfy these three goals is removed, including components that were intentionally retained by the previous SPEC.md passes: the packages installer framework, the analytics/telemetry pipeline, the developer tooling directory, the full testing framework, the testing infrastructure in `localstack/testing/`, all Dockerfiles and container helpers, most CI configuration, and the deprecations module. Tests are stripped down to a single service's suite; that suite (Transfer) must be created as part of this work since none currently exists.

---

## 2. Scope

### 2.1 In Scope (retain)

| Area | Path | Rationale |
|------|------|-----------|
| AWS protocol gateway | `localstack/aws/` | Request parsing, dispatch, handlers, protocol, serving, spec — service-agnostic core |
| Service plugin system | `localstack/services/plugins.py` | Plugin registry and `@aws_provider()` decorator |
| Provider registry | `localstack/services/providers.py` | Single entry: `transfer`. Canonical registration point for new providers |
| Service scaffold | `localstack/services/edge.py`, `internal.py`, `moto.py`, `stores.py` | Router, health endpoints, moto adapter, state helpers |
| Transfer service | `localstack/services/transfer/` | Only service implementation; also the reference pattern |
| Transfer tests | `tests/aws/services/transfer/` (create), `tests/unit/services/transfer/` (create) | Created as part of this spec; the only retained test suite |
| ASF runtime | `localstack/runtime/` | Startup, shutdown, init scripts, hook system |
| HTTP layer | `localstack/http/` | ASGI/WSGI serving, routing, request/response |
| State & persistence | `localstack/state/` | StateContainer protocol, codecs, snapshot framework |
| Extension framework | `localstack/extensions/` | Public extension API |
| DNS | `localstack/dns/` | Framework-level DNS resolution |
| CLI | `localstack/cli/` | Package management CLI |
| Logging | `localstack/logging/` | Structured logging |
| Core modules | `localstack/plugins.py`, `version.py`, `py.typed` | Plugin entry point, version info |
| Configuration | `localstack/config.py` (pruned — see §4.8) | Framework-level variables only |
| Constants | `localstack/constants.py` (pruned — see §4.8) | Framework-level constants only |
| Essential utilities | `localstack/utils/` (partial — see §4.2) | Only modules imported by retained framework code |
| Testing framework (subset) | `localstack/testing/pytest/` (core: `__init__.py`, `markers.py`, `fixtures.py`, `bootstrap.py`, `container.py`) | Required by Transfer tests: `from localstack.testing.pytest import markers` and the `aws_client`, `snapshot`, `account_id` pytest fixtures |
| Transfer integration tests | `tests/aws/services/transfer/` | Already written; two classes (`TestTransferServer`, `TestTransferUser`) covering all five API operations plus error paths and snapshot verification |
| Build config | `pyproject.toml`, `plux.ini`, `requirements-*.txt` (pruned) | Build and plugin wiring |

### 2.2 Out of Scope (remove)

| Area | Path | Rationale |
|------|------|-----------|
| Package installer framework | `localstack/packages/` | No binary dependencies needed for the Transfer service or host-mode framework startup; the framework itself does not install packages |
| Developer tooling | `localstack/dev/` | Debugger plugin, run-configurators, Kubernetes helpers — none required in host mode |
| Testing framework (service-specific) | `localstack/testing/pytest/cloudformation/`, `localstack/testing/pytest/stepfunctions/`, `localstack/testing/scenario/`, `localstack/testing/testselection/`, `localstack/testing/config.py` | Service-specific test helpers with no Transfer consumers; the core `pytest/` modules (markers, fixtures, snapshot) are retained (see §2.1) |
| Analytics pipeline | `localstack/utils/analytics/` | Telemetry collection and publishing; no functional requirement for a minimal framework |
| Container utilities | `localstack/utils/container_utils/`, `utils/container_networking.py`, `utils/docker_utils.py` | Docker SDK wrappers; removed alongside Dockerfiles |
| X-Ray tracing | `localstack/utils/xray/` | Service-agnostic but unused by Transfer or framework core |
| Service catalog | `localstack/utils/catalog/` | Service catalog loader; no service-catalog consumers remain |
| TCP proxy | `localstack/utils/server/` | TCP proxy used only by removed services |
| Java utilities | `localstack/utils/java.py` | Companion to `packages/java.py`; removed with packages |
| Test utilities | `localstack/utils/testutil.py` | Test-support code; removed with testing framework |
| Deprecations module | `localstack/deprecations.py` | Tracks deprecated env vars for removed services; purpose disappears with those services |
| All non-Transfer tests | `tests/aws/` (except transfer/), `tests/unit/` (except services/transfer/), `tests/integration/`, `tests/bootstrap/`, `tests/performance/` | Only Transfer tests are kept |
| Dockerfiles & container scripts | `Dockerfile`, `Dockerfile.s3`, `docker-compose.yml`, `docker-compose-pro.yml`, `bin/docker-entrypoint.sh`, `bin/docker-helper.sh` | Host-mode only; no container artifacts produced |
| CI workflows | `.github/workflows/` (all), `.github/actions/` | No CI pipelines needed |
| Pre-commit hooks | `.pre-commit-config.yaml` | Developer tooling |
| Release scripts | `bin/release-dev.sh`, `bin/release-helper.sh`, `bin/localstack-supervisor`, `bin/hosts` | Release tooling |
| Utility scripts | `scripts/` | Ad-hoc tooling scripts |
| Documentation | `docs/`, `DOCKER.md`, `CODEOWNERS`, `CODE_OF_CONDUCT.md`, `AGENTS.md` | Non-essential prose |
| Remaining non-essential utils | (identified in §4.2) | Utils with zero retained-code callers |

---

## 3. Constraints

1. **Host-mode startup is non-negotiable.** `localstack start --host` must reach `Ready.` with no import errors, no missing module crashes, and no uncaught exceptions during startup hooks.

2. **Transfer service must be fully functional.** All five operations (`CreateServer`, `DescribeServer`, `CreateUser`, `ListUsers`, `DeleteUser`) must produce correct responses as exercised by the Transfer test suite.

3. **Provider registration pattern must remain intact.** The `@aws_provider()` decorator in `services/plugins.py`, the factory-function convention in `services/providers.py`, and the `Service.for_provider()` wiring must work without modification. Transfer is the reference; adding a second service must require only: (a) a new `services/<name>/provider.py`, and (b) a new factory function in `providers.py`.

4. **No Docker runtime dependency.** After removal, no retained Python module may import from `docker`, `localstack.utils.container_utils`, or `localstack.utils.docker_utils` at module level. Imports that are gated behind a runtime condition (e.g., `if CONTAINER_RUNTIME`) may remain if the code path is unreachable in host mode, but are preferred removed.

5. **plux namespaces must stay.** Sections `[localstack.aws.provider]`, `[localstack.cloudformation.resource_providers]`, and `[localstack.lambda.runtime_executor]` must remain in `plux.ini` (empty) so downstream packages can inject into them without code changes.

6. **No circular imports introduced.** Each removal must be checked for import-graph side effects before committing.

7. **Transfer tests are authoritative.** If a removal breaks a Transfer test, the removal is out of scope or requires a compensating fix. Transfer tests must pass with `pytest tests/aws/services/transfer/ tests/unit/services/transfer/ -x -q` before and after each phase.

---

## 4. Component Inventory

### 4.1 services/ Directory

```
localstack/services/
├── plugins.py       KEEP — plugin registry and @aws_provider() decorator
├── providers.py     KEEP — single entry: transfer() factory function; all others already removed
├── edge.py          KEEP — edge router
├── internal.py      KEEP — health/ready/info endpoints
├── moto.py          KEEP — moto adapter scaffold for new providers
├── stores.py        KEEP — AccountRegionBundle, BackendDict, CrossAccountAttribute
└── transfer/        KEEP — only service implementation
    ├── __init__.py
    ├── models.py
    └── provider.py
```

### 4.2 utils/ Directory

Disposition by module:

| Path | Action | Reason |
|------|--------|--------|
| `utils/analytics/` | **REMOVE** | Entire telemetry pipeline; plux.ini hooks also removed (§4.7) |
| `utils/container_utils/` | **REMOVE** | Docker SDK wrappers; no retained code depends on these |
| `utils/container_networking.py` | **REMOVE** | Container network setup; host-mode only |
| `utils/docker_utils.py` | **REMOVE** | Docker subprocess utilities; removed with container tooling |
| `utils/xray/` | **REMOVE** | X-Ray tracing helpers; no retained callers |
| `utils/catalog/` | **REMOVE** | Service catalog; plux.ini entry also removed |
| `utils/server/` | **REMOVE** | TCP proxy; no retained callers |
| `utils/java.py` | **REMOVE** | Java process launcher; companion to packages/java.py |
| `utils/testutil.py` | **REMOVE** | Test utilities; removed with testing framework |
| `utils/diagnose.py` | **AUDIT** | Diagnostic dump tool; remove if no retained callers |
| `utils/scheduler.py` | **AUDIT** | Recurring job scheduler; remove if no retained callers after service removal |
| `utils/serving.py` | **AUDIT** | HTTP server helpers; remove if superseded by http/ layer |
| `utils/config_listener.py` | **AUDIT** | Config-change listener; remove if no retained callers |
| `utils/event_matcher.py` | **AUDIT** | Event pattern matching; remove if no retained callers |
| `utils/tagging.py` | **AUDIT** | AWS resource tagging helpers; remove if no Transfer or framework callers |
| All others in `utils/` | **KEEP** | Networking, crypto, JSON, XML, HTTP, collections, strings, files, sync, threads, auth, bootstrap, patch, objects, functions, time, numbers, ip_utils, ssl, platform, venv, run, urls, asyncio, async_utils, backoff, batching, checksum, id_generator, no_exit_argument_parser, openapi |
| `utils/aws/arns.py` | **KEEP** | ARN parsing used by framework |
| `utils/aws/aws_stack.py` | **KEEP** | AWS stack utilities used by framework |
| `utils/aws/client.py` | **KEEP** | Internal boto3 client factory |
| `utils/aws/client_types.py` | **KEEP** | Client type definitions |
| `utils/aws/request_context.py` | **KEEP** | Request context propagation |
| `utils/aws/resources.py` | **KEEP** | Resource utilities used by framework |

> **AUDIT** items must be resolved via `grep -r "from localstack.utils.<module>" localstack/ --include="*.py"` against the retained codebase. If zero retained callers exist, remove; if callers exist in removed code only, remove; if callers exist in retained code, keep.

### 4.3 packages/ Directory

```
localstack/packages/    REMOVE ENTIRELY
```

All files (`api.py`, `core.py`, `plugins.py`, `java.py`, `ffmpeg.py`, `debugpy.py`, `__init__.py`) are removed. The package installer framework is not needed when the only service (Transfer) has no binary dependencies.

Update `pyproject.toml` to remove the `localstack.packages` entry-point group and any associated package metadata.

### 4.4 dev/ Directory

```
localstack/dev/    REMOVE ENTIRELY
```

Includes: `debugger/plugins.py`, `run/` (configurators, watcher, paths), `kubernetes/__main__.py`. The `conditionally_enable_debugger` plux.ini hook must also be removed (§4.7).

### 4.5 testing/ Directory

The Transfer integration tests import `from localstack.testing.pytest import markers` and rely on the `aws_client`, `snapshot`, and `account_id` pytest fixtures. The core `pytest/` package must therefore be retained; only the service-specific sub-packages are removed.

```
localstack/testing/
├── pytest/
│   ├── __init__.py          KEEP — exports markers; imported directly by test files
│   ├── markers.py           KEEP — @markers.aws.validated, @markers.snapshot.skip_snapshot_verify
│   ├── fixtures.py          KEEP — aws_client, snapshot, account_id fixtures
│   ├── bootstrap.py         KEEP — fixture dependencies
│   ├── container.py         KEEP — fixture dependencies
│   ├── path_filter.py       REMOVE — CI-only --path-filter plugin; depends on testselection/
│   ├── cloudformation/      REMOVE — no Transfer consumers
│   └── stepfunctions/       REMOVE — no Transfer consumers
├── scenario/                REMOVE — no Transfer consumers
├── testselection/           REMOVE — only caller was path_filter.py (also removed)
└── config.py                KEEP — imported by fixtures.py, in_memory_localstack.py, testutil.py, testing/aws/util.py
```

After removing the sub-packages, verify:
```bash
python -c "from localstack.testing.pytest import markers; print('markers OK')"
pytest tests/aws/services/transfer/ --collect-only -q
```

### 4.6 tests/ Directory

```
tests/
├── aws/
│   ├── services/
│   │   ├── transfer/    KEEP — integration tests already written (TestTransferServer, TestTransferUser)
│   │   └── <all others> REMOVE
│   ├── conftest.py      KEEP — provides aws_client, snapshot, account_id fixtures via localstack.testing.pytest
│   ├── files/           REMOVE
│   ├── scenario/        REMOVE
│   ├── serverless/      REMOVE
│   ├── templates/       REMOVE
│   ├── terraform/       REMOVE
│   └── cdk_templates/   REMOVE
│   └── test_*.py        REMOVE (all top-level aws test files)
├── unit/                REMOVE ENTIRELY — no unit tests exist or are being created
├── integration/         REMOVE ENTIRELY
├── bootstrap/           REMOVE ENTIRELY
└── performance/         REMOVE ENTIRELY
```

The `tests/aws/conftest.py` provides the fixtures the Transfer tests depend on (`aws_client`, `snapshot`, `account_id`). Inspect it before removal and retain only the fixtures consumed by Transfer tests; remove any fixture definitions that import from deleted service modules.

### 4.7 Top-Level / Tooling Files

| File | Action |
|------|--------|
| `Dockerfile` | **REMOVE** |
| `Dockerfile.s3` | **REMOVE** |
| `docker-compose.yml` | **REMOVE** |
| `docker-compose-pro.yml` | **REMOVE** |
| `bin/docker-entrypoint.sh` | **REMOVE** |
| `bin/docker-helper.sh` | **REMOVE** |
| `bin/release-dev.sh` | **REMOVE** |
| `bin/release-helper.sh` | **REMOVE** |
| `bin/localstack-supervisor` | **REMOVE** |
| `bin/hosts` | **REMOVE** |
| `.github/` | **REMOVE** (entire directory) |
| `.pre-commit-config.yaml` | **REMOVE** |
| `scripts/` | **REMOVE** (entire directory) |
| `docs/` | **REMOVE** |
| `DOCKER.md` | **REMOVE** |
| `CODEOWNERS` | **REMOVE** |
| `CODE_OF_CONDUCT.md` | **REMOVE** |
| `AGENTS.md` | **REMOVE** |
| `MANIFEST.in` | **AUDIT** — remove if package build no longer needs it |
| `Makefile` | **REDUCE** — keep only: `install`, `start`, `test-transfer` targets; remove all Docker, CI, and service-specific targets |
| `mypy.ini` | **KEEP** (optional; simplify if kept) |
| `pyproject.toml` | **PRUNE** (see §4.9) |
| `plux.ini` | **PRUNE** (see §4.8) |
| `requirements-*.txt` | **PRUNE** (keep runtime only; remove entries for deleted packages) |
| `README.md` | **REDUCE** — replace with a minimal framework + provider guide |
| `LICENSE.txt` | **KEEP** |
| `uv.lock` | **KEEP** (regenerate after dependency changes) |

### 4.8 plux.ini — Hook and Entry Disposition

| Entry | Action | Reason |
|-------|--------|--------|
| `[localstack.aws.provider]` | KEEP (empty) | Downstream packages inject here |
| `[localstack.cloudformation.resource_providers]` | KEEP (empty) | Downstream packages inject here |
| `[localstack.lambda.runtime_executor]` | KEEP (empty) | Downstream packages inject here |
| `[localstack.hooks.configure_localstack_container]` → `_mount_machine_file` | **REMOVE** | Module `utils/analytics/metadata.py` deleted |
| `[localstack.hooks.prepare_host]` → `prepare_host_machine_id` | **REMOVE** | Module `utils/analytics/metadata.py` deleted |
| `[localstack.hooks.on_infra_start]` → `_publish_config_as_analytics_event` | **REMOVE** | Module `runtime/analytics.py` — audit; remove if analytics-only |
| `[localstack.hooks.on_infra_start]` → `conditionally_enable_debugger` | **REMOVE** | Module `dev/debugger/plugins.py` deleted |
| `[localstack.hooks.on_infra_shutdown]` → `publish_metrics` | **REMOVE** | Module `utils/analytics/metrics/publisher.py` deleted |
| `[localstack.packages]` → `ffmpeg/community`, `java/community` | **REMOVE** | Module `packages/plugins.py` deleted |
| `[localstack.utils.catalog]` → both entries | **REMOVE** | Module `utils/catalog/catalog.py` deleted |
| All other `[localstack.hooks.*]` entries | **KEEP** | Framework lifecycle hooks (init scripts, DNS, shutdown, botocore patches, swagger, etc.) |
| `[localstack.init.runner]` | **KEEP** | Python and shell init runners |
| `[localstack.openapi.spec]` | **KEEP** | OpenAPI spec plugin |
| `[localstack.runtime.components]` | **KEEP** | AWS components registration |
| `[localstack.runtime.server]` | **KEEP** | Hypercorn and Twisted server backends |

After editing, validate with:
```bash
python -c "import plux; print(plux.PluginManager('localstack.aws.provider').load_all())"
# Expected: [<TransferProvider>]
```

### 4.9 pyproject.toml — Dependency Disposition

**Remove from `[project.optional-dependencies]` / dependency groups:**

| Package | Reason |
|---------|--------|
| `docker` | Container utilities deleted |
| Any analytics-specific packages | Analytics pipeline deleted; verify via `grep -r "import <pkg>" localstack/utils/analytics/` |
| `debugpy` | Debugger deleted with `dev/` |
| Type-stub extras (`boto3-stubs[...]`) | Reduce to only services still in use |

**Retain (verified framework usage):**

| Package | Framework usage |
|---------|----------------|
| `plux` | Plugin system |
| `boto3` / `botocore` | Protocol layer, internal client factory |
| `pydantic` | Request/response validation |
| `werkzeug` | HTTP utilities |
| `hypercorn` | ASGI server |
| `localstack-twisted` | Twisted server backend |
| `openapi-core` | OpenAPI validation |
| `jsonschema` | Protocol validation |
| `rolo` | HTTP routing |
| `cryptography` | `utils/crypto.py` |
| `moto-ext` | `services/moto.py` adapter scaffold |
| `requests` / `urllib3` | HTTP client utilities |
| `pyyaml` | Config and spec parsing |
| `click` | CLI |

**Remove entry-point group `[project.entry-points."localstack.packages"]`** if present.

**Remove `ruff` exclude paths and `deptry` ignore entries** for deleted modules.

### 4.10 config.py / constants.py / deprecations.py

**`localstack/deprecations.py` — REMOVE ENTIRELY.**  
The module tracked deprecated env vars for services (`KINESIS_PROVIDER`, `LAMBDA_EXECUTOR`, etc.) that no longer exist. With services removed, the deprecations list has no actionable purpose. The `deprecation_warnings` plux hook (`localstack.plugins:deprecation_warnings`) calls into `deprecations.py`; if `deprecations.py` is deleted, this hook must be removed or its implementation inlined in `plugins.py` as a no-op.

**`localstack/constants.py` — PRUNE.**  
Remove any constants that were retained in the original spec but are now orphaned because their sole consumers (packages, analytics, dev, testing) are being removed. Run `grep -r "from localstack.constants import\|localstack.constants\." localstack/ tests/ --include="*.py"` against the retained tree after each phase to identify dead symbols.

**`localstack/config.py` — PRUNE further.**  
Variables to remove now that their consumers are gone:

| Variable(s) | Consumer removed |
|------------|-----------------|
| `CONTAINER_RUNTIME` | `dev/kubernetes/__main__.py` deleted |
| `MAIN_DOCKER_NETWORK`, `EXTERNAL_SERVICE_PORTS_START/END` | Container networking removed |
| `DISABLE_CUSTOM_CORS_S3`, `DISABLE_CUSTOM_CORS_APIGATEWAY` | Audit — remove if CORS handler no longer references them |
| `S3_VIRTUAL_HOSTNAME`, `S3_STATIC_WEBSITE_HOSTNAME` | `utils/aws/aws_stack.py` — keep only if `aws_stack.py` is retained with those references |
| Analytics env vars (`DISABLE_EVENTS`, etc.) | Analytics pipeline removed |
| Any `DEBUG_ANALYTICS_*`, `SKIP_*` flags for removed components | |

After removal, run `python -c "import localstack.config; print('config OK')"` to verify no startup errors.

---

## 5. Execution Plan

### Phase 1 — Verify Transfer Service Tests

> **This phase runs first**, before any code is removed, to confirm the existing test suite passes and will serve as the regression harness throughout all subsequent phases.

The integration test suite already exists at `tests/aws/services/transfer/test_transfer.py`. It contains two classes:

- **`TestTransferServer`** — `test_create_server`, `test_describe_server`, `test_describe_server_invalid_id`, `test_create_and_describe_server_state`
- **`TestTransferUser`** — `test_create_user`, `test_create_user_invalid_server`, `test_create_user_duplicate`, `test_list_users`, `test_list_users_empty`, `test_list_users_invalid_server`, `test_delete_user`, `test_delete_user_invalid_user`, `test_delete_user_invalid_server`

The tests use `@markers.aws.validated` and `@markers.snapshot.skip_snapshot_verify` from `localstack.testing.pytest`, the `aws_client`, `snapshot`, and `account_id` fixtures, snapshot JSON files (`test_transfer.snapshot.json`, `test_transfer.validation.json`), and `localstack.utils.strings.short_uid`. These dependencies constrain what can be removed in later phases.

There are no unit tests; this is integration-only.

**Step 1.1 — Verify tests collect and pass**
```bash
# Requires localstack start --host in another terminal
pytest tests/aws/services/transfer/ -x -q
```
All tests must pass before proceeding to Phase 2.

---

### Phase 2 — Remove packages/

**Step 2.1 — Delete directory**
```bash
rm -rf localstack-core/localstack/packages/
```

**Step 2.2 — Remove plux.ini entries**
Remove `[localstack.packages]` section and both entries (`ffmpeg/community`, `java/community`).

**Step 2.3 — Update pyproject.toml**
Remove the `localstack.packages` entry-point group. Remove `debugpy` from dependencies if it was pulled in solely by `packages/debugpy.py`.

**Step 2.4 — Verify**
```bash
python -c "import localstack.aws.app; import localstack.services.plugins; print('OK')"
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -x -q
```

---

### Phase 3 — Remove dev/

**Step 3.1 — Delete directory**
```bash
rm -rf localstack-core/localstack/dev/
```

**Step 3.2 — Remove plux.ini hook**
Remove `conditionally_enable_debugger = localstack.dev.debugger.plugins:conditionally_enable_debugger` from `[localstack.hooks.on_infra_start]`.

**Step 3.3 — Verify**
```bash
python -c "import localstack.aws.app; print('OK')"
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -x -q
```

---

### Phase 4 — Prune testing/

The Transfer tests import from `localstack.testing.pytest` and rely on its fixtures, so the core `pytest/` package must be retained. Only the service-specific sub-packages are removed.

**Step 4.1 — Remove service-specific sub-packages**
```bash
rm -rf localstack-core/localstack/testing/pytest/cloudformation/
rm -rf localstack-core/localstack/testing/pytest/stepfunctions/
rm -rf localstack-core/localstack/testing/scenario/
rm -rf localstack-core/localstack/testing/testselection/
rm -f  localstack-core/localstack/testing/config.py
```

**Step 4.2 — Verify retained imports still resolve**
```bash
python -c "from localstack.testing.pytest import markers; print('markers OK')"
python -c "from localstack.testing.pytest.fixtures import aws_client; print('fixtures OK')"
```

**Step 4.3 — Verify tests still collect and pass**
```bash
pytest tests/aws/services/transfer/ -x -q
```

---

### Phase 5 — Prune tests/

**Step 5.1 — Remove all non-Transfer test directories under tests/aws/services/**
```bash
find tests/aws/services -mindepth 1 -maxdepth 1 -type d ! -name transfer -exec rm -rf {} +
```

**Step 5.2 — Remove all top-level test files in tests/aws/ and non-Transfer directories**
```bash
rm -f tests/aws/test_*.py
rm -rf tests/aws/files tests/aws/scenario tests/aws/serverless tests/aws/templates tests/aws/terraform tests/aws/cdk_templates
```

**Step 5.3 — Remove unit tests entirely**
```bash
rm -rf tests/unit/
```

**Step 5.4 — Remove entire test directories**
```bash
rm -rf tests/integration tests/bootstrap tests/performance
```

**Step 5.5 — Audit tests/aws/conftest.py**
Inspect `tests/aws/conftest.py` for any fixture definitions or imports that reference removed service modules or the deleted `localstack/testing/` sub-packages. Remove or stub those entries; retain all fixtures used by `test_transfer.py` (`aws_client`, `snapshot`, `account_id`).

**Step 5.6 — Verify**
```bash
pytest tests/ --collect-only -q
# Only tests/aws/services/transfer/ should appear
pytest tests/aws/services/transfer/ -x -q
```

---

### Phase 6 — Remove Docker and container tooling

**Step 6.1 — Remove Dockerfiles and compose files**
```bash
rm -f Dockerfile Dockerfile.s3 docker-compose.yml docker-compose-pro.yml
rm -f bin/docker-entrypoint.sh bin/docker-helper.sh DOCKER.md
```

**Step 6.2 — Remove container utility modules**
```bash
rm -rf localstack-core/localstack/utils/container_utils/
rm -f localstack-core/localstack/utils/container_networking.py
rm -f localstack-core/localstack/utils/docker_utils.py
```

**Step 6.3 — Remove container-related config variables**
Audit and remove from `config.py`: `CONTAINER_RUNTIME`, `MAIN_DOCKER_NETWORK`, `EXTERNAL_SERVICE_PORTS_START`, `EXTERNAL_SERVICE_PORTS_END`, `WINDOWS_DOCKER_MOUNT_PREFIX` (if not already removed), and any other variables exclusively consumed by deleted container modules.

**Step 6.4 — Verify**
```bash
grep -r "from localstack.utils.container_utils\|from localstack.utils.docker_utils\|from localstack.utils.container_networking\|import docker$\|from docker " localstack-core/localstack/ --include="*.py"
# Must return zero results
python -c "import localstack.aws.app; print('OK')"
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -x -q
```

---

### Phase 7 — Remove CI and developer process files

**Step 7.1 — Remove CI directory**
```bash
rm -rf .github/
```

**Step 7.2 — Remove pre-commit config**
```bash
rm -f .pre-commit-config.yaml
```

**Step 7.3 — Remove release scripts and bin utilities**
```bash
rm -f bin/release-dev.sh bin/release-helper.sh bin/localstack-supervisor bin/hosts
```

**Step 7.4 — Remove scripts directory**
```bash
rm -rf scripts/
```

**Step 7.5 — Remove documentation files**
```bash
rm -rf docs/
rm -f CODEOWNERS CODE_OF_CONDUCT.md AGENTS.md
```

**Step 7.6 — Reduce Makefile**
Keep only:
- `install` — `pip install -e ".[runtime,test]"`
- `start` — `localstack start --host`
- `test-transfer` — `pytest tests/aws/services/transfer/ -x -q`

Remove all Docker targets, CI targets, linting targets, and service-specific targets.

---

### Phase 8 — Prune utils/

**Step 8.1 — Remove clearly unused subdirectories and files**
```bash
rm -rf localstack-core/localstack/utils/analytics/
rm -rf localstack-core/localstack/utils/xray/
rm -rf localstack-core/localstack/utils/server/
rm -f localstack-core/localstack/utils/java.py
rm -f localstack-core/localstack/utils/testutil.py
```

**Step 8.2 — Remove plux.ini entries for analytics and catalog**
Remove:
- `_mount_machine_file` from `[localstack.hooks.configure_localstack_container]`  
  (if the section becomes empty, remove the section header too)
- `prepare_host_machine_id` from `[localstack.hooks.prepare_host]`  
  (if the section becomes empty, remove the section header too)
- `_publish_config_as_analytics_event` from `[localstack.hooks.on_infra_start]`
- `publish_metrics` from `[localstack.hooks.on_infra_shutdown]`
- Both entries from `[localstack.utils.catalog]`  
  (remove the section header too)

**Step 8.3 — Remove catalog directory**
```bash
rm -rf localstack-core/localstack/utils/catalog/
```

**Step 8.4 — Audit AUDIT-flagged modules**
For each module flagged AUDIT in §4.2, run:
```bash
grep -rn "from localstack.utils.<module>\|utils\.<module>" localstack-core/localstack/ --include="*.py"
```
Filter to retained paths only. Remove modules with zero retained callers.

**Step 8.5 — Remove analytics hooks from runtime**
Check `localstack/runtime/analytics.py`: if it exists and is solely consumed by the removed `_publish_config_as_analytics_event` hook, delete it. If it has other uses, stub the analytics publish to a no-op.

**Step 8.6 — Verify**
```bash
python -c "import localstack.aws.app; import localstack.services.plugins; print('OK')"
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -x -q
```

---

### Phase 9 — Prune dependencies

**Step 9.1 — Remove `docker` SDK dependency**
Remove `docker` from `pyproject.toml` dependencies. Confirm no retained module imports it.
```bash
grep -r "import docker\|from docker" localstack-core/localstack/ --include="*.py"
# Must return zero results
```

**Step 9.2 — Remove analytics-specific packages**
Identify any packages imported only within `utils/analytics/` (now deleted). Cross-reference `pyproject.toml` and remove them.

**Step 9.3 — Remove debugpy**
Remove `debugpy` from dependencies if it was only used by `packages/debugpy.py`.

**Step 9.4 — Remove dev-tooling extras**
Remove any `pyproject.toml` extras groups or entries that exclusively supported deleted components (packages, dev, testing, analytics).

**Step 9.5 — Regenerate lock file**
```bash
uv lock
```

**Step 9.6 — Verify**
```bash
pip install -e ".[runtime]" --dry-run 2>&1 | grep -i error
# Must be empty
python -c "import localstack.aws.app; print('OK')"
```

---

### Phase 10 — Prune config.py, constants.py; remove deprecations.py

**Step 10.1 — Remove deprecations.py**
```bash
rm -f localstack-core/localstack/deprecations.py
```

**Step 10.2 — Update plugins.py**
Remove the `deprecation_warnings` function or replace its body with `pass` so the plux hook continues to resolve without error. Alternatively remove the `deprecation_warnings` plux.ini entry if the function body was the only reason for the hook.

**Step 10.3 — Prune config.py**
Remove variables whose sole consumers have been deleted in prior phases. Methodology:
```bash
# For each candidate variable VAR:
grep -rn "config\.VAR\b\|config\.VAR " localstack-core/localstack/ tests/unit/services/transfer/ tests/aws/services/transfer/ --include="*.py"
# If zero results, the variable is dead — remove it
```
Key candidates: `CONTAINER_RUNTIME`, `MAIN_DOCKER_NETWORK`, `EXTERNAL_SERVICE_PORTS_*`, `DISABLE_EVENTS`, analytics-related flags, `S3_VIRTUAL_HOSTNAME`, `S3_STATIC_WEBSITE_HOSTNAME` (if `aws_stack.py` usages are in deleted code).

**Step 10.4 — Prune constants.py**
Apply the same grep methodology. Remove constants with zero retained callers.

**Step 10.5 — Verify**
```bash
python -c "import localstack.config; import localstack.constants; print('OK')"
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -x -q
```

---

### Phase 11 — Reduce README and pyproject.toml metadata

**Step 11.1 — Update README.md**
Replace existing content with:
- What the repo is (minimal framework skeleton)
- How to start it (`localstack start --host`)
- How to add a new service provider (pattern: create `services/<name>/provider.py`, register in `services/providers.py`, use Transfer as reference)
- How to run Transfer tests

**Step 11.2 — Update pyproject.toml metadata**
- Update `description` to reflect the framework-only nature
- Remove `package-data` globs for deleted files
- Tighten `[tool.ruff]` exclude paths to match retained code only
- Remove `[tool.deptry]` ignore entries for deleted packages

---

### Phase 12 — Final Cleanup

**Step 12.1 — Dead import removal**
```bash
ruff check --select F401 localstack-core/localstack/ --fix
```
Review all auto-fixes before committing; do not auto-remove imports that are part of a public API surface.

**Step 12.2 — Full framework startup**
```bash
localstack start --host 2>&1 | tee /tmp/ls-startup.log
grep -i "error\|exception\|traceback" /tmp/ls-startup.log
# Must return zero results
grep "Ready\." /tmp/ls-startup.log
# Must appear exactly once
```

**Step 12.3 — Run Transfer test suite**
```bash
pytest tests/unit/services/transfer/ tests/aws/services/transfer/ -v
# All tests must pass
```

**Step 12.4 — Verify plugin extensibility**
Write a scratch provider (in `/tmp/`, not committed) and verify it can be loaded:
```python
# /tmp/test_provider.py
from localstack.services.plugins import aws_provider, Service
from localstack.aws.api.s3 import S3Api  # or any other api

@aws_provider()
def s3():
    from moto.s3 import models
    return Service.for_provider(...)
```
This validates that the `@aws_provider()` decorator and `Service.for_provider()` path still work for new providers.

---

## 6. Validation

### V1 — Import validation
```bash
python -c "
import localstack.aws.app
import localstack.runtime.runtime
import localstack.services.plugins
import localstack.state.core
import localstack.extensions.api
import localstack.services.transfer.provider
print('All core imports OK')
"
```

### V2 — Framework startup
```bash
localstack start --host 2>&1 | grep -E "Ready\.|ERROR|Traceback"
# Expected: exactly one "Ready." line, zero ERROR/Traceback lines
```

### V3 — Transfer service responds correctly
```bash
localstack start --host &
sleep 8
aws --endpoint-url http://localhost:4566 transfer create-server
# Expected: JSON response with ServerId
```

### V4 — Unknown service returns 501 (not a crash)
```bash
aws --endpoint-url http://localhost:4566 s3 ls 2>&1
# Expected: structured error response, not a Python traceback
```

### V5 — Plugin system loads Transfer
```bash
python -c "
import plux
providers = plux.PluginManager('localstack.aws.provider').load_all()
print(f'Loaded providers: {[p.name for p in providers]}')
assert any(p.name == 'transfer' for p in providers), 'transfer provider missing'
print('Plugin system OK')
"
```

### V6 — Transfer test suite passes
```bash
pytest tests/aws/services/transfer/ -v --tb=short
# Expected: all 13 tests green, no collection errors
```

### V7 — No Docker runtime imports in retained code
```bash
grep -r "from docker\|import docker\|container_utils\|docker_utils\|container_networking" \
  localstack-core/localstack/ --include="*.py"
# Expected: zero results
```

### V8 — No broken package imports
```bash
pip install -e ".[runtime]" --dry-run
python -m py_compile $(find localstack-core/localstack -name "*.py" | head -100)
# Expected: no errors
```

### V9 — Dependency audit
```bash
pip show localstack-core | grep -i requires
# docker, debugpy, antlr4-python3-runtime, aws-sam-translator, jpype1, opensearch-py
# must NOT appear in the dependency graph
```

---

## 7. Success Criteria

The work is complete when all of the following are true:

1. `localstack start --host` reaches `Ready.` with no errors and at least one provider registered (`transfer`).
2. All five Transfer API operations (`CreateServer`, `DescribeServer`, `CreateUser`, `ListUsers`, `DeleteUser`) return correct responses when called via boto3 against the local endpoint.
3. `pytest tests/aws/services/transfer/ -q` exits 0 with all 13 tests passing and no collection errors.
4. `plux.PluginManager("localstack.aws.provider").load_all()` returns exactly one provider (`transfer`).
5. The directories `localstack/packages/`, `localstack/dev/`, `localstack/testing/`, `localstack/utils/analytics/`, `localstack/utils/container_utils/` no longer exist.
6. The files `Dockerfile`, `Dockerfile.s3`, `docker-compose.yml`, `.pre-commit-config.yaml`, `localstack/deprecations.py` no longer exist.
7. `grep -r "import docker\|from docker" localstack-core/localstack/` returns zero results.
8. `ruff check --select F401 localstack-core/localstack/` reports zero unused import errors.
9. The Transfer service is the only entry in `[localstack.aws.provider]`; the `[localstack.cloudformation.resource_providers]` and `[localstack.lambda.runtime_executor]` sections remain present but empty.
10. A developer reading `localstack/services/transfer/provider.py` and `localstack/services/providers.py` has everything they need to add a second service provider without reading any other file.
