"""
Download action to provide signed/public URLs for JSONL files in S3.
"""
import os
import boto3


def download(args):
    """
    Generate a download URL for a JSONL file stored in S3.

    Args:
        args: dict with 's3_key' and S3 credentials

    Returns:
        dict with 'download_url' (public or signed URL)
    """
    s3_key = args.get("s3_key", "")

    if not s3_key:
        return {"error": "s3_key is required"}

    # Get S3 configuration
    host = args.get("S3_HOST", os.getenv("S3_HOST"))
    port = args.get("S3_PORT", os.getenv("S3_PORT"))
    s3_url = f"http://{host}:{port}"
    access_key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
    secret_key = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
    bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))
    s3_public = args.get("S3_PUBLIC", os.getenv("S3_PUBLIC"))

    try:
        # If S3_PUBLIC is available, use it for public URL
        if s3_public:
            download_url = f"{s3_public}/{bucket}/{s3_key}"
        else:
            # Otherwise, generate a signed URL (expires in 1 hour)
            s3_client = boto3.client(
                's3',
                region_name='us-east-1',
                endpoint_url=s3_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )

            download_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=3600  # 1 hour
            )

        return {"download_url": download_url}

    except Exception as e:
        return {"error": f"Failed to generate download URL: {str(e)}"}
