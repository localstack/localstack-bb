# LocalStack Core Framework Extraction — Specification

## 1. Objective

Strip the LocalStack monorepo of all AWS service provider implementations, leaving a clean, deployable core framework that:

- Receives, parses, and dispatches AWS API requests via the existing protocol stack
- Exposes a functioning plugin/extension system so service implementations can be loaded externally
- Retains the full lifecycle management runtime (ASF), persistence infrastructure, telemetry pipeline, packaging framework, and HTTP gateway
- Produces a minimal, dependency-lean Python package and Docker image that third-party or downstream service plugins can extend

The resulting codebase is a **framework skeleton**, not a working AWS emulator. No service endpoints should respond with business logic by default; the framework should start cleanly, log that no providers are registered, and return a structured 501 for any AWS API call that hits an unregistered service.

---

## 2. Scope

### 2.1 In Scope (retain)

| Area | Path | Rationale |
|------|------|-----------|
| AWS protocol gateway | `localstack/aws/app.py`, `chain.py`, `handlers/`, `protocol/`, `serving/`, `skeleton.py`, `spec.py`, `forwarder.py` | Core request parsing and dispatch; service-agnostic |
| AWS API specs | `localstack/aws/api/` | Needed by the protocol layer to parse/validate any AWS request; generated files, not service logic |
| AWS client utilities | `localstack/aws/connect.py`, `client.py`, `accounts.py`, `scaffold.py` | Internal client factory, boto3 patching, account management |
| Service plugin system | `localstack/services/plugins.py` | Plugin registry and loader; the mechanism by which services attach — keep the chassis, remove the passengers |
| Provider registry | `localstack/services/providers.py` | Factory function registry; all current service entries are removed but the module is retained as the canonical place for new providers to register themselves |
| Moto service adapter | `localstack/services/moto.py` | Wraps moto backends as LocalStack providers; essential scaffolding for quickly adding a new moto-backed service without writing a full provider |
| Service state helpers | `localstack/services/stores.py` | Common state patterns (`AccountRegionBundle`, `BackendDict`, `CrossAccountAttribute`) used by any service provider; must be available for new providers to import |
| Edge router | `localstack/services/edge.py` | Routes inbound traffic to service handlers |
| Internal service utilities | `localstack/services/internal.py` | Framework-level internal APIs (health, ready, info endpoints) |
| Service package installers | `localstack/packages/java.py`, `ffmpeg.py`, `debugpy.py` | Binary dependency installers for common service patterns (Java-based services, media processing, debug mode); kept so new service providers can declare these as package dependencies without reimplementing the installers |
| ASF runtime | `localstack/runtime/` (all files) | Lifecycle: startup, shutdown, init scripts, hook system, event bus |
| HTTP layer | `localstack/http/` (all files) | ASGI/WSGI serving, tracing, routing |
| State & persistence | `localstack/state/` (all files) | StateContainer protocol, codecs, snapshot framework |
| Package management framework | `localstack/packages/api.py`, `core.py`, `plugins.py` | Binary dependency installer framework; no service-specific installers |
| Configuration | `localstack/config.py`, `constants.py`, `deprecations.py` | Keep framework-level variables; prune service-specific config (see §4.3) |
| Plugin root | `localstack/plugins.py` | Top-level plugin entry point |
| Telemetry/analytics | `localstack/utils/analytics/` | Usage metrics pipeline |
| General utilities | `localstack/utils/` (most) | Networking, crypto, JSON, XML, HTTP, collections, etc. |
| Development utilities | `localstack/dev/` (most) | Bootstrap, Docker helpers, process runners, test utilities |
| Testing framework | `localstack/testing/` | Pytest plugin, fixtures, snapshot testing — kept for downstream consumers |
| Extension framework | `localstack/extensions/` | Public extension API |
| DNS | `localstack/dns/` | Framework-level DNS resolution |
| CLI | `localstack/cli/` | Package management CLI |
| Logging | `localstack/logging/` | Structured logging infrastructure |
| OpenAPI spec | `localstack/aws/openapi.yaml`, `aws/spec-patches.json` | Protocol documentation |
| Docker entrypoint | `bin/docker-entrypoint.sh`, `bin/docker-helper.sh` | Container bootstrap |
| Build system | `pyproject.toml`, `Makefile`, `plux.ini` (trimmed) | Keep, prune service entries |

