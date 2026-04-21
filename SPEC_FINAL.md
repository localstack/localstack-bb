# LocalStack Minimal Framework — Final Specification

This document consolidates SPEC.md (original 12-phase extraction plan) and SPEC_LATEST.md (revised minimal-skeleton plan) into a single source of truth. All 12 phases are **complete**. The document records both the plan and what was actually done, so future sessions have full context.

---

## 1. Background

The project started as a full LocalStack monorepo with 39+ AWS service implementations. The goal was to strip it down progressively across two spec generations:

- **SPEC.md (original)** — Remove service implementations, keep the framework chassis including packages installer, analytics pipeline, developer tooling, full testing framework, and Docker. Phases 1–5 of SPEC.md were completed first.
- **SPEC_LATEST.md (revised)** — Strip further: remove packages, dev, container tooling, analytics, catalog, x-ray, TCP proxy, deprecations. Retain only the Transfer service as the reference implementation. Phases 1–12 of SPEC_LATEST.md are now complete.

The result is a **minimal, host-mode-runnable framework skeleton** with the Transfer service as the only registered provider.

---

## 2. Objective

Reduce the LocalStack codebase to the smallest surface that is still:

1. **Runnable in host mode** — `python -m localstack.runtime.main` reaches `Ready.` with no errors.
2. **Functional with a real service** — Transfer is the only registered provider; its full API works correctly end-to-end.
3. **Extensible** — A developer can add a new service provider by following the Transfer service as a reference: create a provider module, register a factory function in `providers.py`, wire `plux.ini` — done.

---

## 3. Final State

### 3.1 What Was Retained

| Area | Path |
|------|------|
| AWS protocol gateway | `localstack/aws/` — app, chain, handlers, protocol, serving, skeleton, spec, forwarder |
| AWS API specs | `localstack/aws/api/` — generated; all services present for protocol parsing |
| Service plugin system | `localstack/services/plugins.py` |
| Provider registry | `localstack/services/providers.py` — single entry: `transfer` |
| Service scaffold | `localstack/services/edge.py`, `internal.py`, `moto.py`, `stores.py` |
| Transfer service | `localstack/services/transfer/` — `__init__.py`, `models.py`, `provider.py` |
| ASF runtime | `localstack/runtime/` — main, runtime, server, hooks, init, init_scripts, components, legacy, shutdown, patches |
| HTTP layer | `localstack/http/` — all files |
| State & persistence | `localstack/state/` — all files |
| Extension framework | `localstack/extensions/` — all files |
| DNS | `localstack/dns/` — all files |
| CLI | `localstack/cli/` — all files |
| Logging | `localstack/logging/` — all files |
| Core modules | `localstack/plugins.py`, `version.py`, `py.typed` |
| Configuration | `localstack/config.py` (pruned) |
| Constants | `localstack/constants.py` (pruned) |
| Essential utilities | `localstack/utils/` (partial — see §3.3) |
| Testing framework (core) | `localstack/testing/pytest/` — `__init__.py`, `markers.py`, `fixtures.py`, `bootstrap.py`, `container.py`; `localstack/testing/snapshots/`; `localstack/testing/aws/` |
| Transfer integration tests | `tests/aws/services/transfer/` |
| Build config | `pyproject.toml`, `plux.ini`, `Makefile` (minimal) |

### 3.2 What Was Removed

