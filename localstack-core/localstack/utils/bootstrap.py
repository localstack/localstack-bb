from __future__ import annotations

import functools
import logging
import os
import re
from collections.abc import Iterable
from functools import wraps

from localstack import config, constants
from localstack.config import is_env_not_false
from localstack.runtime import hooks
from localstack.utils.files import mkdir

LOG = logging.getLogger(__name__)

# Mandatory dependencies of services on other services
# - maps from API names to list of other API names that they _explicitly_ depend on: <service>:<dependent-services>
# - an explicit service dependency is a service without which another service's basic functionality breaks
# - this mapping is used when enabling strict service loading (use SERVICES env var to allow-list services)
# - do not add "optional" dependencies of services here, use API_DEPENDENCIES_OPTIONAL instead
API_DEPENDENCIES = {
    "dynamodb": ["dynamodbstreams"],
    # dynamodbstreams uses kinesis under the hood
    "dynamodbstreams": ["kinesis"],
    # es forwards all requests to opensearch (basically an API deprecation path in AWS)
    "es": ["opensearch"],
    "cloudformation": ["s3", "sts"],
    "lambda": ["s3", "sts"],
    # firehose currently only supports kinesis as source, this could become optional when more sources are supported
    "firehose": ["kinesis"],
    "transcribe": ["s3"],
    # secretsmanager uses lambda for rotation
    "secretsmanager": ["kms", "lambda"],
    # ssm uses secretsmanager for get_parameter
    "ssm": ["secretsmanager"],
}

# Optional dependencies of services on other services
# - maps from API names to list of other API names that they _optionally_ depend on: <service>:<dependent-services>
# - an optional service dependency is a service without which a service's basic functionality doesn't break,
#   but which is needed for certain features (f.e. for one of multiple integrations)
# - this mapping is used f.e. used for the selective test execution (localstack.testing.testselection)
# - only add optional dependencies of services here, use API_DEPENDENCIES for mandatory dependencies
API_DEPENDENCIES_OPTIONAL = {
    # firehose's optional dependencies are supported delivery stream destinations
    "firehose": ["es", "opensearch", "s3", "redshift"],
    "lambda": [
        "cloudwatch",  # Lambda metrics
        "dynamodbstreams",  # Event source mapping source
        "events",  # Lambda destination
        "logs",  # Function logging
        "kinesis",  # Event source mapping source
        "sqs",  # Event source mapping source + Lambda destination
        "sns",  # Lambda destination
        "sts",  # Credentials injection
        # Additional dependencies to Pro-only services are defined in ext
    ],
    "ses": ["sns"],
    "sns": ["sqs", "lambda", "firehose", "ses", "logs"],
    "sqs": ["cloudwatch"],
    "logs": ["lambda", "kinesis", "firehose"],
    "cloudformation": ["secretsmanager", "ssm", "lambda"],
    "events": ["lambda", "kinesis", "firehose", "sns", "sqs", "stepfunctions", "logs"],
    "stepfunctions": ["logs", "lambda", "dynamodb", "ecs", "sns", "sqs", "apigateway", "events"],
    "apigateway": [
        "s3",
        "sqs",
        "sns",
        "kinesis",
        "route53",
        "servicediscovery",
        "lambda",
        "dynamodb",
        "stepfunctions",
        "events",
    ],
    # This is for S3 notifications and S3 KMS key
    "s3": ["events", "sqs", "sns", "lambda", "kms"],
    # IAM and STS are tightly coupled
    "sts": ["iam"],
    "iam": ["sts"],
}

# composites define an abstract name like "serverless" that maps to a set of services
API_COMPOSITES = {
    "serverless": [
        "cloudformation",
        "cloudwatch",
        "iam",
        "sts",
        "lambda",
        "dynamodb",
        "apigateway",
        "s3",
    ],
    "cognito": ["cognito-idp", "cognito-identity"],
    "timestream": ["timestream-write", "timestream-query"],
}


def log_duration(name=None, min_ms=500):
    """Function decorator to log the duration of function invocations."""

    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from time import perf_counter

            start_time = perf_counter()
            try:
                return f(*args, **kwargs)
            finally:
                end_time = perf_counter()
                func_name = name or f.__name__
                duration = (end_time - start_time) * 1000
                if duration > min_ms:
                    LOG.info('Execution of "%s" took %.2fms', func_name, duration)

        return wrapped

    return wrapper


def setup_logging():
    """Determine and set log level. The singleton factory makes sure the logging is only set up once."""
    from localstack.logging.setup import setup_logging_from_config

    setup_logging_from_config()


# --------------
# INFRA STARTUP
# --------------


