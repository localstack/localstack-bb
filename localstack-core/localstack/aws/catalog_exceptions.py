from localstack.aws.api import CommonServiceException

_DOCS_COVERAGE_URL = "https://docs.localstack.cloud/references/coverage"


class AwsServiceAvailabilityException(CommonServiceException):
    def __init__(self, message: str, error_code: int):
        super().__init__(code="InternalFailure", message=message, status_code=501)
        self.error_code = error_code


class ServiceOrOperationNotSupportedException(AwsServiceAvailabilityException):
    def __init__(self, service_name: str, operation_name: str | None = None):
        if operation_name is None:
            message = f"Sorry, the {service_name} service is not currently supported by LocalStack."
            error_code = 3
        else:
            message = f"Sorry, the {operation_name} operation on the {service_name} service is not currently supported by LocalStack."
            error_code = 8
        super().__init__(message, error_code)


class LatestVersionRequiredException(AwsServiceAvailabilityException):
    def __init__(self, service_name: str, operation_name: str | None = None):
        if operation_name is None:
            message = f"Sorry, the {service_name} service is not supported by this version of LocalStack, but is available if you upgrade to the latest stable version."
            error_code = 2
        else:
            message = f"Sorry, the {operation_name} operation on the {service_name} service is not supported by this version of LocalStack, but is available if you upgrade to the latest stable version."
            error_code = 6
        super().__init__(message, error_code)


class LicenseUpgradeRequiredException(AwsServiceAvailabilityException):
    def __init__(self, service_name: str, operation_name: str | None = None):
        if operation_name is None:
            message = f"Sorry, the {service_name} service is not included within your LocalStack license, but is available in an upgraded license. Please refer to {_DOCS_COVERAGE_URL} for more details."
            error_code = 1
        else:
            message = f"Sorry, the {operation_name} operation on the {service_name} service is not supported with your LocalStack license. Please refer to {_DOCS_COVERAGE_URL} for more details."
            error_code = 5
        super().__init__(message, error_code)


def get_service_availability_exception(
    service_name: str,
    operation_name: str | None,
) -> AwsServiceAvailabilityException:
    return ServiceOrOperationNotSupportedException(service_name, operation_name)
