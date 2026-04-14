import logging
import os

from localstack.runtime import hooks
from localstack.utils.analytics import log

LOG = logging.getLogger(__name__)

# Config options for which both usage and values are reported in analytics.
# Important: This list must only contain options whose values do not contain PII or sensitive data.
TRACKED_ENV_VAR = [
    "ACTIVATE_PRO",
    "ALLOW_NONSTANDARD_REGIONS",
    "CONTAINER_RUNTIME",
    "DEBUG",
    "DEFAULT_REGION",  # Not functional; deprecated in 0.12.7, removed in 3.0.0
    "DISABLE_CORS_CHECK",
    "DISABLE_CORS_HEADERS",
    "DNS_ADDRESS",
    "EAGER_SERVICE_LOADING",
    "EDGE_PORT",
    "ES_CUSTOM_BACKEND",  # deprecated in 0.14.0, removed in 3.0.0
    "ES_MULTI_CLUSTER",  # deprecated in 0.14.0, removed in 3.0.0
    "ES_ENDPOINT_STRATEGY",  # deprecated in 0.14.0, removed in 3.0.0
    "LEGACY_EDGE_PROXY",  # Not functional; deprecated in 1.0.0, removed in 2.0.0
    "LS_LOG",
    "MOCK_UNIMPLEMENTED",  # Not functional; deprecated in 1.3.0, removed in 3.0.0
    "PERSISTENCE",
    "REQUIRE_PRO",
    "SERVICES",
    "STRICT_SERVICE_LOADING",
    "SKIP_INFRA_DOWNLOADS",
    "USE_SINGLE_REGION",  # Not functional; deprecated in 0.12.7, removed in 3.0.0
    "USE_SSL",
]

# Config options for which only the usage is reported in analytics.
# Use this for options which may hold sensitive data or PII.
PRESENCE_ENV_VAR = [
    "DATA_DIR",
    "EDGE_FORWARD_URL",  # Not functional; deprecated in 1.4.0, removed in 3.0.0
    "GATEWAY_LISTEN",
    "HOSTNAME",
    "HOSTNAME_EXTERNAL",
    "HOST_TMP_FOLDER",  # Not functional; deprecated in 1.0.0, removed in 2.0.0
    "INIT_SCRIPTS_PATH",  # Not functional; deprecated in 1.1.0, removed in 2.0.0
    "LEGACY_DIRECTORIES",  # Not functional; deprecated in 1.1.0, removed in 2.0.0
    "LEGACY_INIT_DIR",  # Not functional; deprecated in 1.1.0, removed in 2.0.0
    "LOCALSTACK_HOST",
    "LOCALSTACK_HOSTNAME",
    "OUTBOUND_HTTP_PROXY",
    "OUTBOUND_HTTPS_PROXY",
    "TMPDIR",
]


@hooks.on_infra_start()
def _publish_config_as_analytics_event():
    env_vars = list(TRACKED_ENV_VAR)

    for key, value in os.environ.items():
        if key.startswith("PROVIDER_OVERRIDE_"):
            env_vars.append(key)
        elif key.startswith("SYNCHRONOUS_") and key.endswith("_EVENTS"):
            # these config variables have been removed with 3.0.0
            env_vars.append(key)

    env_vars = {key: os.getenv(key) for key in env_vars}
    present_env_vars = {env_var: 1 for env_var in PRESENCE_ENV_VAR if os.getenv(env_var)}

    # filter out irrelevant None values, making the payload significantly smaller.
    env_vars = {k: v for k, v in env_vars.items() if v is not None}
    present_env_vars = {k: v for k, v in present_env_vars.items() if v is not None}

    log.event("config", env_vars=env_vars, set_vars=present_env_vars)