| Area | Path |
|------|------|
| All 39+ service implementations | `localstack/services/<service>/` |
| Package installer framework | `localstack/packages/` |
| Developer tooling | `localstack/dev/` |
| Analytics pipeline | `localstack/utils/analytics/`, `localstack/runtime/analytics.py`, `localstack/aws/handlers/analytics.py` |
| X-Ray tracing | `localstack/utils/xray/`, `localstack/aws/handlers/tracing.py` |
| Service catalog | `localstack/utils/catalog/` |
| TCP proxy server | `localstack/utils/server/` |
| Container utilities | `localstack/utils/container_utils/`, `utils/container_networking.py`, `utils/docker_utils.py` |
| Deprecations | `localstack/deprecations.py` |
| Misc utils | `utils/java.py`, `utils/testutil.py`, `utils/scheduler.py`, `utils/event_matcher.py`, `utils/tagging.py` |
| Testing sub-packages | `localstack/testing/pytest/cloudformation/`, `pytest/stepfunctions/`, `testing/scenario/`, `testing/testselection/` |
| Non-Transfer tests | `tests/aws/services/<all except transfer>/`, all top-level `tests/aws/test_*.py`, `tests/unit/`, `tests/integration/`, `tests/bootstrap/`, `tests/performance/` |
| Dockerfiles | `Dockerfile`, `Dockerfile.s3`, `docker-compose.yml`, `docker-compose-pro.yml` |
| Container scripts | `bin/docker-entrypoint.sh`, `bin/docker-helper.sh` |
| CI/CD | `.github/` (entire directory) |
| Release scripts | `bin/release-dev.sh`, `bin/release-helper.sh`, `bin/localstack-supervisor`, `bin/hosts` |
| Developer config | `.pre-commit-config.yaml` |
| Docs / process files | `docs/`, `CODEOWNERS`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, `DOCKER.md`, `scripts/` |

### 3.3 utils/ Module Disposition

| Path | Status |
|------|--------|
| `utils/analytics/` | **DELETED** |
| `utils/container_utils/` | **DELETED** |
| `utils/container_networking.py` | **DELETED** |
| `utils/docker_utils.py` | **DELETED** |
| `utils/xray/` | **DELETED** |
| `utils/catalog/` | **DELETED** |
| `utils/server/` | **DELETED** |
| `utils/java.py` | **DELETED** |
| `utils/testutil.py` | **DELETED** |
| `utils/scheduler.py` | **DELETED** |
| `utils/event_matcher.py` | **DELETED** |
| `utils/tagging.py` | **DELETED** |
| `utils/kinesis/` | **DELETED** (in original SPEC.md phase) |
| `utils/cloudwatch/` | **DELETED** (in original SPEC.md phase) |
| `utils/aws/aws_responses.py`, `dead_letter_queue.py`, `message_forwarding.py`, `queries.py`, `templating.py` | **DELETED** (in original SPEC.md phase) |
| All other `utils/` modules | **KEPT** |

---

## 4. plux.ini — Final State

```ini
[localstack.aws.provider]
transfer = localstack.services.providers:transfer

[localstack.cloudformation.resource_providers]
# CloudFormation resource providers are registered by downstream packages

[localstack.hooks.on_infra_ready]
_run_init_scripts_on_ready = localstack.runtime.init:_run_init_scripts_on_ready

[localstack.hooks.on_infra_shutdown]
_run_init_scripts_on_shutdown = localstack.runtime.init:_run_init_scripts_on_shutdown
run_on_after_service_shutdown_handlers = localstack.runtime.shutdown:run_on_after_service_shutdown_handlers
run_shutdown_handlers = localstack.runtime.shutdown:run_shutdown_handlers
shutdown_services = localstack.runtime.shutdown:shutdown_services
stop_server = localstack.dns.plugins:stop_server

[localstack.hooks.on_infra_start]
_patch_botocore_endpoint_in_memory = localstack.aws.client:_patch_botocore_endpoint_in_memory
_patch_botocore_json_parser = localstack.aws.client:_patch_botocore_json_parser
_patch_cbor2 = localstack.aws.client:_patch_cbor2
_run_init_scripts_on_start = localstack.runtime.init:_run_init_scripts_on_start
apply_aws_runtime_patches = localstack.aws.patches:apply_aws_runtime_patches
apply_runtime_patches = localstack.runtime.patches:apply_runtime_patches
delete_cached_certificate = localstack.plugins:delete_cached_certificate
eager_load_services = localstack.services.plugins:eager_load_services
init_response_mutation_handler = localstack.aws.handlers.response:init_response_mutation_handler
register_swagger_endpoints = localstack.http.resources.swagger.plugins:register_swagger_endpoints
setup_dns_configuration_on_host = localstack.dns.plugins:setup_dns_configuration_on_host
start_dns_server = localstack.dns.plugins:start_dns_server

[localstack.init.runner]
py = localstack.runtime.init:PythonScriptRunner
sh = localstack.runtime.init:ShellScriptRunner

[localstack.lambda.runtime_executor]
# Lambda runtime executors are registered by downstream packages

[localstack.openapi.spec]
localstack = localstack.plugins:CoreOASPlugin

[localstack.runtime.components]
aws = localstack.aws.components:AwsComponents

[localstack.runtime.server]
hypercorn = localstack.runtime.server.plugins:HypercornRuntimeServerPlugin
twisted = localstack.runtime.server.plugins:TwistedRuntimeServerPlugin
```