### 2.2 Out of Scope (remove)

| Area | Path | Rationale |
|------|------|-----------|
| All AWS service implementations | `localstack/services/<service>/` (all 39+) | Pure service business logic |
| Service-specific utilities | `localstack/utils/kinesis/`, `utils/cloudwatch/` | Utilities tightly coupled to individual services with no framework consumers |
| All service tests | `tests/aws/services/`, `tests/integration/services/` | Service-level integration/unit tests |
| Service-specific fixtures | Service-level `conftest.py` files | |
| CloudFormation templates in tests | `tests/aws/templates/`, `tests/aws/cdk_templates/` | Service test data |

---

## 3. Constraints

1. **No regressions to the plugin system.** The `plux`-based plugin API must remain fully functional so downstream service packages can register providers using the existing `@aws_provider()` decorator and `plux.ini` entry-point convention without modification.

2. **Framework must start and serve requests.** After stripping, `localstack start` (or the Docker container) must reach the `on_infra_ready` state without errors. Unknown service calls should receive a structured 501 response, not a crash.

3. **Public APIs must remain stable.** The following public APIs must not change signatures, locations, or semantics:
   - `localstack.services.plugins.aws_provider`
   - `localstack.services.plugins.Service`
   - `localstack.services.plugins.ServiceProvider`
   - `localstack.services.plugins.ServicePluginManager`
   - `localstack.runtime.hooks.*` decorators
   - `localstack.state.*` protocols
   - `localstack.extensions.api.*`
   - `localstack.packages.api.*`

4. **No circular imports introduced.** Each removal must be checked for import-graph side effects. Use `importlib` lazy loading where needed rather than introducing new module-level imports.

5. **Preserve plux entry-point namespaces.** Even if a namespace becomes empty (e.g. `[localstack.aws.provider]`), the section must remain in `plux.ini` so downstream packages can inject into it.

6. **Dependency minimization is secondary to correctness.** Remove only dependencies that are exclusively used by service implementations and have no framework usage. When in doubt, keep the dependency and annotate it as a candidate for future removal.

7. **No git history rewriting.** All changes go through normal commits on a feature branch; do not squash or force-push history.

8. **Tests that exercise the framework directly must continue to pass.** This includes unit tests for the HTTP layer, state system, runtime lifecycle, plugin loader, and config — but excludes service-level integration tests.

---

## 4. Component Inventory

### 4.1 Services Directory — Detailed Disposition

```
localstack/services/
├── plugins.py         KEEP   — plugin registry chassis
├── providers.py       KEEP   — factory function registry; all current entries removed, module retained
├── edge.py            KEEP   — framework edge router
├── internal.py        KEEP   — health/ready/info endpoints
├── moto.py            KEEP   — moto adapter; scaffolding for new moto-backed providers
├── stores.py          KEEP   — common state patterns (AccountRegionBundle, BackendDict)
├── acm/               REMOVE
├── acm_pca/           REMOVE
├── apigateway/        REMOVE (includes resource_providers/)
├── appsync/           REMOVE
├── athena/            REMOVE
├── batch/             REMOVE
├── ce/                REMOVE
├── cloudformation/    REMOVE (includes resource_providers/ — 100+ plugins)
├── cloudfront/        REMOVE
├── cloudtrail/        REMOVE
├── cloudwatch/        REMOVE
├── codecommit/        REMOVE
├── cognito_idp/       REMOVE
├── cognito_identity/  REMOVE
├── dms/               REMOVE
├── ds/                REMOVE
├── dynamodb/          REMOVE
├── ec2/               REMOVE (includes resource_providers/)
├── ecr/               REMOVE
├── ecs/               REMOVE
├── efs/               REMOVE
├── elasticache/       REMOVE
├── emr/               REMOVE
├── es/                REMOVE
├── events/            REMOVE
├── firehose/          REMOVE
├── glue/              REMOVE
├── iam/               REMOVE
├── iot/               REMOVE
├── kafka/             REMOVE
├── kinesis/           REMOVE
├── kms/               REMOVE
├── lambda_/           REMOVE (includes runtime executor plugin)
├── logs/              REMOVE
├── mediastore/        REMOVE
├── opensearch/        REMOVE
├── rds/               REMOVE
├── redshift/          REMOVE
├── resource_groups/   REMOVE
├── route53/           REMOVE
├── route53resolver/   REMOVE
├── s3/                REMOVE
├── s3control/         REMOVE
├── scheduler/         REMOVE
├── secretsmanager/    REMOVE
├── ses/               REMOVE
├── sns/               REMOVE
├── sqs/               REMOVE
├── ssm/               REMOVE
├── stepfunctions/     REMOVE
├── transcribe/        REMOVE
├── xray/              REMOVE
└── ...any others      REMOVE
```