def resolve_apis(services: Iterable[str]) -> set[str]:
    """
    Resolves recursively for the given collection of services (e.g., ["serverless", "cognito"]) the list of actual
    API services that need to be included (e.g., {'dynamodb', 'cloudformation', 'logs', 'kinesis', 'sts',
    'cognito-identity', 's3', 'dynamodbstreams', 'apigateway', 'cloudwatch', 'lambda', 'cognito-idp', 'iam'}).

    More specifically, it does this by:
    (1) resolving and adding dependencies (e.g., "dynamodbstreams" requires "kinesis"),
    (2) resolving and adding composites (e.g., "serverless" describes an ensemble
            including "iam", "lambda", "dynamodb", "apigateway", "s3", "sns", and "logs"), and
    (3) removing duplicates from the list.

    :param services: a collection of services that can include composites (e.g., "serverless").
    :returns a set of canonical service names
    """
    stack = []
    result = set()

    # perform a graph search
    stack.extend(services)
    while stack:
        service = stack.pop()

        if service in result:
            continue

        # resolve composites (like "serverless"), but do not add it to the list of results
        if service in API_COMPOSITES:
            stack.extend(API_COMPOSITES[service])
            continue

        result.add(service)

        # add dependencies to stack
        if service in API_DEPENDENCIES:
            stack.extend(API_DEPENDENCIES[service])

    return result


@functools.lru_cache
def get_enabled_apis() -> set[str]:
    """
    Returns the list of APIs that are enabled through the combination of the SERVICES variable and
    STRICT_SERVICE_LOADING variable. If the SERVICES variable is empty, then it will return all available services.
    Meta-services like "serverless" or "cognito", and dependencies are resolved.

    The result is cached, so it's safe to call. Clear the cache with get_enabled_apis.cache_clear().
    """
    from localstack.services.plugins import SERVICE_PLUGINS

    services_env = os.environ.get("SERVICES", "").strip()
    services = SERVICE_PLUGINS.list_available()

    if services_env and is_env_not_false("STRICT_SERVICE_LOADING"):
        # SERVICES and STRICT_SERVICE_LOADING are set
        # we filter the result of SERVICE_PLUGINS.list_available() to cross the user-provided list with
        # the available ones
        enabled_services = []
        for service_port in re.split(r"\s*,\s*", services_env):
            # Only extract the service name, discard the port
            parts = re.split(r"[:=]", service_port)
            service = parts[0]
            enabled_services.append(service)

        services = [service for service in enabled_services if service in services]
        # TODO: log a message if a service was not supported? see with pro loading

    return resolve_apis(services)


def is_api_enabled(api: str) -> bool:
    return api in get_enabled_apis()


@functools.lru_cache
def get_preloaded_services() -> set[str]:
    """
    Returns the list of APIs that are marked to be eager loaded through the combination of SERVICES variable and
    EAGER_SERVICE_LOADING. If the SERVICES variable is empty, then it will return all available services.
    Meta-services like "serverless" or "cognito", and dependencies are resolved.

    The result is cached, so it's safe to call. Clear the cache with get_preloaded_services.cache_clear().
    """
    services_env = os.environ.get("SERVICES", "").strip()
    services = []

    if services_env:
        # SERVICES and EAGER_SERVICE_LOADING are set
        # SERVICES env var might contain ports, but we do not support these anymore
        for service_port in re.split(r"\s*,\s*", services_env):
            # Only extract the service name, discard the port
            parts = re.split(r"[:=]", service_port)
            service = parts[0]
            services.append(service)

    if not services:
        from localstack.services.plugins import SERVICE_PLUGINS

        services = SERVICE_PLUGINS.list_available()

    return resolve_apis(services)


def start_infra_locally():
    from localstack.runtime.main import main

    return main()


@log_duration()
def prepare_host(console):
    """
    Prepare the host environment for running LocalStack, this should be called before start_infra_*.
    """
    if os.environ.get(constants.LOCALSTACK_INFRA_PROCESS) in constants.TRUE_STRINGS:
        return

    try:
        mkdir(config.VOLUME_DIR)
    except Exception as e:
        console.print(f"Error while creating volume dir {config.VOLUME_DIR}: {e}")
        if config.DEBUG:
            console.print_exception()

    setup_logging()
    hooks.prepare_host.run()


def in_ci():
    """Whether or not we are running in a CI environment"""
    for key in ("CI", "TRAVIS"):
        if os.environ.get(key, "") not in [False, "", "0", "false"]:
            return True
    return False


def is_auth_token_configured() -> bool:
    """Whether an API key is set in the environment."""
    return (
        True
        if os.environ.get("LOCALSTACK_AUTH_TOKEN", "").strip()
        or os.environ.get("LOCALSTACK_API_KEY", "").strip()
        else False
    )