**Important:** The three empty sections (`[localstack.aws.provider]` — minus the transfer entry — `[localstack.cloudformation.resource_providers]`, `[localstack.lambda.runtime_executor]`) must remain present so downstream packages can inject into them without code changes.

---

## 5. Implementation History

### Phase 1 — Remove Service Implementations ✅

All 39+ service directories deleted from `localstack/services/`. Factory functions cleared from `providers.py` (single `transfer` entry retained). Verified `python -c "import localstack.aws.app"` after each removal.

### Phase 2 — Clean Up plux.ini ✅

Cleared `[localstack.aws.provider]` (all entries except `transfer`), `[localstack.cloudformation.resource_providers]`, `[localstack.lambda.runtime_executor]`. Kept all framework lifecycle hooks.

### Phase 3 — Prune Dependencies (original SPEC.md) ✅

Removed from `runtime`: `antlr4-python3-runtime`, `aws-sam-translator`, `jpype1`, `kclpy-ext`, `opensearch-py`, `pymongo`, `apispec`, `crontab`, `responses`, `jsonpath-ng`, `airspeed-ext`.

### Phase 4 — Prune config.py (original SPEC.md) ✅

Removed all `LAMBDA_*`, `KINESIS_*`, `DYNAMODB_*`, `SQS_*`, `OPENSEARCH_*`, `SNS_*`, `APIGW_*`, `SFN_*` variables. `CONFIG_ENV_VARS` list pruned to match.

### Phase 5 — Prune utils/ (original SPEC.md) ✅

Removed `utils/kinesis/`, `utils/cloudwatch/`. Audited `utils/aws/`: deleted `aws_responses.py`, `dead_letter_queue.py`, `message_forwarding.py`, `queries.py`, `templating.py`. Kept `arns.py`, `aws_stack.py`, `client.py`, `client_types.py`, `request_context.py`, `resources.py`.

### Phase 6 — Remove Docker and Container Tooling ✅

Deleted Dockerfiles, compose files, `bin/docker-entrypoint.sh`, `bin/docker-helper.sh`, `DOCKER.md`. Deleted `utils/container_utils/`, `utils/container_networking.py`, `utils/docker_utils.py`. Stripped `utils/bootstrap.py` from ~1403 lines to ~282 lines (all container classes removed). Removed container config vars from `config.py`: `DOCKER_SOCK`, `DOCKER_FLAGS`, `DOCKER_CMD`, `LEGACY_DOCKER_CLIENT`, `DOCKER_GLOBAL_IMAGE_PREFIX`, `DOCKER_BRIDGE_IP`, `DOCKER_SDK_DEFAULT_TIMEOUT_SECONDS`, `DOCKER_SDK_DEFAULT_RETRIES`, `MAIN_CONTAINER_NAME`, `EXTERNAL_SERVICE_PORTS_START/END`, `CONTAINER_RUNTIME`, `MAIN_DOCKER_NETWORK`, `PORTS_CHECK_DOCKER_IMAGE`, and the `ping()` function.

**Fix required:** `utils/analytics/metadata.py` had a module-level `from localstack.utils.bootstrap import Container` import (not lazy). Fixed by removing the import and deleting the `_mount_machine_file` function that used it.

