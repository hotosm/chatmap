import boto3
import os
from botocore.exceptions import NoCredentialsError
from datetime import datetime

def upload_to_s3(local_file_path, bucket_name, s3_object_name=None):
    """
    Upload a file to an S3 bucket.
    """
    # Check if the file exists
    if not os.path.exists(local_file_path):
        print(f"Skipping: '{local_file_path}'")
        return False

    if s3_object_name is None:
        s3_object_name = local_file_path.split('/')[-1]

    s3_client = boto3.client('s3')

    try:
        print(f"Uploading {local_file_path} to {bucket_name} as {s3_object_name}...")
        s3_client.upload_file(local_file_path, bucket_name, s3_object_name)
        print("Upload Successful!")
        return True
    except NoCredentialsError:
        print("Credentials not found. Please run 'aws configure'.")
        return False
    except Exception as e:
        print(f"An error occurred while uploading {local_file_path}: {e}")
        return False

# Configuration
FILES_TO_UPLOAD = ['backup.sql.gz', 'media.tgz']
BUCKET_NAME = 'hotosm-chatmap-data'
current_date = datetime.now().strftime('%Y-%m-%d')

# Files to upload
TARGET_NAMES = [
    f'backup/{current_date}-backup-db.sql.gz',
    f'backup/{current_date}-backup-media.tgz'
]

# Upload files
for local_file, target_name in zip(FILES_TO_UPLOAD, TARGET_NAMES):
    upload_to_s3(local_file, BUCKET_NAME, target_name)