### 4.2 plux.ini — Section Disposition

| Section | Action | Notes |
|---------|--------|-------|
| `[localstack.aws.provider]` | CLEAR entries, keep section | Remove all `<service>:default = ...` lines; section must remain for downstream packages |
| `[localstack.cloudformation.resource_providers]` | CLEAR entries, keep section | Remove all 100+ resource provider lines |
| `[localstack.lambda.runtime_executor]` | CLEAR entries, keep section | |
| `[localstack.packages]` | KEEP | Package installer entries are retained alongside their installer modules so new providers can declare these packages as dependencies |
| `[localstack.hooks.on_infra_start]` | PARTIAL | Remove service-specific hooks; keep framework hooks (analytics, DNS, etc.) |
| `[localstack.hooks.on_infra_shutdown]` | PARTIAL | Same as above |
| `[localstack.hooks.on_infra_ready]` | PARTIAL | Remove service-dependent init runners if any |
| `[localstack.hooks.configure]` | KEEP | Framework-level configure hooks |
| `[localstack.hooks.prepare_host]` | KEEP | Host preparation hooks |
| `[localstack.init.runner]` | KEEP | Python and shell init script runners |
| `[localstack.runtime.server]` | KEEP | Hypercorn and Twisted server backends |
| `[localstack.runtime.components]` | KEEP | AWS components registration |
| `[localstack.openapi.spec]` | KEEP | OpenAPI spec registration |
| `[localstack.utils.catalog]` | KEEP | Service catalog utilities |

### 4.3 pyproject.toml — Dependency Disposition

**Remove from `runtime` dependencies:**

| Package | Reason for removal |
|---------|--------------------|
| `aws-sam-translator` | Only used by CloudFormation SAM transform |
| `antlr4-python3-runtime` | Only used by Step Functions ASL parser |
| `jpype1` | Only used by Step Functions JSONata engine |
| `opensearch-py` | Only used by OpenSearch service provider |
| `kclpy-ext` | Only used by Kinesis consumer library |
| `localstack-dualstack-proxy` | Only used by S3/EC2 dual-stack endpoint handling |

**Retain (framework usage confirmed):**

| Package | Framework usage |
|---------|----------------|
| `plux` | Plugin system |
| `boto3` / `botocore` | Protocol layer, internal client factory, spec loading |
| `pydantic` | Request/response model validation |
| `werkzeug` | HTTP utilities used across the framework |
| `hypercorn` | ASGI server |
| `localstack-twisted` | Twisted reactor server backend |
| `openapi-core` | OpenAPI validation in handlers |
| `docker` | Container utilities in dev/ and packages/ |
| `jsonschema` | JSON schema validation in protocol layer |
| `rolo` | HTTP routing |
| `cryptography` | Used in utils/crypto.py |
| `moto-ext` | Required by `services/moto.py` adapter, which is retained to support new moto-backed providers |
| `pymongo` | Verify — if only used by a service, remove |
| `requests`, `urllib3` | HTTP utilities |
| `pyyaml` | Config and spec parsing |
| `click` | CLI |

**Dependency groups:**

- `base-runtime` group: prune service-specific entries
- `runtime` group: prune as above; verify no service imports remain
- `test` group: keep (testing framework is retained)
- `dev` group: keep
- `typehint` group: prune `boto3-stubs` service extras that have no framework usage; keep `mypy_boto3_s3` etc. only if referenced in framework code

### 4.4 config.py — Variable Disposition

Remove or stub out config variables that are exclusively service-specific. Do not remove variables that control framework behavior even if a service also consumes them.

**Remove:**
- `KINESIS_*` variables (Kinesis provider config)
- `DYNAMODB_*` variables (DynamoDB-local config)
- `LAMBDA_*` variables (Lambda runtime config — all executor, network, docker settings)
- `S3_*` variables beyond `S3_SKIP_SIGNATURE_VALIDATION` if the latter has framework use
- `SQS_*` provider-specific variables
- `OPENSEARCH_*`, `ELASTICSEARCH_*` provider config
- `STEPFUNCTIONS_*` provider config
- `TRANSCRIBE_*` provider config
- `RDS_*` provider config

