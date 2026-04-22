import ipaddress
import logging
import os
import platform
import re
import socket
import tempfile
import time
import warnings
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, TypeVar

from localstack import constants
from localstack.constants import (
    DEFAULT_VOLUME_DIR,
    ENV_INTERNAL_TEST_COLLECT_METRIC,
    ENV_INTERNAL_TEST_RUN,
    ENV_INTERNAL_TEST_STORE_METRICS_IN_LOCALSTACK,
    FALSE_STRINGS,
    LOCALHOST,
    LOCALHOST_IP,
    LOCALSTACK_ROOT_FOLDER,
    LOG_LEVELS,
    TRACE_LOG_LEVELS,
    TRUE_STRINGS,
)

T = TypeVar("T", str, int)

# keep track of start time, for performance debugging
load_start_time = time.time()


class Directories:
    """
    Holds different directories available to localstack. Some directories are shared between the host and the
    localstack container, some live only on the host and others in the container.

    Attributes:
        static_libs: container only; binaries and libraries statically packaged with the image
        var_libs:    shared; binaries and libraries+data computed at runtime: lazy-loaded binaries, ssl cert, ...
        cache:       shared; ephemeral data that has to persist across localstack runs and reboots
        tmp:         container only; ephemeral data that has to persist across localstack runs but not reboots
        mounted_tmp: shared; same as above, but shared for persistence across different containers, tests, ...
        functions:   shared; volume to communicate between host<->lambda containers
        data:        shared; holds localstack state, pods, ...
        config:      host only; pre-defined configuration values, cached credentials, machine id, ...
        init:        shared; user-defined provisioning scripts executed in the container when it starts
        logs:        shared; log files produced by localstack
    """

    static_libs: str
    var_libs: str
    cache: str
    tmp: str
    mounted_tmp: str
    functions: str
    data: str
    config: str
    init: str
    logs: str

    def __init__(
        self,
        static_libs: str,
        var_libs: str,
        cache: str,
        tmp: str,
        mounted_tmp: str,
        functions: str,
        data: str,
        config: str,
        init: str,
        logs: str,
    ) -> None:
        super().__init__()
        self.static_libs = static_libs
        self.var_libs = var_libs
        self.cache = cache
        self.tmp = tmp
        self.mounted_tmp = mounted_tmp
        self.functions = functions
        self.data = data
        self.config = config
        self.init = init
        self.logs = logs

    @staticmethod
    def defaults() -> "Directories":
        """Returns Localstack directory paths based on the localstack filesystem hierarchy."""
        return Directories(
            static_libs="/usr/lib/localstack",
            var_libs=f"{DEFAULT_VOLUME_DIR}/lib",
            cache=f"{DEFAULT_VOLUME_DIR}/cache",
            tmp=os.path.join(tempfile.gettempdir(), "localstack"),
            mounted_tmp=f"{DEFAULT_VOLUME_DIR}/tmp",
            functions=f"{DEFAULT_VOLUME_DIR}/tmp",  # FIXME: remove - this was misconceived
            data=f"{DEFAULT_VOLUME_DIR}/state",
            logs=f"{DEFAULT_VOLUME_DIR}/logs",
            config="/etc/localstack/conf.d",  # for future use
            init="/etc/localstack/init",
        )

    @staticmethod
    def for_container() -> "Directories":
        """
        Returns Localstack directory paths as they are defined within the container. Everything shared and writable
        lives in /var/lib/localstack or {tempfile.gettempdir()}/localstack.

        :returns: Directories object
        """
        defaults = Directories.defaults()

        return Directories(
            static_libs=defaults.static_libs,
            var_libs=defaults.var_libs,
            cache=defaults.cache,
            tmp=defaults.tmp,
            mounted_tmp=defaults.mounted_tmp,
            functions=defaults.functions,
            data=defaults.data if PERSISTENCE else os.path.join(defaults.tmp, "state"),
            config=defaults.config,
            logs=defaults.logs,
            init=defaults.init,
        )

    @staticmethod
    def for_host() -> "Directories":
        """Return directories used for running localstack in host mode. Note that these are *not* the directories
        that are mounted into the container when the user starts localstack."""
        root = os.environ.get("FILESYSTEM_ROOT") or os.path.join(
            LOCALSTACK_ROOT_FOLDER, ".filesystem"
        )
        root = os.path.abspath(root)

        defaults = Directories.for_container()

        tmp = os.path.join(root, defaults.tmp.lstrip("/"))
        data = os.path.join(root, defaults.data.lstrip("/"))

        return Directories(
            static_libs=os.path.join(root, defaults.static_libs.lstrip("/")),
            var_libs=os.path.join(root, defaults.var_libs.lstrip("/")),
            cache=os.path.join(root, defaults.cache.lstrip("/")),
            tmp=tmp,
            mounted_tmp=os.path.join(root, defaults.mounted_tmp.lstrip("/")),
            functions=os.path.join(root, defaults.functions.lstrip("/")),
            data=data if PERSISTENCE else os.path.join(tmp, "state"),
            config=os.path.join(root, defaults.config.lstrip("/")),
            init=os.path.join(root, defaults.init.lstrip("/")),
            logs=os.path.join(root, defaults.logs.lstrip("/")),
        )

    @staticmethod
    def for_cli() -> "Directories":
        """Returns directories used for when running localstack CLI commands from the host system. Unlike
        ``for_container``, these needs to be cross-platform. Ideally, this should not be needed at all,
        because the localstack runtime and CLI do not share any control paths. There are a handful of
        situations where directories or files may be created lazily for CLI commands. Some paths are
        intentionally set to None to provoke errors if these paths are used from the CLI - which they
        shouldn't. This is a symptom of not having a clear separation between CLI/runtime code, which will
        be a future project."""
        import tempfile

        from localstack.utils import files

        tmp_dir = os.path.join(tempfile.gettempdir(), "localstack-cli")
        cache_dir = (files.get_user_cache_dir()).absolute() / "localstack-cli"

        return Directories(
            static_libs=None,
            var_libs=None,
            cache=str(cache_dir),  # used by analytics metadata
            tmp=tmp_dir,
            mounted_tmp=tmp_dir,
            functions=None,
            data=os.path.join(tmp_dir, "state"),  # used by localstack-pro config TODO: remove
            logs=os.path.join(tmp_dir, "logs"),  # used for container logs
            config=None,  # in the context of the CLI, config.CONFIG_DIR should be used
            init=None,
        )

    def mkdirs(self):
        for folder in [
            self.static_libs,
            self.var_libs,
            self.cache,
            self.tmp,
            self.mounted_tmp,
            self.functions,
            self.data,
            self.config,
            self.init,
            self.logs,
        ]:
            if folder and not os.path.exists(folder):
                try:
                    os.makedirs(folder)
                except Exception:
                    # this can happen due to a race condition when starting
                    # multiple processes in parallel. Should be safe to ignore
                    pass

    def __str__(self):
        return str(self.__dict__)


