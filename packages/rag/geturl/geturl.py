"""
Generate a browser-usable download URL for an object stored in the S3 data bucket.

Returns a presigned GET URL (valid for 1 hour) via ctx.S3_CLIENT, plus a public
URL derived from ctx.S3_PUBLIC when available. The frontend uses `download_url`.

All S3 access goes through the generated ctx.S3_CLIENT / ctx.S3_DATA wiring.
"""


def _client(ctx):
    if not ctx or not hasattr(ctx, "S3_CLIENT") or ctx.S3_CLIENT is None:
        raise RuntimeError("S3 non configurato")
    return ctx.S3_CLIENT, getattr(ctx, "S3_DATA", None), getattr(ctx, "S3_PUBLIC", None)


def main(args, ctx=None):
    s3_key = args.get("s3_key") or args.get("key") or args.get("filename")

    if not s3_key:
        return {"error": "s3_key is required"}

    try:
        client, bucket, s3_public = _client(ctx)
        if not bucket:
            return {"error": "S3 data bucket not configured"}

        # Presigned GET URL (works for private buckets; valid 1 hour).
        presigned = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=3600,
        )

        result = {
            "download_url": presigned,
            "s3_key": s3_key,
            "bucket": bucket,
        }

        # Public URL when a public S3 endpoint is configured.
        if s3_public:
            public_url = f"{s3_public}/{bucket}/{s3_key}"
            result["public_url"] = public_url
            # Prefer the public URL for browser downloads when available.
            result["download_url"] = public_url

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate download URL: {str(e)}"}