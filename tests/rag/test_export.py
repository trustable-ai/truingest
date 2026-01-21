import sys
import json
from unittest.mock import MagicMock, patch
sys.path.insert(0, "packages/rag/export")
from export import export as export_func, generate_qa_with_ollama

def test_export_no_s3_key():
    """Test export with missing s3_key"""
    res = export_func({})
    assert "error" in res
    assert res["num_pairs"] == 0
    assert res["jsonl"] == ""

def test_export_s3_failure():
    """Test export when S3 retrieval fails"""
    with patch('export.boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = Exception("S3 error")
        mock_boto.return_value = mock_s3

        res = export_func({
            "s3_key": "chunks/test.json",
            "S3_HOST": "localhost",
            "S3_PORT": "9000",
            "S3_ACCESS_KEY": "test",
            "S3_SECRET_KEY": "test",
            "S3_BUCKET_DATA": "test-bucket"
        })

        assert "error" in res
        assert "Failed to retrieve chunks" in res["error"]

def test_export_empty_chunks():
    """Test export with empty chunks list"""
    with patch('export.boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_response = {
            'Body': MagicMock()
        }
        mock_response['Body'].read.return_value = json.dumps({"chunks": []}).encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        mock_boto.return_value = mock_s3

        res = export_func({
            "s3_key": "chunks/test.json",
            "S3_HOST": "localhost",
            "S3_PORT": "9000",
            "S3_ACCESS_KEY": "test",
            "S3_SECRET_KEY": "test",
            "S3_BUCKET_DATA": "test-bucket"
        })

        assert "error" in res
        assert res["num_pairs"] == 0

def test_export_success():
    """Test successful export with mocked Ollama"""
    chunks_data = {
        "chunks": [
            "Python is a programming language.",
            "JavaScript is used for web development."
        ],
        "num_chunks": 2
    }

    with patch('export.boto3.client') as mock_boto, \
         patch('export.generate_qa_with_ollama') as mock_generate:

        # Mock S3 retrieval
        mock_s3 = MagicMock()
        mock_response = {
            'Body': MagicMock()
        }
        mock_response['Body'].read.return_value = json.dumps(chunks_data).encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        mock_boto.return_value = mock_s3

        # Mock Q&A generation
        mock_generate.side_effect = [
            {"question": "What is Python?", "answer": "Python is a programming language."},
            {"question": "What is JavaScript?", "answer": "JavaScript is used for web development."}
        ]

        res = export_func({
            "s3_key": "chunks/test.json",
            "S3_HOST": "localhost",
            "S3_PORT": "9000",
            "S3_ACCESS_KEY": "test",
            "S3_SECRET_KEY": "test",
            "S3_BUCKET_DATA": "test-bucket",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OLLAMA_MODEL": "llama2"
        })

        assert "error" not in res
        assert res["num_pairs"] == 2
        assert res["num_chunks_processed"] == 2

        # Verify JSONL format
        lines = res["jsonl"].split("\n")
        assert len(lines) == 4

        # Check format: {"user": ...} then {"assistant": ...}
        line1 = json.loads(lines[0])
        assert "user" in line1
        assert line1["user"] == "What is Python?"

        line2 = json.loads(lines[1])
        assert "assistant" in line2
        assert line2["assistant"] == "Python is a programming language."

def test_generate_qa_with_ollama_success():
    """Test Q&A generation with successful Ollama response"""
    chunk = "Machine learning is a subset of AI."

    with patch('export.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of AI."
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        qa = generate_qa_with_ollama(chunk, "http://localhost:11434/v1", "llama2")

        assert qa is not None
        assert qa["question"] == "What is machine learning?"
        assert qa["answer"] == "Machine learning is a subset of AI."

def test_generate_qa_with_ollama_invalid_json():
    """Test Q&A generation with non-JSON response"""
    chunk = "Test content"

    with patch('export.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not JSON"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        qa = generate_qa_with_ollama(chunk, "http://localhost:11434/v1", "llama2")

        # Should fallback to default question
        assert qa is not None
        assert qa["question"] == "What information is provided in this text?"
        assert "Test content" in qa["answer"]

def test_generate_qa_with_ollama_failure():
    """Test Q&A generation when Ollama fails"""
    chunk = "Test content"

    with patch('export.OpenAI') as mock_openai:
        mock_openai.side_effect = Exception("Connection error")

        qa = generate_qa_with_ollama(chunk, "http://localhost:11434/v1", "llama2")

        assert qa is None

def test_export_partial_failure():
    """Test export when some chunks fail to process"""
    chunks_data = {
        "chunks": [
            "Chunk 1",
            "Chunk 2",
            "Chunk 3"
        ],
        "num_chunks": 3
    }

    with patch('export.boto3.client') as mock_boto, \
         patch('export.generate_qa_with_ollama') as mock_generate:

        # Mock S3 retrieval
        mock_s3 = MagicMock()
        mock_response = {
            'Body': MagicMock()
        }
        mock_response['Body'].read.return_value = json.dumps(chunks_data).encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        mock_boto.return_value = mock_s3

        # Mock Q&A generation - one fails, two succeed
        mock_generate.side_effect = [
            {"question": "Q1?", "answer": "A1"},
            None,  # This one fails
            {"question": "Q3?", "answer": "A3"}
        ]

        res = export_func({
            "s3_key": "chunks/test.json",
            "S3_HOST": "localhost",
            "S3_PORT": "9000",
            "S3_ACCESS_KEY": "test",
            "S3_SECRET_KEY": "test",
            "S3_BUCKET_DATA": "test-bucket"
        })

        # Should have 2 Q&A pairs (4 lines total)
        assert res["num_pairs"] == 2
        assert res["num_chunks_processed"] == 3
        lines = res["jsonl"].split("\n")
        assert len(lines) == 4
