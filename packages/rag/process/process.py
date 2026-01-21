"""
Process a single chunk by sending it to an AI model to generate Q&A pairs.
Returns JSONL formatted lines as specified in the spec.
"""
import os
import json
from openai import OpenAI


def process(args):
    """
    Process a single text chunk to generate Q&A pairs in JSONL format.

    According to spec 5-processing.md:
    - Transform content as sequence of question and answer
    - Return sequence of JSONs (one in each line) like:
      {"role": "user", "content": <question>}
      {"role": "assistant", "content": <answer>}

    Args:
        args: dict with 'input' (chunk text) and OpenAI credentials

    Returns:
        dict with 'output' (JSONL string with Q&A pairs)
    """
    chunk_text = args.get("input", "")

    if not chunk_text:
        return {"error": "input is required", "output": ""}

    # Get OpenAI configuration
    api_key = args.get("OPENAI_API_TOKEN", os.getenv("OPENAI_API_TOKEN", "dummy"))
    base_url = args.get("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL"))
    model = args.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))

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

        # Get response text
        response_text = response.choices[0].message.content.strip()

        # The model should return JSONL format directly
        # Validate that it's proper JSONL
        lines = response_text.strip().split('\n')
        validated_lines = []

        for line in lines:
            line = line.strip()
            if line:
                try:
                    # Validate it's valid JSON
                    parsed = json.loads(line)
                    # Ensure it has role and content fields
                    if "role" in parsed and "content" in parsed:
                        validated_lines.append(line)
                except json.JSONDecodeError:
                    # Skip invalid lines
                    continue

        if validated_lines:
            output = '\n'.join(validated_lines)
            return {"output": output}
        else:
            # Fallback: create a simple Q&A if model didn't return proper format
            fallback = [
                json.dumps({"role": "user", "content": "What information is provided in this text?"}),
                json.dumps({"role": "assistant", "content": chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text})
            ]
            return {"output": '\n'.join(fallback)}

    except Exception as e:
        return {"error": f"Failed to process chunk: {str(e)}", "output": ""}
   