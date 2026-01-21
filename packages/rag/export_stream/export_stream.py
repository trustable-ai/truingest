"""
Export chunks as Q&A pairs in JSONL format with streaming support.
Processes chunks one by one, streaming results and saving incrementally to S3.
"""
import os
import json
import boto3
from openai import OpenAI
from datetime import datetime


def export_stream(args):
    """
    Stream processing of chunks into Q&A pairs, saving incrementally to S3.

    Yields SSE events for each processed chunk and final completion.

    Args:
        args: dict with 's3_key' (chunks file) and OpenAI/S3 credentials

    Yields:
        String events in SSE format with chunk processing results
    """
    s3_key = args.get("s3_key", "")

    if not s3_key:
        yield f"data: {json.dumps({'error': 's3_key is required'})}\n\n"
        return

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
        yield f"data: {json.dumps({'error': f'Failed to retrieve chunks: {str(e)}'})}\n\n"
        return

    if not chunks:
        yield f"data: {json.dumps({'error': 'No chunks found'})}\n\n"
        return

    # Get OpenAI configuration
    api_key = args.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "dummy"))
    base_url = args.get("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL"))
    model = args.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))

    # Prepare JSONL file path
    base_name = s3_key.split('/')[-1].replace('.json', '')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_s3_key = f"exports/{base_name}_{timestamp}.jsonl"

    # Send initial event with total chunks and file info
    yield f"data: {json.dumps({'type': 'start', 'total_chunks': len(chunks), 's3_key': jsonl_s3_key})}\n\n"

    # Process each chunk and stream results
    processed_count = 0
    jsonl_content = ""

    for idx, chunk in enumerate(chunks):
        try:
            # Generate Q&A pair
            qa_pair = generate_qa_pair(chunk, api_key, base_url, model)

            if qa_pair:
                # Create JSONL lines
                user_line = json.dumps({"role": "user", "content": qa_pair["question"]})
                assistant_line = json.dumps({"role": "assistant", "content": qa_pair["answer"]})

                # Append to content
                if jsonl_content:
                    jsonl_content += "\n"
                jsonl_content += user_line + "\n" + assistant_line

                # Save intermediate result to S3 (append mode simulation)
                s3_client.put_object(
                    Bucket=bucket,
                    Key=jsonl_s3_key,
                    Body=jsonl_content.encode('utf-8'),
                    ContentType='application/jsonl'
                )

                processed_count += 1

                # Stream the processed chunk result
                yield f"data: {json.dumps({'type': 'chunk', 'index': idx, 'question': qa_pair['question'], 'answer': qa_pair['answer'], 'processed': processed_count, 'total': len(chunks)})}\n\n"
            else:
                # Stream error for this chunk
                yield f"data: {json.dumps({'type': 'chunk_error', 'index': idx, 'error': 'Failed to generate Q&A'})}\n\n"

        except Exception as e:
            # Stream error for this chunk
            yield f"data: {json.dumps({'type': 'chunk_error', 'index': idx, 'error': str(e)})}\n\n"

    # Build download URL
    s3_public = args.get("S3_PUBLIC", os.getenv("S3_PUBLIC"))
    if s3_public:
        download_url = f"{s3_public}/{bucket}/{jsonl_s3_key}"
    else:
        download_url = f"{s3_url}/{bucket}/{jsonl_s3_key}"

    # Send completion event
    yield f"data: {json.dumps({'type': 'complete', 's3_jsonl_key': jsonl_s3_key, 'num_pairs': processed_count, 'download_url': download_url})}\n\n"


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

        # Fallback
        return {
            "question": "What information is provided in this text?",
            "answer": chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text
        }

    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return None