def eval_log_type(env_var_name: str) -> str | bool:
    """Get the log type from environment variable"""
    ls_log = os.environ.get(env_var_name, "").lower().strip()
    return ls_log if ls_log in LOG_LEVELS else False


def parse_boolean_env(env_var_name: str) -> bool | None:
    """Parse the value of the given env variable and return True/False, or None if it is not a boolean value."""
    value = os.environ.get(env_var_name, "").lower().strip()
    if value in TRUE_STRINGS:
        return True
    if value in FALSE_STRINGS:
        return False
    return None


def parse_comma_separated_list(env_var_name: str) -> list[str]:
    """Parse a comma separated list from the given environment variable."""
    return os.environ.get(env_var_name, "").strip().split(",")


def is_env_true(env_var_name: str) -> bool:
    """Whether the given environment variable has a truthy value."""
    return os.environ.get(env_var_name, "").lower().strip() in TRUE_STRINGS


def is_env_not_false(env_var_name: str) -> bool:
    """Whether the given environment variable is empty or has a truthy value."""
    return os.environ.get(env_var_name, "").lower().strip() not in FALSE_STRINGS


def load_environment(profiles: str = None, env=os.environ) -> list[str]:
    """Loads the environment variables from ~/.localstack/{profile}.env, for each profile listed in the profiles.
    :param env: environment to load profile to. Defaults to `os.environ`
    :param profiles: a comma separated list of profiles to load (defaults to "default")
    :returns str: the list of the actually loaded profiles (might be the fallback)
    """
    if not profiles:
        profiles = "default"

    profiles = profiles.split(",")
    environment = {}
    import dotenv

    for profile in profiles:
        profile = profile.strip()
        path = os.path.join(CONFIG_DIR, f"{profile}.env")
        if not os.path.exists(path):
            continue
        environment.update(dotenv.dotenv_values(path))

    for k, v in environment.items():
        # we do not want to override the environment
        if k not in env and v is not None:
            env[k] = v

    return profiles


def is_persistence_enabled() -> bool:
    return PERSISTENCE and dirs.data


def is_linux() -> bool:
    return platform.system() == "Linux"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_wsl() -> bool:
    return platform.system().lower() == "linux" and os.environ.get("WSL_DISTRO_NAME") is not None


def in_docker():
    """
    Returns True if running in a docker container, else False
    Ref. https://docs.docker.com/config/containers/runmetrics/#control-groups
    """
    if OVERRIDE_IN_DOCKER is not None:
        return OVERRIDE_IN_DOCKER

    # check some marker files that we create in our Dockerfiles
    for path in [
        "/usr/lib/localstack/.community-version",
        "/usr/lib/localstack/.pro-version",
        "/tmp/localstack/.marker",
    ]:
        if os.path.isfile(path):
            return True

    # details: https://github.com/localstack/localstack/pull/4352
    if os.path.exists("/.dockerenv"):
        return True
    if os.path.exists("/run/.containerenv"):
        return True

    if not os.path.exists("/proc/1/cgroup"):
        return False
    try:
        if any(
            [
                os.path.exists("/sys/fs/cgroup/memory/docker/"),
                any(
                    "docker-" in file_names
                    for file_names in os.listdir("/sys/fs/cgroup/memory/system.slice")
                ),
                os.path.exists("/sys/fs/cgroup/docker/"),
                any(
                    "docker-" in file_names
                    for file_names in os.listdir("/sys/fs/cgroup/system.slice/")
                ),
            ]
        ):
            return False
    except Exception:
        pass
    with open("/proc/1/cgroup") as ifh:
        content = ifh.read()
        if "docker" in content or "buildkit" in content:
            return True
        os_hostname = socket.gethostname()
        if os_hostname and os_hostname in content:
            return True

    # containerd does not set any specific file or config, but it does use
    # io.containerd.snapshotter.v1.overlayfs as the overlay filesystem for `/`.
    try:
        with open("/proc/mounts") as infile:
            for line in infile:
                line = line.strip()

                if not line:
                    continue

                # skip comments
                if line[0] == "#":
                    continue

                # format (man 5 fstab)
                # <spec> <mount point> <type> <options> <rest>...
                parts = line.split()
                if len(parts) < 4:
                    # badly formatted line
                    continue

                mount_point = parts[1]
                options = parts[3]

                # only consider the root filesystem
                if mount_point != "/":
                    continue

                if "io.containerd" in options:
                    return True

    except FileNotFoundError:
        pass

    return False