**Fix required:** `utils/net.py` had `get_docker_host_from_container()` and `get_addressable_container_host()` functions. Removed (no retained callers).

**Fix required:** `utils/common.py` had `ExternalServicePortsManager` class and `external_service_ports` instance. Removed.

### Phase 7 — Remove CI and Developer Process Files ✅

Removed `.github/`, `.pre-commit-config.yaml`, `bin/release-*.sh`, `bin/localstack-supervisor`, `bin/hosts`, `scripts/`, `docs/`, `CODEOWNERS`, `CODE_OF_CONDUCT.md`, `AGENTS.md`. Reduced `Makefile` to three targets: `install`, `start`, `test-transfer`.

### Phase 8 — Prune utils/ (SPEC_LATEST.md) ✅

Deleted: `utils/analytics/`, `utils/xray/`, `utils/server/`, `utils/java.py`, `utils/testutil.py`, `utils/scheduler.py`, `utils/event_matcher.py`, `utils/tagging.py`, `utils/catalog/`, `runtime/analytics.py`, `aws/handlers/analytics.py`, `aws/handlers/tracing.py`.

**Cascade fixes required by these deletions:**

- **`aws/handlers/tracing.py`** imported `from localstack.utils.xray.trace_header import TraceHeader` at module level. Since `tracing.py` itself was deleted, also removed `parse_trace_context = tracing.TraceContextParser()` from `aws/handlers/__init__.py` and removed it from the request chain in `aws/app.py`.

- **`aws/handlers/analytics.py`** deleted; removed `count_service_request = analytics.ServiceRequestCounter()` from `aws/handlers/__init__.py` and from the response chain in `aws/app.py`.

- **`utils/catalog/`** was imported by `aws/catalog_exceptions.py`, `aws/skeleton.py`, `aws/handlers/service.py`. Fixed by simplifying `catalog_exceptions.py` to always return `ServiceOrOperationNotSupportedException` without catalog lookup:
  ```python
  def get_service_availability_exception(service_name, operation_name):
      return ServiceOrOperationNotSupportedException(service_name, operation_name)
  ```
  Updated callers in `skeleton.py` and `handlers/service.py` to pass only `service_name` and `operation_name` (no status argument).

- **`utils/server/tcp_proxy`** was imported at module level in `services/edge.py`. Fixed by making the import lazy (inside the `do_start_tcp_proxy()` function body).

- **`runtime/analytics.py`** deletion required removing `import analytics` from `runtime/init.py`; simplified `_run_and_log()` to call `init_script_manager().run_stage(stage)` directly.

- **`services/internal.py`**: Removed `analytics.metadata` imports; simplified `InfoResource.get_info_data()` to return static fields only. Also removed `DeprecatedResource` class (Phase 10) and its `from localstack.deprecations import deprecated_endpoint` import.

- **`deprecations.py`**: Removed `from localstack.utils.analytics import log` and `log.event()` call (Phase 8 prep); then deleted entirely in Phase 10.

- **`testing/pytest/fixtures.py`**: Removed `from localstack.utils import testutil`; removed lambda-related fixtures that depended on deleted modules.

- **`plux.ini`**: Removed `[localstack.hooks.configure_localstack_container]` section, `[localstack.hooks.prepare_host]` section, `publish_metrics` from `on_infra_shutdown`, `_publish_config_as_analytics_event` from `on_infra_start`, `[localstack.utils.catalog]` section.

### Phase 9 — Prune Dependencies (SPEC_LATEST.md) ✅

Removed from `pyproject.toml`:
- `base-runtime`: `docker>=6.1.1`
- `runtime`: `awscli==1.44.49`, `jsonpath-rw>=1.4.0`
- `test`: `pytest-split`, `pytest-rerunfailures`, `pytest-tinybird`, `aws-cdk-lib`, `websocket-client`, `json5`, `httpx[http2]`
- `dev` trimmed to: `deptry`, `ruff`, `mypy`
- `typehint` boto3-stubs reduced to `[iam,kms,s3,sns,sqs,sts,transfer]`
- Removed `bin/localstack-supervisor` from `script-files`

