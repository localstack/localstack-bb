from typing import TypedDict

from localstack.aws.api.transfer import Arn, Role, ServerId, State, UserName
from localstack.services.stores import AccountRegionBundle, BaseStore, LocalAttribute


class ServerInstance(TypedDict, total=False):
    account_id: str
    region_name: str
    server_id: ServerId
    state: State
    arn: Arn


class UserInstance(TypedDict, total=False):
    user_name: UserName
    server_id: ServerId
    role: Role
    arn: Arn


class TransferStore(BaseStore):
    servers: dict[ServerId, ServerInstance] = LocalAttribute(default=dict)
    users: dict[ServerId, dict[UserName, UserInstance]] = LocalAttribute(default=dict)


transfer_stores = AccountRegionBundle("transfer", TransferStore)