# whether the `in_docker` check should always return True or False
OVERRIDE_IN_DOCKER = parse_boolean_env("OVERRIDE_IN_DOCKER")

is_in_docker = in_docker()
is_in_linux = is_linux()
is_in_macos = is_macos()
is_in_windows = is_windows()
is_in_wsl = is_wsl()
default_ip = "0.0.0.0" if is_in_docker else "127.0.0.1"

# CLI specific: host configuration directory
CONFIG_DIR = os.environ.get("CONFIG_DIR", os.path.expanduser("~/.localstack"))

# keep this on top to populate the environment
try:
    LOADED_PROFILES = load_environment("")
except ImportError:
    # dotenv may not be available in lambdas or other environments where config is loaded
    LOADED_PROFILES = None

# loaded components name - default: all components are loaded and the first one is chosen
RUNTIME_COMPONENTS = os.environ.get("RUNTIME_COMPONENTS", "").strip()

# directory for persisting data (TODO: deprecated, simply use PERSISTENCE=1)
DATA_DIR = os.environ.get("DATA_DIR", "").strip()

# whether localstack should persist service state across localstack runs
PERSISTENCE = is_env_true("PERSISTENCE")

# the strategy for loading snapshots from disk when `PERSISTENCE=1` is used (on_startup, on_request, manual)
SNAPSHOT_LOAD_STRATEGY = os.environ.get("SNAPSHOT_LOAD_STRATEGY", "").upper()

# the strategy saving snapshots to disk when `PERSISTENCE=1` is used (on_shutdown, on_request, scheduled, manual)
SNAPSHOT_SAVE_STRATEGY = os.environ.get("SNAPSHOT_SAVE_STRATEGY", "").upper()

# the flush interval (in seconds) for persistence when the snapshot save strategy is set to "scheduled"
SNAPSHOT_FLUSH_INTERVAL = int(os.environ.get("SNAPSHOT_FLUSH_INTERVAL") or 15)

# whether to clear config.dirs.tmp on startup and shutdown
CLEAR_TMP_FOLDER = is_env_not_false("CLEAR_TMP_FOLDER")

# folder for temporary files and data
TMP_FOLDER = os.path.join(tempfile.gettempdir(), "localstack")

# this is exclusively for the CLI to configure the container mount into /var/lib/localstack
VOLUME_DIR = os.environ.get("LOCALSTACK_VOLUME_DIR", "").strip() or TMP_FOLDER

# fix for Mac OS, to be able to mount /var/folders in Docker
if TMP_FOLDER.startswith("/var/folders/") and os.path.exists(f"/private{TMP_FOLDER}"):
    TMP_FOLDER = f"/private{TMP_FOLDER}"

# whether to enable verbose debug logging ("LOG" is used when using the CLI with LOCALSTACK_LOG instead of LS_LOG)
LS_LOG = eval_log_type("LS_LOG") or eval_log_type("LOG")
DEBUG = is_env_true("DEBUG") or LS_LOG in TRACE_LOG_LEVELS

# EXPERIMENTAL: allow setting custom log levels for individual loggers
LOG_LEVEL_OVERRIDES = os.environ.get("LOG_LEVEL_OVERRIDES", "")

# whether to assume http or https for `get_protocol`
USE_SSL = is_env_true("USE_SSL")

# Whether to report internal failures as 500 or 501 errors.
FAIL_FAST = is_env_true("FAIL_FAST")

# default encoding used to convert strings to byte arrays (mainly for Python 3 compatibility)
DEFAULT_ENCODING = "utf-8"


def is_trace_logging_enabled():
    if LS_LOG:
        log_level = str(LS_LOG).upper()
        return log_level.lower() in TRACE_LOG_LEVELS
    return False


# set log levels immediately, but will be overwritten later by setup_logging
if DEBUG:
    logging.getLogger("").setLevel(logging.DEBUG)
    logging.getLogger("localstack").setLevel(logging.DEBUG)

LOG = logging.getLogger(__name__)
if is_trace_logging_enabled():
    load_end_time = time.time()
    LOG.debug(
        "Initializing the configuration took %s ms", int((load_end_time - load_start_time) * 1000)
    )


def is_ipv6_address(host: str) -> bool:
    """
    Returns True if the given host is an IPv6 address.
    """

    if not host:
        return False

    try:
        ipaddress.IPv6Address(host)
        return True
    except ipaddress.AddressValueError:
        return False


