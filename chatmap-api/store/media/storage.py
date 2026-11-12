import asyncio
import logging
from functools import cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.response import StreamingBody

from settings import S3_ENDPOINT_URL, S3_V2_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_KEY

logger = logging.getLogger(__name__)


@cache
def _s3_client():
    s3_client_kwargs = {
        'endpoint_url': S3_ENDPOINT_URL,
    }
    if S3_ACCESS_KEY:
        s3_client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        s3_client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY
    return boto3.client('s3', **s3_client_kwargs)


async def put_object(storage_key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(
        lambda: _s3_client().put_object(
            Bucket=S3_V2_BUCKET_NAME, Key=storage_key, Body=data, ContentType=content_type,
        )
    )


async def get_object(storage_key: str) -> StreamingBody:
    response = await asyncio.to_thread(
        lambda: _s3_client().get_object(Bucket=S3_V2_BUCKET_NAME, Key=storage_key)
    )
    return response["Body"]


async def discard_object(storage_key: str) -> None:
    try:
        await asyncio.to_thread(
            lambda: _s3_client().delete_object(Bucket=S3_V2_BUCKET_NAME, Key=storage_key)
        )
    except (BotoCoreError, ClientError) as error:
        logger.error(f"Discard orphan media object '{storage_key}' failed with: '{error}'")
