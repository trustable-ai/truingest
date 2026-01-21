"""
Chunk text using empty lines as separators.
Stores chunks in S3 and returns the list of chunks.
"""
import os
import json
import boto3

def chunk(args):
    """
    Split text into chunks using empty lines as separators.
    Each paragraph (text between empty lines) becomes a chunk.

    Args:
        args: dict with 'input' (text to chunk) and optional S3 credentials

    Returns:
        dict with 'output' (list of chunks) and 's3_key' if stored
    """
    input_text = args.get("input", "")

    if not input_text:
        return {"output": []}

    # Split by empty lines (one or more consecutive newlines)
    # This creates chunks separated by blank lines
    chunks = []
    current_chunk = []

    for line in input_text.split('\n'):
        if line.strip():  # Non-empty line
            current_chunk.append(line)
        else:  # Empty line - end current chunk
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []

    # Add the last chunk if there's any content
    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    # Store in S3 if credentials provided
    s3_key = None
    if args.get("S3_HOST"):
        s3_key = store_chunks_in_s3(chunks, args)

    return {
        "output": chunks,
        "s3_key": s3_key,
        "num_chunks": len(chunks)
    }


def store_chunks_in_s3(chunks, args):
    """
    Store chunks in S3 as JSONL with format {"assistant": <chunk>}.

    According to spec 4-chunk.md:
    - Save all chunks as a single JSONL file
    - Each line in format: {"assistant": <chunk>}

    Args:
        chunks: list of text chunks
        args: dict with S3 credentials

    Returns:
        S3 key where chunks are stored
    """
    try:
        # Get S3 configuration
        host = args.get("S3_HOST", os.getenv("S3_HOST"))
        port = args.get("S3_PORT", os.getenv("S3_PORT"))
        s3_url = f"http://{host}:{port}"
        access_key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
        secret_key = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
        bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))

        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            endpoint_url=s3_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # Generate S3 key
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"chunks/chunks_{timestamp}.jsonl"

        # Create JSONL content with format {"assistant": <chunk>}
        jsonl_lines = []
        for chunk in chunks:
            jsonl_lines.append(json.dumps({"assistant": chunk}))

        jsonl_content = '\n'.join(jsonl_lines)

        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=jsonl_content.encode('utf-8'),
            ContentType='application/jsonl'
        )

        return s3_key

    except Exception as e:
        # If S3 storage fails, just log and continue
        print(f"Warning: Failed to store chunks in S3: {e}")
        return None

