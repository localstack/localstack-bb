import glob
import importlib
import io
import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Callable
from typing import Any

from localstack.aws.connect import connect_to
from localstack.testing.aws.util import is_aws_cloud
from localstack.utils.aws import arns
from localstack.utils.aws.request_context import mock_aws_request_headers
from localstack.utils.urls import localstack_host

try:
    from typing import Literal
except ImportError:
    from typing import Literal

import boto3
import requests

from localstack import config
from localstack.constants import (
    LOCALSTACK_ROOT_FOLDER,
    LOCALSTACK_VENV_FOLDER,
)
from localstack.testing.config import (
    TEST_AWS_ACCESS_KEY_ID,
    TEST_AWS_ACCOUNT_ID,
    TEST_AWS_REGION_NAME,
)
from localstack.utils.archives import create_zip_file_cli, create_zip_file_python
from localstack.utils.collections import ensure_list
from localstack.utils.files import (
    TMP_FILES,
    chmod_r,
    cp_r,
    is_empty_dir,
    load_file,
    mkdir,
    rm_rf,
    save_file,
)
from localstack.utils.platform import is_debian
from localstack.utils.strings import short_uid, to_str

ARCHIVE_DIR_PREFIX = "lambda.archive."
DEFAULT_GET_LOG_EVENTS_DELAY = 3


def is_local_test_mode():
    return config.is_local_test_mode()