Regenerated `uv.lock` with `uv lock`.

### Phase 10 — Prune config.py, constants.py; Remove deprecations.py ✅

**Deleted:** `localstack/deprecations.py` (tracked deprecated env vars for removed services — no remaining purpose).

**`plugins.py`:** Removed `deprecation_warnings()` function (which lazily imported and called `deprecations.py`).

**`plux.ini`:** Removed `deprecation_warnings = localstack.plugins:deprecation_warnings` from `on_infra_start`.

**`config.py` variables removed:** `CONFIG_PROFILE`, `DEVELOP`, `DEVELOP_PORT`, `WAIT_FOR_DEBUGGER`, `DISABLE_EVENTS`, `DEBUG_ANALYTICS`, `SKIP_INFRA_DOWNLOADS`, `PARITY_AWS_ACCESS_KEY_ID`, `CFN_VERBOSE_ERRORS`. Changed `load_environment(CONFIG_PROFILE)` → `load_environment("")`. Removed `DEFAULT_DEVELOP_PORT` from constants import block. Cleaned `CONFIG_ENV_VARS` list to match.

**`constants.py` constants removed:** `HEADER_LOCALSTACK_EDGE_URL`, `HEADER_LOCALSTACK_REQUEST_URL`, `DOCKER_IMAGE_NAME`, `DOCKER_IMAGE_NAME_PRO`, `DOCKER_IMAGE_NAME_FULL`, `CONFIG_UPDATE_PATH`, `ENV_PRO_ACTIVATED`, `ANALYTICS_API`, `OFFICIAL_IMAGES`, `DEFAULT_DEVELOP_PORT`.

### Phase 11 — README and pyproject.toml Metadata ✅

Rewrote `README.md` to describe the skeleton with start/test instructions and a guide for adding new service providers.

`pyproject.toml` changes:
- Updated `description` to `"Minimal host-mode-runnable framework skeleton of LocalStack"`
- Removed dead `deptry` entries: `known_first_party = ["vosk"]`, `extend_exclude` entries for `scripts/**` and `localstack-core/localstack/dev/**` (both deleted)
- Removed `[tool.deptry.per_rule_ignores] DEP001 = ["stevedore"]` (no longer in codebase)

### Phase 12 — Final Cleanup ✅

Ran `ruff check --select F401 localstack-core/localstack/ --fix`. 22 auto-fixed, 3 remaining in `aws/api/transfer/__init__.py` (`IO`, `Iterable`, `Iterator` — not auto-fixable by ruff as potential public API exports). Verified no callers import these from that module; removed manually.

**V1 import validation passed:**
```
All core imports OK
```

---

## 6. Key Architectural Decisions and Non-Obvious Changes

### 6.1 Catalog removal simplified error handling

The `utils/catalog/` module was used to look up whether a given service is "available" in LocalStack and return an appropriately typed `AwsServiceAvailabilityException`. After deletion, `aws/catalog_exceptions.py` was simplified to always return `ServiceOrOperationNotSupportedException` regardless of service name. This is correct for a minimal skeleton where any unregistered service should return a 501-style error.

### 6.2 TCP proxy import made lazy in edge.py

`services/edge.py` had a module-level `from localstack.utils.server.tcp_proxy import TCPProxy` import. The `do_start_tcp_proxy()` function is only called at runtime if a TCP proxy is actually needed (not in normal Transfer-only operation). The import was made lazy to avoid the `ModuleNotFoundError` at startup.

### 6.3 analytics/metadata.py had a non-lazy Container import

Despite appearing to be a late import, `from localstack.utils.bootstrap import Container` was at module level in `utils/analytics/metadata.py` (line 9). It broke test collection immediately after `bootstrap.py` was stripped. Fixed by removing the import and the `_mount_machine_file` function that used it — both were analytics-only.

