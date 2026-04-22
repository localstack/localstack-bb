"""This is the entrypoint used to start the localstack runtime. It starts the infrastructure and also
manages the interaction with the operating system - mostly signal handlers for now."""

import signal
import sys

from localstack import config, constants
from localstack.runtime.exceptions import LocalstackExit


def print_runtime_information():
    print()
    print(f"LocalStack version: {constants.VERSION}")

    if config.LOCALSTACK_BUILD_DATE:
        print(f"LocalStack build date: {config.LOCALSTACK_BUILD_DATE}")

    if config.LOCALSTACK_BUILD_GIT_HASH:
        print(f"LocalStack build git hash: {config.LOCALSTACK_BUILD_GIT_HASH}")

    print()


def main():
    from localstack.logging.setup import setup_logging_from_config
    from localstack.runtime import current

    try:
        setup_logging_from_config()
        runtime = current.initialize_runtime()
    except Exception as e:
        sys.stdout.write(
            f"ERROR: The LocalStack Runtime could not be initialized: {e}\n"
        )
        sys.stdout.flush()
        raise

    # TODO: where should this go?
    print_runtime_information()

    # signal handler to make sure SIGTERM properly shuts down localstack
    def _terminate_localstack(sig: int, frame):
        sys.stdout.write(f"Localstack runtime received signal {sig}\n")
        sys.stdout.flush()
        runtime.exit(0)

    signal.signal(signal.SIGINT, _terminate_localstack)
    signal.signal(signal.SIGTERM, _terminate_localstack)

    try:
        runtime.run()
    except LocalstackExit as e:
        sys.stdout.write(f"Localstack returning with exit code {e.code}. Reason: {e}")
        sys.exit(e.code)
    except Exception as e:
        sys.stdout.write(f"ERROR: the LocalStack runtime exited unexpectedly: {e}\n")
        sys.stdout.flush()
        raise

    sys.exit(runtime.exit_code)


if __name__ == "__main__":
    main()