class HostAndPort:
    """
    Definition of an address for a server to listen to.

    Includes a `parse` method to convert from `str`, allowing for default fallbacks, as well as
    some helper methods to help tests - particularly testing for equality and a hash function
    so that `HostAndPort` instances can be used as keys to dictionaries.
    """

    host: str
    port: int

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @classmethod
    def parse(
        cls,
        input: str,
        default_host: str,
        default_port: int,
    ) -> "HostAndPort":
        """
        Parse a `HostAndPort` from strings like:
            - 0.0.0.0:4566 -> host=0.0.0.0, port=4566
            - 0.0.0.0      -> host=0.0.0.0, port=`default_port`
            - :4566        -> host=`default_host`, port=4566
            - [::]:4566    -> host=[::], port=4566
            - [::1]        -> host=[::1], port=`default_port`
        """
        host, port = default_host, default_port

        # recognize IPv6 addresses (+ port)
        if input.startswith("["):
            ipv6_pattern = re.compile(r"^\[(?P<host>[^]]+)\](:(?P<port>\d+))?$")
            match = ipv6_pattern.match(input)

            if match:
                host = match.group("host")
                if not is_ipv6_address(host):
                    raise ValueError(
                        f"input looks like an IPv6 address (is enclosed in square brackets), but is not valid: {host}"
                    )
                port_s = match.group("port")
                if port_s:
                    port = cls._validate_port(port_s)
            else:
                raise ValueError(
                    f'input looks like an IPv6 address, but is invalid. Should be formatted "[ip]:port": {input}'
                )

        # recognize IPv4 address + port
        elif ":" in input:
            hostname, port_s = input.split(":", 1)
            if hostname.strip():
                host = hostname.strip()
            port = cls._validate_port(port_s)
        else:
            if input.strip():
                host = input.strip()

        # validation
        if port < 0 or port >= 2**16:
            raise ValueError("port out of range")

        return cls(host=host, port=port)

    @classmethod
    def _validate_port(cls, port_s: str) -> int:
        try:
            port = int(port_s)
        except ValueError as e:
            raise ValueError(f"specified port {port_s} not a number") from e

        return port

    def _get_unprivileged_port_range_start(self) -> int:
        try:
            with open("/proc/sys/net/ipv4/ip_unprivileged_port_start") as unprivileged_port_start:
                port = unprivileged_port_start.read()
                return int(port.strip())
        except Exception:
            return 1024

    def is_unprivileged(self) -> bool:
        return self.port >= self._get_unprivileged_port_range_start()

    def host_and_port(self) -> str:
        formatted_host = f"[{self.host}]" if is_ipv6_address(self.host) else self.host
        return f"{formatted_host}:{self.port}" if self.port is not None else formatted_host

    def __hash__(self) -> int:
        return hash((self.host, self.port))

    # easier tests
    def __eq__(self, other: "str | HostAndPort") -> bool:
        if isinstance(other, self.__class__):
            return self.host == other.host and self.port == other.port
        elif isinstance(other, str):
            return str(self) == other
        else:
            raise TypeError(f"cannot compare {self.__class__} to {other.__class__}")

    def __str__(self) -> str:
        return self.host_and_port()

    def __repr__(self) -> str:
        return f"HostAndPort(host={self.host}, port={self.port})"


class UniqueHostAndPortList(list[HostAndPort]):
    """
    Container type that ensures that ports added to the list are unique based
    on these rules:
        - :: "trumps" any other binding on the same port, including both IPv6 and IPv4
          addresses. All other bindings for this port are removed, since :: already
          covers all interfaces. For example, adding 127.0.0.1:4566, [::1]:4566,
          and [::]:4566 would result in only [::]:4566 being preserved.
        - 0.0.0.0 "trumps" any other binding on IPv4 addresses only. IPv6 addresses
          are not removed.
        - Identical identical hosts and ports are de-duped
    """

    def __init__(self, iterable: list[HostAndPort] | None = None):
        super().__init__(iterable or [])
        self._ensure_unique()

    def _ensure_unique(self):
        """
        Ensure that all bindings on the same port are de-duped.
        """
        if len(self) <= 1:
            return

        unique: list[HostAndPort] = []

        # Build a dictionary of hosts by port
        hosts_by_port: dict[int, list[str]] = defaultdict(list)
        for item in self:
            hosts_by_port[item.port].append(item.host)

        # For any given port, dedupe the hosts
        for port, hosts in hosts_by_port.items():
            deduped_hosts = set(hosts)

            # IPv6 all interfaces: this is the most general binding.
            # Any others should be removed.
            if "::" in deduped_hosts:
                unique.append(HostAndPort(host="::", port=port))
                continue
            # IPv4 all interfaces: this is the next most general binding.
            # Any others should be removed.
            if "0.0.0.0" in deduped_hosts:
                unique.append(HostAndPort(host="0.0.0.0", port=port))
                continue

            # All other bindings just need to be unique
            unique.extend([HostAndPort(host=host, port=port) for host in deduped_hosts])

        self.clear()
        self.extend(unique)

    def append(self, value: HostAndPort):
        super().append(value)
        self._ensure_unique()


