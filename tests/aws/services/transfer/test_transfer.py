import pytest  # noqa
from botocore.exceptions import ClientError  # noqa

from localstack.testing.pytest import markers


class TestTransferFamily:
    @markers.aws.unknown
    def test_create_server(self, aws_client):
        response = aws_client.transfer.create_server()

        assert response['ServerId'].startswith("s-")

        aws_client.transfer.delete_server(ServerId=response["ServerId"])

    @markers.aws.unknown
    def test_describe_server(self, aws_client):
        server_id = aws_client.transfer.create_server()["ServerId"]

        response = aws_client.transfer.describe_server(ServerId=server_id)

        assert response['Server']['ServerId'] == server_id

        aws_client.transfer.delete_server(ServerId=server_id)