import pytest
from botocore.exceptions import ClientError

from localstack.testing.pytest import markers


class TestTransferFamily:
    @markers.aws.validated
    def test_create_server(self, aws_client, snapshot, cleanups):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))

        response = aws_client.transfer.create_server()
        server_id = response["ServerId"]
        cleanups.append(lambda: aws_client.transfer.delete_server(ServerId=server_id))

        snapshot.match("create-server", response)

    @markers.aws.validated
    @markers.snapshot.skip_snapshot_verify(
        paths=[
            "$..Server.Domain",
            "$..Server.EndpointType",
            "$..Server.HostKeyFingerprint",
            "$..Server.IdentityProviderType",
            "$..Server.IpAddressType",
            "$..Server.ProtocolDetails",
            "$..Server.Protocols",
            "$..Server.S3StorageOptions",
            "$..Server.SecurityPolicyName",
            "$..Server.Tags",
            "$..Server.UserCount",
        ]
    )
    def test_describe_server(self, aws_client, snapshot, cleanups):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("Arn"))
        snapshot.add_transformer(snapshot.transform.key_value("HostKeyFingerprint"))

        response = aws_client.transfer.create_server()
        server_id = response["ServerId"]

        cleanups.append(lambda: aws_client.transfer.delete_server(ServerId=server_id))

        response = aws_client.transfer.describe_server(ServerId=server_id)
        snapshot.match("describe-server", response)

        with pytest.raises(ClientError) as exc:
            aws_client.transfer.describe_server(ServerId='s-00123456789abcdef')
        snapshot.match("describe-server-invalid-id", exc.value.response)