def populate_edge_configuration(
    environment: Mapping[str, str],
) -> tuple[HostAndPort, UniqueHostAndPortList]:
    """Populate the LocalStack edge configuration from environment variables."""
    localstack_host_raw = environment.get("LOCALSTACK_HOST")
    gateway_listen_raw = environment.get("GATEWAY_LISTEN")

    # parse gateway listen from multiple components
    if gateway_listen_raw is not None:
        gateway_listen = []
        for address in gateway_listen_raw.split(","):
            gateway_listen.append(
                HostAndPort.parse(
                    address.strip(),
                    default_host=default_ip,
                    default_port=constants.DEFAULT_PORT_EDGE,
                )
            )
    else:
        # use default if gateway listen is not defined
        gateway_listen = [HostAndPort(host=default_ip, port=constants.DEFAULT_PORT_EDGE)]

    # the actual value of the LOCALSTACK_HOST port now depends on what gateway listen actually listens to.
    if localstack_host_raw is None:
        localstack_host = HostAndPort(
            host=constants.LOCALHOST_HOSTNAME, port=gateway_listen[0].port
        )
    else:
        localstack_host = HostAndPort.parse(
            localstack_host_raw,
            default_host=constants.LOCALHOST_HOSTNAME,
            default_port=gateway_listen[0].port,
        )

    assert gateway_listen is not None
    assert localstack_host is not None

    return (
        localstack_host,
        UniqueHostAndPortList(gateway_listen),
    )


# How to access LocalStack
(
    # -- Cosmetic
    LOCALSTACK_HOST,
    # -- Edge configuration
    # Main configuration of the listen address of the hypercorn proxy. Of the form
    # <ip_address>:<port>(,<ip_address>:port>)*
    GATEWAY_LISTEN,
) = populate_edge_configuration(os.environ)

GATEWAY_WORKER_COUNT = int(os.environ.get("GATEWAY_WORKER_COUNT") or 1000)

# the gateway server that should be used (supported: hypercorn, twisted dev: werkzeug)
GATEWAY_SERVER = os.environ.get("GATEWAY_SERVER", "").strip() or "twisted"

# whether to enable API-based updates of configuration variables at runtime
ENABLE_CONFIG_UPDATES = is_env_true("ENABLE_CONFIG_UPDATES")

# CORS settings
DISABLE_CORS_HEADERS = is_env_true("DISABLE_CORS_HEADERS")
DISABLE_CORS_CHECKS = is_env_true("DISABLE_CORS_CHECKS")
DISABLE_CUSTOM_CORS_S3 = is_env_true("DISABLE_CUSTOM_CORS_S3")
DISABLE_CUSTOM_CORS_APIGATEWAY = is_env_true("DISABLE_CUSTOM_CORS_APIGATEWAY")
EXTRA_CORS_ALLOWED_HEADERS = os.environ.get("EXTRA_CORS_ALLOWED_HEADERS", "").strip()
EXTRA_CORS_EXPOSE_HEADERS = os.environ.get("EXTRA_CORS_EXPOSE_HEADERS", "").strip()
EXTRA_CORS_ALLOWED_ORIGINS = os.environ.get("EXTRA_CORS_ALLOWED_ORIGINS", "").strip()
DISABLE_PREFLIGHT_PROCESSING = is_env_true("DISABLE_PREFLIGHT_PROCESSING")

# whether to log fine-grained debugging information for the handler chain
DEBUG_HANDLER_CHAIN = is_env_true("DEBUG_HANDLER_CHAIN")

# whether to eagerly start services
EAGER_SERVICE_LOADING = is_env_true("EAGER_SERVICE_LOADING")

# whether to selectively load services in SERVICES
STRICT_SERVICE_LOADING = is_env_not_false("STRICT_SERVICE_LOADING")

# Whether to skip downloading our signed SSL cert.
SKIP_SSL_CERT_DOWNLOAD = is_env_true("SKIP_SSL_CERT_DOWNLOAD")

# Absolute path to a custom certificate (pem file)
CUSTOM_SSL_CERT_PATH = os.environ.get("CUSTOM_SSL_CERT_PATH", "").strip()

# Whether delete the cached signed SSL certificate at startup
REMOVE_SSL_CERT = is_env_true("REMOVE_SSL_CERT")

# Allow non-standard AWS regions
ALLOW_NONSTANDARD_REGIONS = is_env_true("ALLOW_NONSTANDARD_REGIONS")
if ALLOW_NONSTANDARD_REGIONS:
    os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "true"

# the latest commit id of the repository when the docker image was created
LOCALSTACK_BUILD_GIT_HASH = os.environ.get("LOCALSTACK_BUILD_GIT_HASH", "").strip() or None

# the date on which the docker image was created
LOCALSTACK_BUILD_DATE = os.environ.get("LOCALSTACK_BUILD_DATE", "").strip() or None

# Equivalent to HTTP_PROXY, but only applicable for external connections
OUTBOUND_HTTP_PROXY = os.environ.get("OUTBOUND_HTTP_PROXY", "")

# Equivalent to HTTPS_PROXY, but only applicable for external connections
OUTBOUND_HTTPS_PROXY = os.environ.get("OUTBOUND_HTTPS_PROXY", "")

# Feature flag to enable validation of internal endpoint responses in the handler chain. For test use only.
OPENAPI_VALIDATE_RESPONSE = is_env_true("OPENAPI_VALIDATE_RESPONSE")
# Flag to enable the validation of the requests made to the LocalStack internal endpoints. Active by default.
OPENAPI_VALIDATE_REQUEST = is_env_true("OPENAPI_VALIDATE_REQUEST")

# environment variable to determine whether to include stack traces in http responses
INCLUDE_STACK_TRACES_IN_HTTP_RESPONSE = is_env_true("INCLUDE_STACK_TRACES_IN_HTTP_RESPONSE")

