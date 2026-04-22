#!/usr/bin/env bash

set -euo pipefail

USERNAME="transfer-user-tech-assessment"
DURATION=10800  # 3 hours

echo "Creating IAM user"
aws --profile user1 iam create-user --user-name "$USERNAME" > /dev/null || /bin/true

echo "Creating IAM policy"
aws --profile user1 iam put-user-policy \
  --user-name "$USERNAME" \
  --policy-name TransferServiceOnly \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "transfer:CreateServer",
          "transfer:DescribeServer",
          "transfer:DeleteServer",
          "transfer:ListServers",
          "transfer:CreateUser",
          "transfer:DescribeUser",
          "transfer:DeleteUser",
          "transfer:ListUsers"
        ],
        "Resource": "*"
      }
    ]
  }' || /bin/true

echo "Deleting existing user credentials"
aws --profile user1 iam list-access-keys --user-name "$USERNAME" \
  --query 'AccessKeyMetadata[*].AccessKeyId' \
  --output text | tr '\t' '\n' | while read -r KEY_ID; do
    aws --profile user1 iam delete-access-key --user-name "$USERNAME" --access-key-id "$KEY_ID"
    echo "."
done

echo "Generating new user credentials"
KEY_OUTPUT=$(aws --profile user1 iam create-access-key --user-name "$USERNAME")
PERM_KEY_ID=$(echo "$KEY_OUTPUT" | jq .AccessKey.AccessKeyId)
PERM_SECRET=$(echo "$KEY_OUTPUT" | jq .AccessKey.SecretAccessKey)

sleep 10

echo "Generating temporary credentials"
TEMP_OUTPUT=$(AWS_ACCESS_KEY_ID="$PERM_KEY_ID" AWS_SECRET_ACCESS_KEY="$PERM_SECRET" aws --profile user1 sts get-session-token --duration-seconds $DURATION)

TEMP_KEY_ID=$(echo "$TEMP_OUTPUT" | jq .Credentials.AccessKeyId)
TEMP_SECRET=$(echo "$TEMP_OUTPUT" | jq .Credentials.SecretAccessKey)
TEMP_TOKEN=$(echo "$TEMP_OUTPUT" | jq .Credentials.SessionToken)

echo ""
echo "export AWS_ACCESS_KEY_ID=$TEMP_KEY_ID"
echo "export AWS_SECRET_ACCESS_KEY=$TEMP_SECRET"
echo "export AWS_SESSION_TOKEN=$TEMP_TOKEN"
echo "export AWS_DEFAULT_REGION=eu-central-1"
echo ""