**Keep:**
- `SERVICES` — controls which plugins are loaded
- `DEBUG`, `LOG_LEVEL` — framework-wide
- `DATA_DIR`, `TMP_FOLDER`, `CACHE_DIR` — directory management
- `LOCALSTACK_HOST`, `GATEWAY_LISTEN`, `EDGE_PORT` — networking
- `PERSISTENCE` — state persistence toggle
- `SNAPSHOT_*` — snapshot system
- `DISABLE_EVENTS`, `SKIP_SSL_CERT_DOWNLOAD` — framework flags
- All `Directories` class internals

### 4.5 Service-Specific Utilities — Disposition

| Path | Action |
|------|--------|
| `localstack/utils/kinesis/` | REMOVE — exclusively used by Kinesis provider |
| `localstack/utils/cloudwatch/` | REMOVE — exclusively used by CloudWatch provider |
| `localstack/utils/aws/` | PARTIAL — keep AWS utility functions used by the framework (auth, arns, protocol), remove service-specific helpers |
| `localstack/dev/aws/` | PARTIAL — keep framework test utilities, remove service-specific mock builders |

### 4.6 Packages Directory — Disposition

| File | Action |
|------|--------|
| `localstack/packages/api.py` | KEEP |
| `localstack/packages/core.py` | KEEP |
| `localstack/packages/plugins.py` | KEEP |
| `localstack/packages/java.py` | KEEP — reusable installer for any Java-based service provider (DynamoDB-local, Kinesis mock, Step Functions); new providers depend on it |
| `localstack/packages/ffmpeg.py` | KEEP — reusable installer for media-processing service providers |
| `localstack/packages/debugpy.py` | KEEP — reusable debug-mode installer available to any provider |

### 4.7 Test Directory — Disposition

| Path | Action |
|------|--------|
| `tests/aws/services/` | REMOVE |
| `tests/aws/templates/` | REMOVE |
| `tests/aws/cdk_templates/` | REMOVE |
| `tests/aws/serverless/` | REMOVE |
| `tests/aws/terraform/` | REMOVE |
| `tests/aws/scenario/` | REMOVE |
| `tests/integration/services/` | REMOVE |
| `tests/integration/aws/` | PARTIAL — remove service tests, keep protocol/gateway tests |
| `tests/unit/` | PARTIAL — remove service unit tests, keep framework unit tests |
| `tests/bootstrap/` | KEEP — framework init tests |
| `tests/performance/` | PARTIAL — remove service benchmarks |
| `tests/integration/docker_utils/` | KEEP |
| `tests/integration/dns/` | KEEP |
| `tests/integration/utils/` | KEEP |

---

## 5. Step-by-Step Plan

### Phase 0 — Setup (Pre-work)

**Step 0.1 — Create feature branch**
```
git checkout -b chore/strip-service-implementations
```

**Step 0.2 — Capture baseline metrics**
- Record current: package count in `plux.ini`, total line count, number of test files, `pip install --dry-run` dependency list
- Save to `scripts/strip-baseline.txt` for comparison after each phase

**Step 0.3 — Identify all cross-references**
- For each service directory, run a reverse import search to identify any framework files that import from it
- Build an import dependency graph: `python -c "import localstack.services.<svc>.provider"` and log any framework-level callers
- Output a `scripts/cross-refs.txt` report; this list drives the order of removals to avoid breaking framework imports

**Step 0.4 — Tag current HEAD**
```
git tag pre-strip-baseline
```

---

### Phase 1 — Remove Service Implementations

Work service-by-service. For each service, the micro-process is:

1. Delete `localstack/services/<service>/` directory
2. Remove any import of that service in `localstack/services/providers.py`
3. Run `python -c "import localstack.aws.app"` to verify no import error
4. Commit: `chore(strip): remove <service> provider`

**Step 1.1 — Remove low-risk, lightly-coupled services first**

Services with no resource providers and no external package dependencies:
- `acm`, `acm_pca`, `athena`, `batch`, `ce`, `codecommit`, `cognito_identity`, `dms`, `ds`
- `ecr`, `ecs`, `efs`, `elasticache`, `emr`, `es`, `glue`, `iot`
- `kafka`, `mediastore`, `redshift`, `resource_groups`, `route53resolver`
- `transcribe`, `xray`

