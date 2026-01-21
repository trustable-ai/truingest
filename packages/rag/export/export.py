"""
Export chunks as Q&A pairs in JSONL format using OpenAI-compatible API.
Processes all chunks from an S3 key, generates JSONL, and saves to S3.
"""
import os
import json
import boto3
from openai import OpenAI
from datetime import datetime


def export(args):
    """
    Process all chunks from S3 into Q&A pairs and save as JSONL to S3.

    Args:
        args: dict with 's3_key' (chunks file) and OpenAI/S3 credentials

    Returns:
        dict with 's3_jsonl_key' (S3 path to JSONL), 'num_pairs' (count), and 'download_url' (signed URL)
    """
    s3_key = args.get("s3_key", "")

    if not s3_key:
        return {"error": "s3_key is required", "s3_jsonl_key": "", "num_pairs": 0}

    # Get S3 configuration
    host = args.get("S3_HOST", os.getenv("S3_HOST"))
    port = args.get("S3_PORT", os.getenv("S3_PORT"))
    s3_url = f"http://{host}:{port}"
    access_key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
    secret_key = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
    bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))

    # Initialize S3 client
    try:
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            endpoint_url=s3_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # Retrieve chunks from S3
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        chunks_data = json.loads(response['Body'].read().decode('utf-8'))
        chunks = chunks_data.get("chunks", [])

    except Exception as e:
        return {"error": f"Failed to retrieve chunks from S3: {str(e)}", "s3_jsonl_key": "", "num_pairs": 0}

    if not chunks:
        return {"error": "No chunks found", "s3_jsonl_key": "", "num_pairs": 0}

    # Get OpenAI configuration (supports both OpenAI and Ollama via base_url)
    api_key = args.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "dummy"))
    base_url = args.get("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL"))
    model = args.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))

    # Process each chunk into Q&A pairs
    jsonl_lines = []
    for chunk in chunks:
        try:
            qa_pair = generate_qa_pair(chunk, api_key, base_url, model)
            if qa_pair:
                # Add user line with role/content format
                jsonl_lines.append(json.dumps({"role": "user", "content": qa_pair["question"]}))
                # Add assistant line with role/content format
                jsonl_lines.append(json.dumps({"role": "assistant", "content": qa_pair["answer"]}))
        except Exception as e:
            print(f"Warning: Failed to process chunk: {e}")
            continue

    # Join all lines with newlines
    jsonl_content = "\n".join(jsonl_lines)
    num_pairs = len(jsonl_lines) // 2

    # Save JSONL to S3
    try:
        # Extract base filename from chunks S3 key
        # E.g., chunks/chunks_20260121_123456.json -> chunks_20260121_123456.jsonl
        base_name = s3_key.split('/')[-1].replace('.json', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        jsonl_s3_key = f"exports/{base_name}_{timestamp}.jsonl"

        s3_client.put_object(
            Bucket=bucket,
            Key=jsonl_s3_key,
            Body=jsonl_content.encode('utf-8'),
            ContentType='application/jsonl'
        )

        # Use S3_PUBLIC for public download URL
        s3_public = args.get("S3_PUBLIC", os.getenv("S3_PUBLIC"))
        if s3_public:
            # Build public URL: http://S3_PUBLIC/bucket/key
            download_url = f"{s3_public}/{bucket}/{jsonl_s3_key}"
        else:
            # Fallback to internal URL if S3_PUBLIC not set
            download_url = f"{s3_url}/{bucket}/{jsonl_s3_key}"

        return {
            "s3_jsonl_key": jsonl_s3_key,
            "num_pairs": num_pairs,
            "num_chunks_processed": len(chunks),
            "download_url": download_url
        }

    except Exception as e:
        return {"error": f"Failed to save JSONL to S3: {str(e)}", "s3_jsonl_key": "", "num_pairs": num_pairs}


def generate_qa_pair(chunk_text, api_key, base_url, model):
    """
    Generate a question-answer pair from a text chunk using OpenAI-compatible API.

    Args:
        chunk_text: text chunk to process
        api_key: API key
        base_url: API base URL (OpenAI or Ollama)
        model: model name

    Returns:
        dict with 'question' and 'answer' keys, or None if failed
    """
    try:
        # Use OpenAI client (works with both OpenAI and Ollama)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # Exact prompt from spec 5-processing.md
        prompt = f"""Transform the content of the following text
as a sequence of question and answer related to it.
return a sequence of jsons (one in each like) like this:

{{"role": "user", "content": <question>}}
{{"role": "assistant", "content": <answer>}}

Text:
{chunk_text}"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        # Parse response
        response_text = response.choices[0].message.content.strip()

        # Parse JSONL response - take first user/assistant pair
        lines = response_text.strip().split('\n')
        question = None
        answer = None

        for line in lines:
            line = line.strip()
            if line:
                try:
                    parsed = json.loads(line)
                    if parsed.get("role") == "user" and not question:
                        question = parsed.get("content", "")
                    elif parsed.get("role") == "assistant" and not answer:
                        answer = parsed.get("content", "")

                    # Got both, we're done
                    if question and answer:
                        break
                except json.JSONDecodeError:
                    continue

        if question and answer:
            return {"question": question, "answer": answer}

        # Fallback: create simple Q&A
        return {
            "question": "What information is provided in this text?",
            "answer": chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text
        }

    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return None