# whether to skip waiting for the infrastructure to shut down, or exit immediately
FORCE_SHUTDOWN = is_env_not_false("FORCE_SHUTDOWN")

# set variables no_proxy, i.e., run internal service calls directly
no_proxy = ",".join([constants.LOCALHOST_HOSTNAME, LOCALHOST, LOCALHOST_IP, "[::1]"])
if os.environ.get("no_proxy"):
    os.environ["no_proxy"] += "," + no_proxy
elif os.environ.get("NO_PROXY"):
    os.environ["NO_PROXY"] += "," + no_proxy
else:
    os.environ["no_proxy"] = no_proxy

# additional CLI commands, can be set by plugins
CLI_COMMANDS = {}

# AWS account used to store internal resources such as Lambda archives or internal SQS queues.
# It should not be modified by the user, or visible to him, except as through a presigned url with the
# get-function call.
INTERNAL_RESOURCE_ACCOUNT = os.environ.get("INTERNAL_RESOURCE_ACCOUNT") or "949334387222"

# -----
# SERVICE-SPECIFIC CONFIGS BELOW
# -----

# bind address of local DNS server
DNS_ADDRESS = os.environ.get("DNS_ADDRESS") or "0.0.0.0"
# port of the local DNS server
DNS_PORT = int(os.environ.get("DNS_PORT", "53"))

# Comma-separated list of regex patterns for DNS names to resolve locally.
# Any DNS name not matched against any of the patterns on this whitelist
# will resolve it to the real DNS entry, rather than the local one.
DNS_NAME_PATTERNS_TO_RESOLVE_UPSTREAM = (
    os.environ.get("DNS_NAME_PATTERNS_TO_RESOLVE_UPSTREAM") or ""
).strip()
DNS_LOCAL_NAME_PATTERNS = (os.environ.get("DNS_LOCAL_NAME_PATTERNS") or "").strip()  # deprecated

# IP address that AWS endpoints should resolve to in our local DNS server. By default,
# hostnames resolve to 127.0.0.1, which allows to use the LocalStack APIs transparently
# from the host machine. If your code is running in Docker, this should be configured
# to resolve to the Docker bridge network address, e.g., DNS_RESOLVE_IP=172.17.0.1
DNS_RESOLVE_IP = os.environ.get("DNS_RESOLVE_IP") or LOCALHOST_IP

# fallback DNS server to send upstream requests to
DNS_SERVER = os.environ.get("DNS_SERVER")
DNS_VERIFICATION_DOMAIN = os.environ.get("DNS_VERIFICATION_DOMAIN") or "localstack.cloud"


def use_custom_dns():
    return str(DNS_ADDRESS) not in FALSE_STRINGS


# s3 virtual host name
S3_VIRTUAL_HOSTNAME = f"s3.{LOCALSTACK_HOST.host}"
S3_STATIC_WEBSITE_HOSTNAME = f"s3-website.{LOCALSTACK_HOST.host}"

BOTO_WAITER_DELAY = int(os.environ.get("BOTO_WAITER_DELAY") or "1")
BOTO_WAITER_MAX_ATTEMPTS = int(os.environ.get("BOTO_WAITER_MAX_ATTEMPTS") or "120")
DISABLE_CUSTOM_BOTO_WAITER_CONFIG = is_env_true("DISABLE_CUSTOM_BOTO_WAITER_CONFIG")

# defaults to false
# if `DISABLE_BOTO_RETRIES=1` is set, all our created boto clients will have retries disabled
DISABLE_BOTO_RETRIES = is_env_true("DISABLE_BOTO_RETRIES")

DISTRIBUTED_MODE = is_env_true("DISTRIBUTED_MODE")

# This flag enables `connect_to` to be in-memory only and not do networking calls
IN_MEMORY_CLIENT = is_env_true("IN_MEMORY_CLIENT")

# This flag enables all responses from LocalStack to contain a `x-localstack` HTTP header.
LOCALSTACK_RESPONSE_HEADER_ENABLED = is_env_not_false("LOCALSTACK_RESPONSE_HEADER_ENABLED")

# Serialization backend for the LocalStack internal state (`dill` is used by default`).
STATE_SERIALIZATION_BACKEND = os.environ.get("STATE_SERIALIZATION_BACKEND", "").strip() or "dill"

