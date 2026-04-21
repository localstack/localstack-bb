import pytest
from _pytest.config import Config
from localstack_snapshot.snapshots import SnapshotSession
from localstack_snapshot.snapshots.transformer import RegexTransformer

from localstack import config as localstack_config
from localstack import constants
from localstack.testing.snapshots.transformer_utility import (
    SNAPSHOT_BASIC_TRANSFORMER_NEW,
    TransformerUtility,
)
from localstack.utils.aws.arns import get_partition


def pytest_configure(config: Config):
    config.option.start_localstack = True
    localstack_config.FORCE_SHUTDOWN = False
    localstack_config.GATEWAY_LISTEN = localstack_config.UniqueHostAndPortList(
        [localstack_config.HostAndPort(host="0.0.0.0", port=constants.DEFAULT_PORT_EDGE)]
    )


@pytest.fixture(scope="function")
def snapshot(request, _snapshot_session: SnapshotSession, account_id, region_name):
    _snapshot_session.transform = TransformerUtility

    _snapshot_session.add_transformer(RegexTransformer(account_id, "1" * 12), priority=2)
    _snapshot_session.add_transformer(RegexTransformer(region_name, "<region>"), priority=2)
    _snapshot_session.add_transformer(
        RegexTransformer(f"arn:{get_partition(region_name)}:", "arn:<partition>:"), priority=2
    )

    _snapshot_session.add_transformer(_snapshot_session.transform.remove_key("x-localstack"))
    _snapshot_session.add_transformer(SNAPSHOT_BASIC_TRANSFORMER_NEW, priority=2)

    return _snapshot_session
