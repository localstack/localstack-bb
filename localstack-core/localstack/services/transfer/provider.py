import logging

from localstack.aws.api import RequestContext
from localstack.aws.api.transfer import (
    Certificate,
    CreateServerResponse,
    DescribedServer,
    DescribeServerResponse,
    Domain,
    EndpointDetails,
    EndpointType,
    HostKey,
    IdentityProviderDetails,
    IdentityProviderType,
    IpAddressType,
    NullableRole,
    PostAuthenticationLoginBanner,
    PreAuthenticationLoginBanner,
    ProtocolDetails,
    Protocols,
    S3StorageOptions,
    SecurityPolicyName,
    ServerId,
    StructuredLogDestinations,
    Tags,
    TransferApi,
    WorkflowDetails,
    Role,
    UserName,
    HomeDirectory,
    HomeDirectoryType,
    HomeDirectoryMappings,
    Policy,
    PosixProfile,
    SshPublicKeyBody,
    CreateUserResponse,
    MaxResults,
    NextToken,
    ListUsersResponse,
)
from localstack.services.transfer.models import ServerInstance, transfer_stores
from localstack.utils.strings import long_uid


LOG = logging.getLogger(__name__)


class TransferProvider(TransferApi):
    #
    # Server
    #

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
        server_id = f"s-{long_uid()}"
        store.servers[server_id] = ServerInstance(
            account_id=context.account_id,
            region_name=context.region,
            server_id=server_id,
        )
        LOG.info("Created server: %s", server_id)
        return CreateServerResponse(ServerId=server_id)

    def describe_server(
        self, context: RequestContext, server_id: ServerId, **kwargs
    ) -> DescribeServerResponse:
        store = transfer_stores[context.account_id][context.region]
        server = store.servers[server_id]
        return DescribeServerResponse(
            Server=DescribedServer(ServerId=server["server_id"])
        )

    #
    # User
    #

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
        raise NotImplementedError

    def list_users(
        self,
        context: RequestContext,
        server_id: ServerId,
        max_results: MaxResults | None = None,
        next_token: NextToken | None = None,
        **kwargs,
    ) -> ListUsersResponse:
        raise NotImplementedError

    def delete_user(
        self,
        context: RequestContext,
        server_id: ServerId,
        user_name: UserName,
        **kwargs,
    ) -> None:
        raise NotImplementedError
