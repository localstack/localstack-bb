from localstack.services.plugins import (
    Service,
    aws_provider,
)

@aws_provider()
def transfer():
    from localstack.services.transfer.provider import TransferProvider

    provider = TransferProvider()
    return Service.for_provider(provider)