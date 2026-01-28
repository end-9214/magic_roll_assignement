import boto3
from botocore.exceptions import NoCredentialsError
import os
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()
# AWS Credentials (Ensure you have set them in ~/.aws/credentials or environment variables)
# 1. Account ID
AccountID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

# 2. Bucket name
Bucket = os.getenv("CLOUDFLARE_BUCKET_NAME")

# 3. Client access key
ClientAccessKey = os.getenv("CLOUDFLARE_CLIENT_ACCESS_KEY")

# 4. Client secret
ClientSecret = os.getenv("CLOUDFLARE_CLIENT_SECRET")

# 5. Connection url
ConnectionUrl = f"https://{AccountID}.r2.cloudflarestorage.com"
# Initialize S3 Client
s3_client = boto3.client(
    "s3",
    endpoint_url=ConnectionUrl,
    aws_access_key_id=ClientAccessKey,
    aws_secret_access_key=ClientSecret,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket"""
    print(file_name)
    if object_name is None:
        object_name = "videos/" + file_name

    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        print(f"File {file_name} uploaded to {bucket}/{object_name}")
        print(response)
        return f"{os.getenv('CLOUDFLARE_PUBLIC_URL')}" + "/" + object_name
    except NoCredentialsError:
        print("AWS Credentials not found")


def download_file(bucket, object_name, file_name):
    """Download a file from an S3 bucket"""
    try:
        s3_client.download_file(bucket, object_name, file_name)
        print(f"File {object_name} downloaded as {file_name}")
    except NoCredentialsError:
        print("AWS Credentials not found")


def list_files(bucket):
    """List files in an S3 bucket"""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket)
        if "Contents" in response:
            for obj in response["Contents"]:
                print(obj["Key"])
        else:
            print("No files found in the bucket")
    except NoCredentialsError:
        print("AWS Credentials not found")


def delete_file(bucket, object_name):
    """Delete a file from an S3 bucket"""
    try:
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        print(f"File {object_name} deleted from {bucket}")
    except NoCredentialsError:
        print("AWS Credentials not found")