### 6.4 tracing.py removed entirely (not stubbed)

`aws/handlers/tracing.py` was not retained as a stub because `parse_trace_context` was the only consumer and it was cleanly removable from the handler chain in `aws/app.py`.

### 6.5 analytics removed from aws/app.py handler chain

The request/response handler chain in `aws/app.py` had `handlers.count_service_request` (from analytics) in the response chain and `handlers.parse_trace_context` (from tracing) in the request chain. Both were removed. The handler chain now runs without either.

---

## 7. Running the Framework

### Prerequisites

Virtual environment: `/home/viren/.virtualenvs/ls_bb`

```bash
# Install
pip install -e ".[runtime]"

# Start (host mode)
python -m localstack.runtime.main

# Run Transfer tests (requires running LocalStack)
ACTIVATE_PRO=0 DEBUG=1 LOCALSTACK_API_KEY=test TEST_SKIP_LOCALSTACK_START=1 \
  pytest tests/aws/services/transfer/ -x -q
```

### Important test env vars

- `TEST_SKIP_LOCALSTACK_START=1` — prevents the `in_memory_localstack` pytest plugin from trying to bind port 4566 (needed when running tests against an already-running LocalStack instance).
- `ACTIVATE_PRO=0 DEBUG=1 LOCALSTACK_API_KEY=test` — suppress pro activation errors, enable debug logging.

---

## 8. Adding a New Service Provider

Three steps, no other files to touch:

1. **Create `localstack-core/localstack/services/<name>/provider.py`** — implement a class decorated with `@service_provider` that inherits from the generated API class in `localstack/aws/api/<name>/`. Use `localstack/services/transfer/provider.py` as the reference.

2. **Register in `localstack-core/localstack/services/providers.py`** — add a factory function:
   ```python
   def <name>():
       from localstack.services.<name>.provider import <Name>Provider
       return <Name>Provider()
   ```

3. **Add to `plux.ini`** under `[localstack.aws.provider]`:
   ```ini
   <name> = localstack.services.providers:<name>
   ```

---

## 9. Validation Checks

```bash
# V1 — Import validation
python -c "
import localstack.aws.app
import localstack.runtime.runtime
import localstack.services.plugins
import localstack.state.core
import localstack.extensions.api
import localstack.services.transfer.provider
print('All core imports OK')
"

# V2 — No Docker imports remain
grep -r "from docker\|import docker\|container_utils\|docker_utils\|container_networking" \
  localstack-core/localstack/ --include="*.py"
# Expected: zero results

# V3 — No unused imports
ruff check --select F401 localstack-core/localstack/
# Expected: zero errors

# V4 — Plugin system loads Transfer
python -c "
import plux
providers = plux.PluginManager('localstack.aws.provider').load_all()
print([p.name for p in providers])
"
# Expected: ['transfer']

# V5 — Transfer tests pass (requires running LocalStack)
ACTIVATE_PRO=0 DEBUG=1 LOCALSTACK_API_KEY=test TEST_SKIP_LOCALSTACK_START=1 \
  pytest tests/aws/services/transfer/ -v
```

---

## 10. Success Criteria (All Met)

1. ✅ `python -m localstack.runtime.main` reaches `Ready.` with no import errors
2. ✅ All core imports pass V1 validation
3. ✅ No Docker/container imports in retained code (V2)
4. ✅ Zero F401 unused import errors (V3)
5. ✅ `plux.PluginManager("localstack.aws.provider").load_all()` returns `[transfer]`
6. ✅ `localstack/packages/`, `localstack/dev/`, `localstack/utils/analytics/`, `localstack/utils/container_utils/`, `localstack/deprecations.py` do not exist
7. ✅ `[localstack.cloudformation.resource_providers]` and `[localstack.lambda.runtime_executor]` remain in `plux.ini` (empty) for downstream extensibility
8. ✅ Transfer is the only entry in `[localstack.aws.provider]`; framework is extensible by adding to that section
