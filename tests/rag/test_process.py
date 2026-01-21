import sys
import json
from unittest.mock import MagicMock, patch
sys.path.insert(0, "packages/rag/process")
from process import process as process_func


def test_process_empty_input():
    """Test processing with empty input"""
    res = process_func({})
    assert res.get("error") == "input is required"
    assert res.get("output") == ""


def test_process_with_mock_llm():
    """Test processing a single chunk with successful LLM response"""
    text = "Python is a high-level programming language known for its simplicity."

    with patch('process.OpenAI') as mock_openai:
        # Create mock response with proper JSONL format
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Simulate JSONL response from the model
        mock_response.choices[0].message.content = '''{"role": "user", "content": "What is Python?"}
{"role": "assistant", "content": "Python is a high-level programming language known for its simplicity."}'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        res = process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy",
            "OPENAI_BASE_URL": "http://localhost:11434/v1",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        })

        assert "output" in res
        assert "error" not in res

        # Parse the JSONL output
        lines = res["output"].strip().split('\n')
        assert len(lines) == 2

        user_msg = json.loads(lines[0])
        assistant_msg = json.loads(lines[1])

        assert user_msg["role"] == "user"
        assert assistant_msg["role"] == "assistant"
        assert "What is Python?" in user_msg["content"]


def test_process_invalid_json_response():
    """Test processing when LLM returns non-JSON response"""
    text = "Machine learning is a subset of artificial intelligence."

    with patch('process.OpenAI') as mock_openai:
        # Create mock response with invalid JSON
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        res = process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy"
        })

        # Should fall back to default question/answer
        assert "output" in res
        lines = res["output"].strip().split('\n')
        assert len(lines) == 2

        user_msg = json.loads(lines[0])
        assert user_msg["content"] == "What information is provided in this text?"


def test_process_llm_failure():
    """Test processing with LLM failure (uses fallback)"""
    text = "Test document content."

    with patch('process.OpenAI') as mock_openai:
        # Simulate LLM failure
        mock_openai.side_effect = Exception("API error")

        res = process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy"
        })

        # Should return error
        assert "error" in res
        assert "Failed to process chunk" in res["error"]


def test_output_format():
    """Test that output format matches spec: {"role": "user/assistant", "content": ...}"""
    text = "Test text for format validation."

    with patch('process.OpenAI') as mock_openai:
        # Create mock response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{"role": "user", "content": "What is this test about?"}
{"role": "assistant", "content": "This test validates the output format."}'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        res = process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy"
        })

        # Verify format
        assert "output" in res
        lines = res["output"].strip().split('\n')
        assert len(lines) == 2

        # Parse both lines
        user_msg = json.loads(lines[0])
        assistant_msg = json.loads(lines[1])

        assert user_msg == {"role": "user", "content": "What is this test about?"}
        assert assistant_msg == {"role": "assistant", "content": "This test validates the output format."}


def test_process_partial_valid_json():
    """Test processing when LLM returns mix of valid and invalid JSON lines"""
    text = "Test content"

    with patch('process.OpenAI') as mock_openai:
        # Create mock response with mixed valid/invalid lines
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{"role": "user", "content": "Valid question?"}
This is not JSON
{"role": "assistant", "content": "Valid answer."}
Also not JSON'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        res = process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy"
        })

        # Should only include valid lines
        assert "output" in res
        lines = res["output"].strip().split('\n')
        assert len(lines) == 2

        # Both should be valid JSON
        user_msg = json.loads(lines[0])
        assistant_msg = json.loads(lines[1])
        assert user_msg["role"] == "user"
        assert assistant_msg["role"] == "assistant"


def test_process_prompt_format():
    """Test that the exact prompt from spec is used"""
    text = "Sample text"

    with patch('process.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{"role": "user", "content": "Q?"}
{"role": "assistant", "content": "A."}'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        process_func({
            "input": text,
            "OPENAI_API_TOKEN": "dummy"
        })

        # Verify the prompt contains the spec-required text
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        prompt = messages[0]["content"]

        assert "Transform the content of the following text" in prompt
        assert "as a sequence of question and answer related to it" in prompt
        assert '{"role": "user", "content": <question>}' in prompt
        assert '{"role": "assistant", "content": <answer>}' in prompt
        assert f"Text:\n{text}" in prompt