# List of environment variable names used for configuration that are passed from the host into the LocalStack container.
# => Synchronize this list with the above and the configuration docs:
# https://docs.localstack.cloud/references/configuration/
# => Sort this list alphabetically
# => Add deprecated environment variables to deprecations.py and add a comment in this list
# => Move removed legacy variables to the section grouped by release (still relevant for deprecation warnings)
# => Do *not* include any internal developer configurations that apply to host-mode only in this list.
CONFIG_ENV_VARS = [
    "ALLOW_NONSTANDARD_REGIONS",
    "BOTO_WAITER_DELAY",
    "BOTO_WAITER_MAX_ATTEMPTS",
    "CFN_VERBOSE_ERRORS",  # retained until testing/pytest/fixtures.py is pruned in Phase 6
    "CI",
    "CUSTOM_SSL_CERT_PATH",
    "DEBUG",
    "DEBUG_HANDLER_CHAIN",
    "DISABLE_BOTO_RETRIES",
    "DISABLE_CORS_CHECKS",
    "DISABLE_CORS_HEADERS",
    "DISABLE_CUSTOM_BOTO_WAITER_CONFIG",
    "DISABLE_CUSTOM_CORS_APIGATEWAY",
    "DISABLE_CUSTOM_CORS_S3",
    "DISTRIBUTED_MODE",
    "DNS_ADDRESS",
    "DNS_PORT",
    "DNS_LOCAL_NAME_PATTERNS",
    "DNS_NAME_PATTERNS_TO_RESOLVE_UPSTREAM",
    "DNS_RESOLVE_IP",
    "DNS_SERVER",
    "DNS_VERIFICATION_DOMAIN",
    "EAGER_SERVICE_LOADING",
    "ENABLE_CONFIG_UPDATES",
    "EXTRA_CORS_ALLOWED_HEADERS",
    "EXTRA_CORS_ALLOWED_ORIGINS",
    "EXTRA_CORS_EXPOSE_HEADERS",
    "GATEWAY_LISTEN",
    "GATEWAY_SERVER",
    "GATEWAY_WORKER_THREAD_COUNT",
    "HOSTNAME",
    "IN_MEMORY_CLIENT",
    "LOCALSTACK_API_KEY",
    "LOCALSTACK_AUTH_TOKEN",
    "LOCALSTACK_HOST",
    "LOCALSTACK_RESPONSE_HEADER_ENABLED",
    "LOG_LICENSE_ISSUES",
    "LS_LOG",
    "OPENAPI_VALIDATE_REQUEST",
    "OPENAPI_VALIDATE_RESPONSE",
    "OUTBOUND_HTTP_PROXY",
    "OUTBOUND_HTTPS_PROXY",
    "PERSISTENCE",
    "REQUESTS_CA_BUNDLE",
    "REMOVE_SSL_CERT",
    "SERVICES",
    "SKIP_SSL_CERT_DOWNLOAD",
    "SNAPSHOT_LOAD_STRATEGY",
    "SNAPSHOT_SAVE_STRATEGY",
    "SNAPSHOT_FLUSH_INTERVAL",
    "STATE_SERIALIZATION_BACKEND",
    "STRICT_SERVICE_LOADING",
    "USE_SSL",
    # Removed legacy variables in 2.0.0
    # DATA_DIR => do *not* include in this list, as it is treated separately.  # deprecated since 1.0.0
    "LEGACY_DIRECTORIES",  # deprecated since 1.0.0
    # Removed legacy variables in 3.0.0
    "DEFAULT_REGION",  # deprecated since 0.12.7
    "EDGE_BIND_HOST",  # deprecated since 2.0.0
    "EDGE_FORWARD_URL",  # deprecated since 1.4.0
    "EDGE_PORT",  # deprecated since 2.0.0
    "EDGE_PORT_HTTP",  # deprecated since 2.0.0
    "HOSTNAME_EXTERNAL",  # deprecated since 2.0.0
    "LEGACY_EDGE_PROXY",  # deprecated since 1.0.0
    "LOCALSTACK_HOSTNAME",  # deprecated since 2.0.0
    "USE_SINGLE_REGION",  # deprecated since 0.12.7
    "MOCK_UNIMPLEMENTED",  # deprecated since 1.3.0
]


def is_local_test_mode() -> bool:
    """Returns True if we are running in the context of our local integration tests."""
    return is_env_true(ENV_INTERNAL_TEST_RUN)


def is_collect_metrics_mode() -> bool:
    """Returns True if metric collection is enabled."""
    return is_env_true(ENV_INTERNAL_TEST_COLLECT_METRIC)


def store_test_metrics_in_local_filesystem() -> bool:
    """Returns True if test metrics should be stored in the local filesystem (instead of the system that runs pytest)."""
    return is_env_true(ENV_INTERNAL_TEST_STORE_METRICS_IN_LOCALSTACK)


def collect_config_items() -> list[tuple[str, Any]]:
    """Returns a list of key-value tuples of LocalStack configuration values."""
    none = object()  # sentinel object

    # collect which keys to print
    keys = []
    keys.extend(CONFIG_ENV_VARS)
    keys.append("DATA_DIR")
    keys.sort()

    values = globals()

    result = []
    for k in keys:
        v = values.get(k, none)
        if v is none:
            continue
        result.append((k, v))
    result.sort()
    return result


def populate_config_env_var_names():
    global CONFIG_ENV_VARS

    CONFIG_ENV_VARS += [
        key
        for key in [key.upper() for key in os.environ]
        if (key.startswith("LOCALSTACK_") or key.startswith("PROVIDER_OVERRIDE_"))
        # explicitly exclude LOCALSTACK_CLI (it's prefixed with "LOCALSTACK_",
        # but is only used in the CLI (should not be forwarded to the container)
        and key != "LOCALSTACK_CLI"
    ]

    # create variable aliases prefixed with LOCALSTACK_ (except LOCALSTACK_HOST)
    CONFIG_ENV_VARS += [
        "LOCALSTACK_" + v for v in CONFIG_ENV_VARS if not v.startswith("LOCALSTACK_")
    ]

    CONFIG_ENV_VARS = list(set(CONFIG_ENV_VARS))


# populate env var names to be passed to the container
populate_config_env_var_names()


# helpers to build urls
def get_protocol() -> str:
    return "https" if USE_SSL else "http"