**Step 1.2 — Remove medium-complexity services**

Services with resource providers or moderate cross-references:
- `cloudfront`, `cloudtrail`, `cloudwatch`, `appsync`
- `cognito_idp`, `firehose`, `scheduler`, `ses`, `ssm`
- `secretsmanager`, `route53`, `s3control`

**Step 1.3 — Remove core services with resource providers**

Services that have extensive CloudFormation resource provider plugins:
- `ec2` — has EC2 resource providers (VPC, subnet, security group, etc.)
- `iam` — has IAM resource providers (role, policy, user)
- `apigateway` — has API Gateway resource providers
- `logs`, `kms`, `rds`, `opensearch`

**Step 1.4 — Remove high-complexity services**

The most interconnected services, removed last to avoid cascading errors:
- `kinesis` — used by other services as event source
- `sqs` — used by SNS, Lambda event sources
- `sns` — has publisher infrastructure with cross-service integrations
- `events` (EventBridge) — has cross-service targets
- `dynamodb` — DynamoDB-local package dependency
- `s3` — S3Provider has cross-service hooks (SNS, SQS notifications)
- `stepfunctions` — antlr/jpype dependency
- `lambda_` — most complex; runtime executor plugins, Docker integration, event source mappings
- `cloudformation` — 100+ resource provider plugins; remove last

For CloudFormation specifically:
1. Delete all `localstack/services/cloudformation/resource_providers/` first (100+ plugin files)
2. Then delete the rest of `localstack/services/cloudformation/`

**Step 1.5 — Clear service factory functions from `providers.py`**

After all service directories are deleted:
- Remove all `def <service>(...)` factory functions from `localstack/services/providers.py`; leave the module structure, imports, and any helper utilities intact
- Do **not** delete `providers.py`, `moto.py`, or `stores.py` — these are retained as scaffolding for new providers
- Verify `localstack/services/plugins.py` and `localstack/services/moto.py` import cleanly in isolation

---

### Phase 2 — Clean Up plux.ini

**Step 2.1 — Clear `[localstack.aws.provider]`**
- Remove all service provider entries
- Leave the section header in place with a comment: `# Service providers registered by downstream packages`

**Step 2.2 — Clear `[localstack.cloudformation.resource_providers]`**
- Remove all 100+ resource provider entries
- Leave section header with comment

**Step 2.3 — Clear `[localstack.lambda.runtime_executor]`**
- Remove the Lambda runtime executor entry
- Leave section header

**Step 2.4 — Retain `[localstack.packages]`**
- Keep all package installer entries (`dynamodb-local`, `elasticsearch`, `opensearch`, `kinesis-mock`, `lambda-runtime`, `jpype-jsonata`, `vosk`, `ffmpeg`, `java`) unchanged
- The installer modules (`java.py`, `ffmpeg.py`, `debugpy.py`) are retained so new providers can declare these as package dependencies

**Step 2.5 — Audit `[localstack.hooks.*]` sections**
- Enumerate all hook registrations; cross-reference with removed service directories
- Remove hooks whose implementing module no longer exists
- Keep all hooks whose module is in a retained path

**Step 2.6 — Validate plux.ini**
```bash
python -c "import plux; plux.PluginManager('localstack.aws.provider').load_all()"
```
This must succeed with zero providers loaded (not an error).

---

### Phase 3 — Prune Dependencies

**Step 3.1 — Update `pyproject.toml`**
- Remove from `[project.optional-dependencies] runtime`: `aws-sam-translator`, `antlr4-python3-runtime`, `jpype1`, `opensearch-py`, `kclpy-ext`, `localstack-dualstack-proxy`
- Keep `moto-ext` — required by the retained `services/moto.py` adapter
- Remove from `base-runtime` any service-specific packages confirmed absent after Phase 1
- Annotate each removed package with a comment noting which service used it

**Step 3.2 — Update requirements files**
- Re-run the freeze process for each requirements tier:
  ```
  make freeze
  ```
- Alternatively, manually remove the confirmed-absent packages from:
  - `requirements-base-runtime.txt`
  - `requirements-runtime.txt`
  - `requirements-test.txt` (only if test deps were service-specific)