def create_zip_file(
    file_path: str,
    zip_file: str = None,
    get_content: bool = False,
    content_root: str = None,
    mode: Literal["r", "w", "x", "a"] = "w",
):
    """
    Creates a zipfile to the designated file_path.

    By default, a new zip file is created but the mode parameter can be used to append to an existing zip file
    """
    base_dir = file_path
    if not os.path.isdir(file_path):
        base_dir = tempfile.mkdtemp(prefix=ARCHIVE_DIR_PREFIX)
        shutil.copy(file_path, base_dir)
        TMP_FILES.append(base_dir)
    tmp_dir = tempfile.mkdtemp(prefix=ARCHIVE_DIR_PREFIX)
    full_zip_file = zip_file
    if not full_zip_file:
        zip_file_name = "archive.zip"
        full_zip_file = os.path.join(tmp_dir, zip_file_name)
    # special case where target folder is empty -> create empty zip file
    if is_empty_dir(base_dir):
        # see https://stackoverflow.com/questions/25195495/how-to-create-an-empty-zip-file#25195628
        content = (
            b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        if get_content:
            return content
        save_file(full_zip_file, content)
        return full_zip_file

    # TODO: using a different packaging method here also produces wildly different .zip package sizes
    if is_debian() and "PYTEST_CURRENT_TEST" not in os.environ:
        # todo: extend CLI with the new parameters
        create_zip_file_cli(source_path=file_path, base_dir=base_dir, zip_file=full_zip_file)
    else:
        create_zip_file_python(
            base_dir=base_dir, zip_file=full_zip_file, mode=mode, content_root=content_root
        )
    if not get_content:
        TMP_FILES.append(tmp_dir)
        return full_zip_file
    with open(full_zip_file, "rb") as file_obj:
        zip_file_content = file_obj.read()
    rm_rf(tmp_dir)
    return zip_file_content


def assert_objects(asserts, all_objects):
    if type(asserts) is not list:
        asserts = [asserts]
    for obj in asserts:
        assert_object(obj, all_objects)


def assert_object(expected_object, all_objects):
    # for Python 3 compatibility
    dict_values = type({}.values())
    if isinstance(all_objects, dict_values):
        all_objects = list(all_objects)
    # wrap single item in an array
    if type(all_objects) is not list:
        all_objects = [all_objects]
    found = find_object(expected_object, all_objects)
    if not found:
        raise Exception(f"Expected object not found: {expected_object} in list {all_objects}")


def find_object(expected_object, object_list):
    for obj in object_list:
        if isinstance(obj, list):
            found = find_object(expected_object, obj)
            if found:
                return found

        all_ok = True
        if obj != expected_object:
            if not isinstance(expected_object, dict):
                all_ok = False
            else:
                for k, v in expected_object.items():
                    if not find_recursive(k, v, obj):
                        all_ok = False
                        break
        if all_ok:
            return obj
    return None


def find_recursive(key, value, obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and v == value:
                return True
            if find_recursive(key, value, v):
                return True
    elif isinstance(obj, list):
        for o in obj:
            if find_recursive(key, value, o):
                return True
    else:
        return False


def list_all_s3_objects(s3_client):
    return map_all_s3_objects(s3_client=s3_client).values()


def delete_all_s3_objects(s3_client, buckets: str | list[str]):
    buckets = ensure_list(buckets)
    for bucket in buckets:
        keys = all_s3_object_keys(s3_client, bucket)
        deletes = [{"Key": key} for key in keys]
        if deletes:
            s3_client.delete_objects(Bucket=bucket, Delete={"Objects": deletes})


def download_s3_object(s3_client, bucket, path):
    body = s3_client.get_object(Bucket=bucket, Key=path)["Body"]
    result = body.read()
    try:
        result = to_str(result)
    except Exception:
        pass
    return result


def all_s3_object_keys(s3_client, bucket: str) -> list[str]:
    response = s3_client.list_objects_v2(Bucket=bucket)
    keys = [obj["Key"] for obj in response.get("Contents", [])]
    return keys


def map_all_s3_objects(
    s3_client, to_json: bool = True, buckets: str | list[str] = None
) -> dict[str, Any]:
    result = {}
    buckets = ensure_list(buckets)
    if not buckets:
        # get all buckets
        response = s3_client.list_buckets()
        buckets = [b["Name"] for b in response["Buckets"]]

    for bucket in buckets:
        response = s3_client.list_objects_v2(Bucket=bucket)
        objects = [obj["Key"] for obj in response.get("Contents", [])]
        for key in objects:
            value = download_s3_object(s3_client, bucket, key)
            try:
                if to_json:
                    value = json.loads(value)
                separator = "" if key.startswith("/") else "/"
                result[f"{bucket}{separator}{key}"] = value
            except Exception:
                # skip non-JSON or binary objects
                pass
    return result


def send_describe_dynamodb_ttl_request(table_name):
    return send_dynamodb_request("", "DescribeTimeToLive", json.dumps({"TableName": table_name}))


def send_update_dynamodb_ttl_request(table_name, ttl_status):
    return send_dynamodb_request(
        "",
        "UpdateTimeToLive",
        json.dumps(
            {
                "TableName": table_name,
                "TimeToLiveSpecification": {
                    "AttributeName": "ExpireItem",
                    "Enabled": ttl_status,
                },
            }
        ),
    )


def send_dynamodb_request(path, action, request_body):
    headers = {
        "Host": "dynamodb.amazonaws.com",
        "x-amz-target": f"DynamoDB_20120810.{action}",
        "Authorization": mock_aws_request_headers(
            "dynamodb", aws_access_key_id=TEST_AWS_ACCESS_KEY_ID, region_name=TEST_AWS_REGION_NAME
        )["Authorization"],
    }
    url = f"{config.internal_service_url()}/{path}"
    return requests.put(url, data=request_body, headers=headers, verify=False)


def get_lambda_log_group_name(function_name):
    return f"/aws/lambda/{function_name}"


# TODO: make logs_client mandatory
def check_expected_lambda_log_events_length(
    expected_length, function_name, regex_filter=None, logs_client=None
):
    events = get_lambda_log_events(
        function_name, regex_filter=regex_filter, logs_client=logs_client
    )
    events = [line for line in events if line not in ["\x1b[0m", "\\x1b[0m"]]
    if len(events) != expected_length:
        print(
            "Invalid # of Lambda {} log events: {} / {}: {}".format(
                function_name,
                len(events),
                expected_length,
                [
                    event if len(event) < 1000 else f"{event[:1000]}... (truncated)"
                    for event in events
                ],
            )
        )
    assert len(events) == expected_length
    return events


def list_all_log_events(log_group_name: str, logs_client=None) -> list[dict]:
    logs = logs_client or connect_to().logs
    return list_all_resources(
        lambda kwargs: logs.filter_log_events(logGroupName=log_group_name, **kwargs),
        last_token_attr_name="nextToken",
        list_attr_name="events",
    )


def get_lambda_log_events(
    function_name,
    delay_time=DEFAULT_GET_LOG_EVENTS_DELAY,
    regex_filter: str | None = None,
    log_group=None,
    logs_client=None,
):
    def get_log_events(func_name, delay):
        time.sleep(delay)
        log_group_name = log_group or get_lambda_log_group_name(func_name)
        return list_all_log_events(log_group_name, logs_client)

    try:
        events = get_log_events(function_name, delay_time)
    except Exception as e:
        if "ResourceNotFoundException" in str(e):
            return []
        raise

    rs = []
    for event in events:
        raw_message = event["message"]
        if (
            not raw_message
            or raw_message.startswith("INIT_START")
            or raw_message.startswith("START")
            or raw_message.startswith("END")
            or raw_message.startswith(
                "REPORT"
            )  # necessary until tail is updated in docker images. See this PR:
            # http://git.savannah.gnu.org/gitweb/?p=coreutils.git;a=commitdiff;h=v8.24-111-g1118f32
            or "tail: unrecognized file system type" in raw_message
            or regex_filter
            and not re.search(regex_filter, raw_message)
        ):
            continue
        if raw_message in ["\x1b[0m", "\\x1b[0m"]:
            continue

        try:
            rs.append(json.loads(raw_message))
        except Exception:
            rs.append(raw_message)

    return rs


def list_all_resources(
    page_function: Callable[[dict], Any],
    last_token_attr_name: str,
    list_attr_name: str,
    next_token_attr_name: str | None = None,
) -> list:
    """
    List all available resources by loading all available pages using `page_function`.

    :type page_function: Callable
    :param page_function: callable function or lambda that accepts kwargs with next token
                          and returns the next results page

    :type last_token_attr_name: str
    :param last_token_attr_name: where to look for the last evaluated token

    :type list_attr_name: str
    :param list_attr_name: where to look for the list of items

    :type next_token_attr_name: Optional[str]
    :param next_token_attr_name: name of kwarg with the next token, default is the same as `last_token_attr_name`

    Example usage:

        all_log_groups = list_all_resources(
            lambda kwargs: logs.describe_log_groups(**kwargs),
            last_token_attr_name="nextToken",
            list_attr_name="logGroups"
        )

        all_records = list_all_resources(
            lambda kwargs: dynamodb.scan(**{**kwargs, **dynamodb_kwargs}),
            last_token_attr_name="LastEvaluatedKey",
            next_token_attr_name="ExclusiveStartKey",
            list_attr_name="Items"
        )
    """

    if next_token_attr_name is None:
        next_token_attr_name = last_token_attr_name

    result = None
    collected_items = []
    last_evaluated_token = None

    while not result or last_evaluated_token:
        kwargs = {next_token_attr_name: last_evaluated_token} if last_evaluated_token else {}
        result = page_function(kwargs)
        last_evaluated_token = result.get(last_token_attr_name)
        collected_items += result.get(list_attr_name, [])

    return collected_items


def response_arn_matches_partition(client, response_arn: str) -> bool:
    parsed_arn = arns.parse_arn(response_arn)
    return (
        client.meta.partition
        == boto3.session.Session().get_partition_for_region(parsed_arn["region"])
        and client.meta.partition == parsed_arn["partition"]
    )


def upload_file_to_bucket(s3_client, bucket_name, file_path, file_name=None):
    key = file_name or f"file-{short_uid()}"

    s3_client.upload_file(
        file_path,
        Bucket=bucket_name,
        Key=key,
    )

    domain = "amazonaws.com" if is_aws_cloud() else localstack_host().host_and_port()
    url = f"https://{bucket_name}.s3.{domain}/{key}"

    return {"Bucket": bucket_name, "Key": key, "Url": url}
