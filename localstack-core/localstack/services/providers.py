from localstack.aws.forwarder import HttpFallbackDispatcher
from localstack.services.plugins import (
    Service,
    aws_provider,
)



@aws_provider(api="cloudformation", name="engine-legacy")
def cloudformation():
    from localstack.services.cloudformation.provider import CloudformationProvider

    provider = CloudformationProvider()
    return Service.for_provider(provider)


@aws_provider(api="cloudformation")
def cloudformation_v2():
    from localstack.services.cloudformation.v2.provider import CloudformationProviderV2

    provider = CloudformationProviderV2()
    return Service.for_provider(provider)



@aws_provider()
def dynamodb():
    from localstack.services.dynamodb.provider import DynamoDBProvider

    provider = DynamoDBProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )


@aws_provider(api="dynamodb", name="v2")
def dynamodb_v2():
    from localstack.services.dynamodb.v2.provider import DynamoDBProvider

    provider = DynamoDBProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )





@aws_provider()
def kinesis():
    from localstack.services.kinesis.provider import KinesisProvider

    provider = KinesisProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )



@aws_provider(api="lambda")
def lambda_():
    from localstack.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)


@aws_provider(api="lambda", name="asf")
def lambda_asf():
    from localstack.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)


@aws_provider(api="lambda", name="v2")
def lambda_v2():
    from localstack.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)





@aws_provider()
def s3():
    from localstack.services.s3.provider import S3Provider

    provider = S3Provider()
    return Service.for_provider(provider)



@aws_provider()
def sns():
    from localstack.services.sns.provider import SnsProvider

    provider = SnsProvider()
    return Service.for_provider(provider)


@aws_provider()
def sqs():
    from localstack.services.sqs.provider import SqsProvider

    provider = SqsProvider()
    return Service.for_provider(provider)


@aws_provider(api="events", name="default")
def events():
    from localstack.services.events.provider import EventsProvider

    provider = EventsProvider()
    return Service.for_provider(provider)


@aws_provider(api="events", name="v2")
def events_v2():
    from localstack.services.events.provider import EventsProvider

    provider = EventsProvider()
    return Service.for_provider(provider)


@aws_provider(api="events", name="v1")
def events_v1():
    from localstack.services.events.v1.provider import EventsProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = EventsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="events", name="legacy")
def events_legacy():
    from localstack.services.events.v1.provider import EventsProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = EventsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def stepfunctions():
    from localstack.services.stepfunctions.provider import StepFunctionsProvider

    provider = StepFunctionsProvider()
    return Service.for_provider(provider)


# TODO: remove with 4.1.0 to allow smooth deprecation path for users that have v2 set manually
@aws_provider(api="stepfunctions", name="v2")
def stepfunctions_v2():
    # provider for people still manually using `v2`
    from localstack.services.stepfunctions.provider import StepFunctionsProvider

    provider = StepFunctionsProvider()
    return Service.for_provider(provider)