**Step 3.3 — Retain service package installers**
- Keep `localstack/packages/java.py`, `ffmpeg.py`, and `debugpy.py` unchanged
- Verify all imports in `packages/plugins.py` still resolve after service directories are deleted (the installers themselves have no service-directory imports)

**Step 3.4 — Verify installation**
```bash
pip install -e ".[runtime]" --dry-run 2>&1 | grep -E "Would install|error"
```
Confirm no resolution errors and the install count has decreased.

---

### Phase 4 — Prune Configuration

**Step 4.1 — Audit `config.py` for service-specific variables**
- Use a script to find all `LAMBDA_*`, `KINESIS_*`, `DYNAMODB_*`, `SQS_*`, `SNS_*`, `S3_*`, `OPENSEARCH_*`, `STEPFUNCTIONS_*` variables
- For each: grep the retained codebase for usages outside service directories
- Remove variables that have zero references in retained code
- Keep variables that cross-cut (e.g., feature flags, port configs used by the framework's SERVICES loader)

**Step 4.2 — Audit `constants.py`**
- Remove service-specific constants (service names hardcoded as strings, magic values only used in service code)
- Keep constants used by the protocol framework and routing

**Step 4.3 — Audit `deprecations.py`**
- Remove deprecation notices for removed service-specific config variables
- Keep deprecations for framework-level variables

---

### Phase 5 — Prune Utilities

**Step 5.1 — Remove `localstack/utils/kinesis/`**
- Delete entire directory
- Check for any imports outside the removed Kinesis service

**Step 5.2 — Remove `localstack/utils/cloudwatch/`**
- Delete entire directory
- Check for any imports outside removed CloudWatch service

**Step 5.3 — Audit `localstack/utils/aws/`**
- Run grep for each function/class exported from this module
- Remove helper functions that are exclusively used by removed service code
- Keep utilities used by: `aws/handlers/`, `aws/protocol/`, `runtime/`, `testing/`

**Step 5.4 — Audit `localstack/dev/`**
- Remove service-specific mock builders and test helpers for deleted services
- Keep: `bootstrap.py`, `docker_utils.py`, `run.py`, `server/`, `kubernetes/`, `debugger/`, `analytics/`

---

### Phase 6 — Prune Tests

**Step 6.1 — Remove service test directories**
```
rm -rf tests/aws/services/
rm -rf tests/aws/templates/
rm -rf tests/aws/cdk_templates/
rm -rf tests/aws/serverless/
rm -rf tests/aws/terraform/
rm -rf tests/aws/scenario/
rm -rf tests/integration/services/
```

**Step 6.2 — Audit remaining test directories**
- `tests/unit/` — remove any test module that imports from a removed service directory
- `tests/integration/aws/` — audit file by file; remove service-level tests, keep protocol tests
- `tests/bootstrap/` — review; keep framework bootstrap tests, remove service-init tests
- `tests/performance/` — remove service benchmarks

**Step 6.3 — Prune `conftest.py` files**
- Remove all service-level pytest fixtures (AWS service clients for removed services)
- Keep framework-level fixtures: gateway URL, account ID, region, Docker client, etc.
- Verify `pytest --collect-only` runs without import errors

---

### Phase 7 — Update Docker

**Step 7.1 — Audit `Dockerfile`**
- Remove `apt` packages only needed by removed services (e.g., Java runtime for DynamoDB-local)
- Remove Node.js installation if only used by a Lambda runtime (verify Lambda executor removed)
- Remove any `COPY` or `RUN` steps that install service-specific binaries

**Step 7.2 — Remove `Dockerfile.s3`**
- This file is an S3-only image variant; it should be removed or repurposed as a documentation artifact since S3 is no longer bundled

**Step 7.3 — Update `docker-compose.yml`**
- Remove service-specific environment variables
- Simplify to the minimal set needed to start the stripped framework

**Step 7.4 — Update `bin/docker-entrypoint.sh`**
- Remove any service-specific initialization steps (e.g., waiting for DynamoDB-local to start, initializing Kinesis mock)

---

### Phase 8 — Validation

**Step 8.1 — Import validation**
```bash
python -c "
import localstack.aws.app
import localstack.runtime.runtime
import localstack.services.plugins
import localstack.state.core
import localstack.packages.api
import localstack.extensions.api
print('All core imports OK')
"
```

**Step 8.2 — Framework startup test**
```bash
# Start the framework
SERVICES="" localstack start --host 2>&1 | head -50
# Framework should reach 'Ready.' state with no service providers registered
```

**Step 8.3 — Plugin system test**
- Write a minimal in-memory test provider using the existing `@aws_provider()` decorator
- Register it via a temporary `plux.ini` test entry
- Confirm it loads and responds to requests

**Step 8.4 — Run retained unit tests**
```bash
pytest tests/unit/ tests/integration/docker_utils/ tests/integration/dns/ tests/integration/utils/ tests/bootstrap/ -x -q
```
All tests in these directories must pass.

**Step 8.5 — Dependency audit**
```bash
pip install pipdeptree
pipdeptree --packages localstack-core
# Confirm no removed service packages appear in the dependency tree
```

**Step 8.6 — plux audit**
```bash
python -c "
import plux
for ns in [
    'localstack.aws.provider',
    'localstack.cloudformation.resource_providers',
    'localstack.packages',
]:
    plugins = plux.PluginManager(ns).load_all()
    print(f'{ns}: {len(plugins)} plugins')
"
# localstack.aws.provider should show 0 plugins
```

**Step 8.7 — Regression: unknown service returns 501**
```bash
localstack start &
sleep 10
aws --endpoint-url http://localhost:4566 s3 ls 2>&1
# Should return a structured error, not a crash or 500
```

---

### Phase 9 — Final Cleanup

**Step 9.1 — Dead import removal**
- Run `ruff check --select F401 localstack/` to find unused imports
- Fix or suppress each one
- Run `mypy localstack/` against the retained code to catch type errors introduced by removal

**Step 9.2 — Update `README.md`**
- Replace AWS service documentation with framework-only documentation
- Document how to register a service provider as an external plugin
- Document the retained framework components and their entry points

**Step 9.3 — Update `pyproject.toml` metadata**
- Update package description to reflect framework-only nature
- Update classifiers if needed
- Update `package_data` includes to remove references to deleted files

**Step 9.4 — Final baseline comparison**
- Compare `scripts/strip-baseline.txt` to current state
- Report: lines removed, packages removed, plux entries removed, test files removed

**Step 9.5 — Tag and PR**
```bash
git tag post-strip-v1
git push origin chore/strip-service-implementations
gh pr create --title "chore: strip service implementations, retain core framework"
```

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Framework module imports service code at module level | High | High | Run import graph analysis in Phase 0.3; fix before removing |
| `config.py` variable removal breaks framework hooks | Medium | High | Grep all removed variables in retained code before deletion |
| plux entry-point namespace gaps break downstream packages | Low | High | Keep all section headers; never delete a namespace, only clear entries |
| `providers.py` still imports removed service modules after clearing factory functions | Medium | High | After removing each service directory, immediately grep `providers.py` for residual imports and clean them up |
| `moto.py` or `stores.py` imports a service module that no longer exists | Low | High | Run `python -m py_compile localstack/services/moto.py` and `stores.py` after each service removal to catch broken imports early |
| Lambda executor removal leaves dead Docker network config | Low | Low | Audit `docker-entrypoint.sh` and `config.py` for Lambda network vars |
| Step Functions antlr runtime removal causes import-time crash in retained code | Low | High | Grep `antlr4` across retained modules before removing dependency |
| Service-specific hooks registered in retained `on_infra_start` entries | Medium | Medium | Audit each hook implementation path in Phase 2.5 |
| Test fixtures that import removed services break `conftest.py` collection | High | Medium | Run `pytest --collect-only` after each phase to catch early |

---

## 7. Success Criteria

The extraction is complete when all of the following are true:

1. `localstack start` completes to `Ready.` state with zero service providers registered
2. `pytest tests/unit/ tests/integration/docker_utils/ tests/integration/dns/ tests/bootstrap/ -q` exits 0
3. `python -c "import localstack.aws.app; import localstack.services.plugins"` exits 0
4. `plux.PluginManager("localstack.aws.provider").load_all()` returns an empty list
5. A test-only service plugin can be registered at runtime via `@aws_provider()` and responds to requests
6. The Docker image builds successfully from the stripped `Dockerfile`
7. The installed package has no dependency on `aws-sam-translator`, `antlr4-python3-runtime`, `jpype1`, or `opensearch-py`; `moto-ext` is intentionally retained to support the moto service adapter
8. `ruff check localstack/` reports zero F401 (unused import) errors in retained code
