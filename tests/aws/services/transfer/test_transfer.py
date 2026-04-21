import re

import pytest
from botocore.exceptions import ClientError

from localstack.testing.pytest import markers
from localstack.utils.strings import short_uid


class TestTransferServer:
    @markers.aws.validated
    def test_create_server(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))

        response = aws_client.transfer.create_server()
        
        server_id = response["ServerId"]
        assert re.match(r"^s-[0-9a-f]{17}$", server_id), f"Server ID '{server_id}' does not match pattern s-[0-9a-f]{{17}}"

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
            "$..Server.State",
            "$..Server.Tags",
            "$..Server.UserCount",
        ]
    )
    def test_describe_server(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("Arn"))
        snapshot.add_transformer(snapshot.transform.key_value("HostKeyFingerprint"))

        create_response = aws_client.transfer.create_server()
        server_id = create_response["ServerId"]

        describe_response = aws_client.transfer.describe_server(ServerId=server_id)
        snapshot.match("describe-server", describe_response)

    @markers.aws.validated
    def test_describe_server_invalid_id(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.regex(r"s-[a-f0-9-]+", "<server-id>"))

        invalid_server_id = f"s-{short_uid()}-{short_uid()}"

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.describe_server(ServerId=invalid_server_id)

        snapshot.match("describe-server-invalid-id", exc_info.value.response)

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
            "$..Server.State",
            "$..Server.Tags",
            "$..Server.UserCount",
        ]
    )
    def test_create_and_describe_server_state(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("Arn"))
        snapshot.add_transformer(snapshot.transform.key_value("HostKeyFingerprint"))

        create_response = aws_client.transfer.create_server()
        server_id = create_response["ServerId"]

        describe_response = aws_client.transfer.describe_server(ServerId=server_id)

        assert "Server" in describe_response
        assert "Arn" in describe_response["Server"]
        assert "State" in describe_response["Server"]
        assert describe_response["Server"]["State"] in ["ONLINE", "STARTING"]

        snapshot.match("describe-server-with-state", describe_response)


class TestTransferUser:
    @markers.aws.validated
    def test_create_user(self, aws_client, snapshot, account_id):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("UserName"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        user_response = aws_client.transfer.create_user(
            ServerId=server_id,
            UserName="testuser",
            Role=f"arn:aws:iam::{account_id}:role/TransferRole",
        )

        snapshot.match("create-user", user_response)

    @markers.aws.validated
    def test_create_user_invalid_server(self, aws_client, snapshot, account_id):
        snapshot.add_transformer(snapshot.transform.regex(r"s-[a-f0-9-]+", "<server-id>"))

        invalid_server_id = f"s-{short_uid()}-{short_uid()}"

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.create_user(
                ServerId=invalid_server_id,
                UserName="testuser",
                Role=f"arn:aws:iam::{account_id}:role/TransferRole",
            )

        snapshot.match("create-user-invalid-server", exc_info.value.response)

    @markers.aws.validated
    def test_create_user_duplicate(self, aws_client, snapshot, account_id):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("UserName"))
        snapshot.add_transformer(snapshot.transform.key_value("Resource"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        aws_client.transfer.create_user(
            ServerId=server_id,
            UserName="testuser",
            Role=f"arn:aws:iam::{account_id}:role/TransferRole",
        )

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.create_user(
                ServerId=server_id,
                UserName="testuser",
                Role=f"arn:aws:iam::{account_id}:role/TransferRole",
            )

        snapshot.match("create-user-duplicate", exc_info.value.response)

    @markers.aws.validated
    @markers.snapshot.skip_snapshot_verify(
        paths=[
            "$..Users..HomeDirectoryType",
            "$..Users..SshPublicKeyCount",
        ]
    )
    def test_list_users(self, aws_client, snapshot, account_id):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("UserName"))
        snapshot.add_transformer(snapshot.transform.key_value("Arn"))
        snapshot.add_transformer(snapshot.transform.key_value("Role"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        aws_client.transfer.create_user(
            ServerId=server_id,
            UserName="user1",
            Role=f"arn:aws:iam::{account_id}:role/TransferRole",
        )
        aws_client.transfer.create_user(
            ServerId=server_id,
            UserName="user2",
            Role=f"arn:aws:iam::{account_id}:role/TransferRole",
        )

        list_response = aws_client.transfer.list_users(ServerId=server_id)
        snapshot.match("list-users", list_response)

    @markers.aws.validated
    def test_list_users_empty(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        list_response = aws_client.transfer.list_users(ServerId=server_id)
        snapshot.match("list-users-empty", list_response)

    @markers.aws.validated
    def test_list_users_invalid_server(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.regex(r"s-[a-f0-9-]+", "<server-id>"))

        invalid_server_id = f"s-{short_uid()}-{short_uid()}"

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.list_users(ServerId=invalid_server_id)

        snapshot.match("list-users-invalid-server", exc_info.value.response)

    @markers.aws.validated
    def test_delete_user(self, aws_client, snapshot, account_id):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.key_value("UserName"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        aws_client.transfer.create_user(
            ServerId=server_id,
            UserName="testuser",
            Role=f"arn:aws:iam::{account_id}:role/TransferRole",
        )

        aws_client.transfer.delete_user(ServerId=server_id, UserName="testuser")

        list_response = aws_client.transfer.list_users(ServerId=server_id)
        assert len(list_response["Users"]) == 0

        snapshot.match("list-users-after-delete", list_response)

    @markers.aws.validated
    def test_delete_user_invalid_user(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.key_value("ServerId"))
        snapshot.add_transformer(snapshot.transform.regex(r"testuser-\w+", "<user-name>"))

        server_response = aws_client.transfer.create_server()
        server_id = server_response["ServerId"]

        invalid_user_name = f"testuser-{short_uid()}"

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.delete_user(ServerId=server_id, UserName=invalid_user_name)

        snapshot.match("delete-user-invalid-user", exc_info.value.response)

    @markers.aws.validated
    def test_delete_user_invalid_server(self, aws_client, snapshot):
        snapshot.add_transformer(snapshot.transform.regex(r"s-[a-f0-9-]+", "<server-id>"))

        invalid_server_id = f"s-{short_uid()}-{short_uid()}"

        with pytest.raises(ClientError) as exc_info:
            aws_client.transfer.delete_user(ServerId=invalid_server_id, UserName="testuser")

        snapshot.match("delete-user-invalid-server", exc_info.value.response)