def external_service_url(
    host: str | None = None,
    port: int | None = None,
    protocol: str | None = None,
    subdomains: str | None = None,
) -> str:
    """Returns a service URL (e.g., SQS queue URL) to an external client (e.g., boto3) potentially running on another
    machine than LocalStack. The configurations LOCALSTACK_HOST and USE_SSL can customize these returned URLs.
    The optional parameters can be used to customize the defaults.
    Examples with default configuration:
    * external_service_url() == http://localhost.localstack.cloud:4566
    * external_service_url(subdomains="s3") == http://s3.localhost.localstack.cloud:4566
    """
    protocol = protocol or get_protocol()
    subdomains = f"{subdomains}." if subdomains else ""
    host = host or LOCALSTACK_HOST.host
    port = port or LOCALSTACK_HOST.port
    return f"{protocol}://{subdomains}{host}:{port}"


def internal_service_url(
    host: str | None = None,
    port: int | None = None,
    protocol: str | None = None,
    subdomains: str | None = None,
) -> str:
    """Returns a service URL for internal use within LocalStack (i.e., same host).
    The configuration USE_SSL can customize these returned URLs but LOCALSTACK_HOST has no effect.
    The optional parameters can be used to customize the defaults.
    Examples with default configuration:
    * internal_service_url() == http://localhost:4566
    * internal_service_url(port=8080) == http://localhost:8080
    """
    protocol = protocol or get_protocol()
    subdomains = f"{subdomains}." if subdomains else ""
    host = host or LOCALHOST
    port = port or GATEWAY_LISTEN[0].port
    return f"{protocol}://{subdomains}{host}:{port}"


# DEPRECATED: old helpers for building URLs


def service_url(service_key, host=None, port=None):
    """@deprecated: Use `internal_service_url()` instead. We assume that most usages are internal
    but really need to check and update each usage accordingly.
    """
    warnings.warn(
        """@deprecated: Use `internal_service_url()` instead. We assume that most usages are
        internal but really need to check and update each usage accordingly.""",
        DeprecationWarning,
        stacklevel=2,
    )
    return internal_service_url(host=host, port=port)


def service_port(service_key: str, external: bool = False) -> int:
    """@deprecated: Use `localstack_host().port` for external and `GATEWAY_LISTEN[0].port` for
    internal use."""
    warnings.warn(
        "Deprecated: use `localstack_host().port` for external and `GATEWAY_LISTEN[0].port` for "
        "internal use.",
        DeprecationWarning,
        stacklevel=2,
    )
    if external:
        return LOCALSTACK_HOST.port
    return GATEWAY_LISTEN[0].port


def get_edge_port_http():
    """@deprecated: Use `localstack_host().port` for external and `GATEWAY_LISTEN[0].port` for
    internal use. This function is not needed anymore because we don't separate between HTTP
    and HTTP ports anymore since LocalStack listens to both ports."""
    warnings.warn(
        """@deprecated: Use `localstack_host().port` for external and `GATEWAY_LISTEN[0].port`
        for internal use. This function is also not needed anymore because we don't separate
        between HTTP and HTTP ports anymore since LocalStack listens to both.""",
        DeprecationWarning,
        stacklevel=2,
    )
    return GATEWAY_LISTEN[0].port


def get_edge_url(localstack_hostname=None, protocol=None):
    """@deprecated: Use `internal_service_url()` instead.
    We assume that most usages are internal but really need to check and update each usage accordingly.
    """
    warnings.warn(
        """@deprecated: Use `internal_service_url()` instead.
    We assume that most usages are internal but really need to check and update each usage accordingly.
    """,
        DeprecationWarning,
        stacklevel=2,
    )
    return internal_service_url(host=localstack_hostname, protocol=protocol)


class ServiceProviderConfig(Mapping[str, str]):
    _provider_config: dict[str, str]
    default_value: str
    override_prefix: str = "PROVIDER_OVERRIDE_"

    def __init__(self, default_value: str):
        self._provider_config = {}
        self.default_value = default_value

    def load_from_environment(self, env: Mapping[str, str] = None):
        if env is None:
            env = os.environ
        for key, value in env.items():
            if key.startswith(self.override_prefix) and value:
                self.set_provider(key[len(self.override_prefix) :].lower().replace("_", "-"), value)

    def get_provider(self, service: str) -> str:
        return self._provider_config.get(service, self.default_value)

    def set_provider_if_not_exists(self, service: str, provider: str) -> None:
        if service not in self._provider_config:
            self._provider_config[service] = provider

    def set_provider(self, service: str, provider: str):
        self._provider_config[service] = provider

    def bulk_set_provider_if_not_exists(self, services: list[str], provider: str):
        for service in services:
            self.set_provider_if_not_exists(service, provider)

    def __getitem__(self, item):
        return self.get_provider(item)

    def __setitem__(self, key, value):
        self.set_provider(key, value)

    def __len__(self):
        return len(self._provider_config)

    def __iter__(self):
        return self._provider_config.__iter__()


SERVICE_PROVIDER_CONFIG = ServiceProviderConfig("default")

SERVICE_PROVIDER_CONFIG.load_from_environment()


def init_directories() -> Directories:
    if is_in_docker:
        return Directories.for_container()
    else:
        if is_env_true("LOCALSTACK_CLI"):
            return Directories.for_cli()

        return Directories.for_host()


# initialize directories
dirs: Directories
dirs = init_directories()
