from localstack.aws.forwarder import HttpFallbackDispatcher
from localstack.services.plugins import (
    Service,
    aws_provider,
)


@aws_provider()
def apigateway():
    from localstack.services.apigateway.next_gen.provider import ApigatewayNextGenProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = ApigatewayNextGenProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="apigateway", name="next_gen")
def apigateway_next_gen():
    from localstack.services.apigateway.next_gen.provider import ApigatewayNextGenProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = ApigatewayNextGenProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="apigateway", name="legacy")
def apigateway_legacy():
    from localstack.services.apigateway.legacy.provider import ApigatewayProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = ApigatewayProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


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


@aws_provider(api="cloudwatch", name="default")
def cloudwatch():
    from localstack.services.cloudwatch.provider_v2 import CloudwatchProvider

    provider = CloudwatchProvider()
    return Service.for_provider(provider)


@aws_provider(api="cloudwatch", name="v1")
def cloudwatch_v1():
    from localstack.services.cloudwatch.provider import CloudwatchProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = CloudwatchProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="cloudwatch", name="v2")
def cloudwatch_v2():
    from localstack.services.cloudwatch.provider_v2 import CloudwatchProvider

    provider = CloudwatchProvider()
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
def ec2():
    from localstack.services.ec2.provider import Ec2Provider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = Ec2Provider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def firehose():
    from localstack.services.firehose.provider import FirehoseProvider

    provider = FirehoseProvider()
    return Service.for_provider(provider)


@aws_provider()
def iam():
    from localstack.services.iam.provider import IamProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = IamProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


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


@aws_provider()
def kms():
    from localstack.services.kms.provider import KmsProvider

    provider = KmsProvider()
    return Service.for_provider(provider)


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
def logs():
    from localstack.services.logs.provider import LogsProvider
    from localstack.services.moto import MotoFallbackDispatcher

    provider = LogsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def opensearch():
    from localstack.services.opensearch.provider import OpensearchProvider

    provider = OpensearchProvider()
    return Service.for_provider(provider)


@aws_provider()
def route53():
    from localstack.services.moto import MotoFallbackDispatcher
    from localstack.services.route53.provider import Route53Provider

    provider = Route53Provider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def s3():
    from localstack.services.s3.provider import S3Provider

    provider = S3Provider()
    return Service.for_provider(provider)


@aws_provider()
def secretsmanager():
    from localstack.services.moto import MotoFallbackDispatcher
    from localstack.services.secretsmanager.provider import SecretsmanagerProvider

    provider = SecretsmanagerProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


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
