import re

from localstack.aws.api import CommonServiceException, RequestContext
from localstack.aws.api.transfer import (
    Certificate,
    CreateServerResponse,
    CreateUserResponse,
    DescribedServer,
    DescribeServerResponse,
    Domain,
    EndpointDetails,
    EndpointType,
    HomeDirectory,
    HomeDirectoryMappings,
    HomeDirectoryType,
    HostKey,
    IdentityProviderDetails,
    IdentityProviderType,
    IpAddressType,
    ListedUser,
    ListUsersResponse,
    MaxResults,
    NextToken,
    NullableRole,
    Policy,
    PosixProfile,
    PostAuthenticationLoginBanner,
    PreAuthenticationLoginBanner,
    ProtocolDetails,
    Protocols,
    ResourceExistsException,
    ResourceNotFoundException,
    Role,
    S3StorageOptions,
    SecurityPolicyName,
    ServerId,
    SshPublicKeyBody,
    State,
    StructuredLogDestinations,
    Tags,
    TransferApi,
    UserName,
    WorkflowDetails,
)
from localstack.services.transfer.models import ServerInstance, UserInstance, transfer_stores
from localstack.utils.strings import long_uid


def _validate_server_id(server_id: ServerId) -> None:
    if not re.match(r"^s-[0-9a-f]{17}$", server_id):
        raise CommonServiceException(
            code="ValidationException",
            message="1 validation error detected: Value at 'serverId' failed to satisfy constraint: "
            "Member must satisfy regular expression pattern: s-([0-9a-f]{17})",
        )


def _generate_server_id() -> ServerId:
    return f"s-{long_uid().replace('-', '')[:17]}"


class TransferProvider(TransferApi):
    def create_server(
        self,
        context: RequestContext,
        certificate: Certificate | None = None,
        domain: Domain | None = None,
        endpoint_details: EndpointDetails | None = None,
        endpoint_type: EndpointType | None = None,
        host_key: HostKey | None = None,
        identity_provider_details: IdentityProviderDetails | None = None,
        identity_provider_type: IdentityProviderType | None = None,
        logging_role: NullableRole | None = None,
        post_authentication_login_banner: PostAuthenticationLoginBanner | None = None,
        pre_authentication_login_banner: PreAuthenticationLoginBanner | None = None,
        protocols: Protocols | None = None,
        protocol_details: ProtocolDetails | None = None,
        security_policy_name: SecurityPolicyName | None = None,
        tags: Tags | None = None,
        workflow_details: WorkflowDetails | None = None,
        structured_log_destinations: StructuredLogDestinations | None = None,
        s3_storage_options: S3StorageOptions | None = None,
        ip_address_type: IpAddressType | None = None,
        **kwargs,
    ) -> CreateServerResponse:
        store = transfer_stores[context.account_id][context.region]
        server_id = _generate_server_id()
        arn = f"arn:aws:transfer:{context.region}:{context.account_id}:server/{server_id}"

        store.servers[server_id] = ServerInstance(
            server_id=server_id,
            arn=arn,
            state=State.ONLINE,
        )

        return CreateServerResponse(ServerId=server_id)

    def describe_server(
        self, context: RequestContext, server_id: ServerId, **kwargs
    ) -> DescribeServerResponse:
        _validate_server_id(server_id)

        store = transfer_stores[context.account_id][context.region]

        if server_id not in store.servers:
            raise ResourceNotFoundException(
                "Unknown server",
                Resource=server_id,
                ResourceType="Server",
            )

        server = store.servers[server_id]
        return DescribeServerResponse(
            Server=DescribedServer(
                ServerId=server["server_id"],
                Arn=server["arn"],
                State=server["state"],
            )
        )

    def create_user(
        self,
        context: RequestContext,
        role: Role,
        server_id: ServerId,
        user_name: UserName,
        home_directory: HomeDirectory | None = None,
        home_directory_type: HomeDirectoryType | None = None,
        home_directory_mappings: HomeDirectoryMappings | None = None,
        policy: Policy | None = None,
        posix_profile: PosixProfile | None = None,
        ssh_public_key_body: SshPublicKeyBody | None = None,
        tags: Tags | None = None,
        **kwargs,
    ) -> CreateUserResponse:
        _validate_server_id(server_id)

        store = transfer_stores[context.account_id][context.region]

        if server_id not in store.servers:
            raise ResourceNotFoundException(
                "Unknown server",
                Resource=server_id,
                ResourceType="Server",
            )

        if server_id not in store.users:
            store.users[server_id] = {}

        if user_name in store.users[server_id]:
            raise ResourceExistsException(
                "User already exists",
                Resource=f"{user_name}@{server_id}",
                ResourceType="User",
            )

        store.users[server_id][user_name] = UserInstance(
            user_name=user_name,
            server_id=server_id,
            role=role,
            arn=f"arn:aws:transfer:{context.region}:{context.account_id}:user/{server_id}/{user_name}",
        )

        return CreateUserResponse(ServerId=server_id, UserName=user_name)

    def list_users(
        self,
        context: RequestContext,
        server_id: ServerId,
        max_results: MaxResults | None = None,
        next_token: NextToken | None = None,
        **kwargs,
    ) -> ListUsersResponse:
        _validate_server_id(server_id)

        store = transfer_stores[context.account_id][context.region]

        if server_id not in store.servers:
            raise ResourceNotFoundException(
                "Unknown server",
                Resource=server_id,
                ResourceType="Server",
            )

        users = store.users.get(server_id, {})
        listed_users = [
            ListedUser(
                Arn=user["arn"],
                UserName=user["user_name"],
                Role=user["role"],
            )
            for user in users.values()
        ]

        return ListUsersResponse(ServerId=server_id, Users=listed_users)

    def delete_user(
        self,
        context: RequestContext,
        server_id: ServerId,
        user_name: UserName,
        **kwargs,
    ) -> None:
        _validate_server_id(server_id)

        store = transfer_stores[context.account_id][context.region]

        if server_id not in store.servers:
            raise ResourceNotFoundException(
                "Unknown server",
                Resource=server_id,
                ResourceType="Server",
            )

        if server_id not in store.users or user_name not in store.users[server_id]:
            raise ResourceNotFoundException(
                "Unknown user",
                Resource=user_name,
                ResourceType="User",
            )

        del store.users[server_id][user_name]
