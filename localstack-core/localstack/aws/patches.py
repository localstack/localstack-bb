from localstack.runtime import hooks


@hooks.on_infra_start(priority=100)
def apply_aws_runtime_patches():
    pass
