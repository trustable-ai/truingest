import sys
sys.path.insert(0, "packages/rag/chunk")
from chunk import chunk as chunk_func

def test_chunk_empty():
    res = chunk_func({})
    assert res["output"] == []

def test_chunk_single_paragraph():
    """Test chunking with single paragraph (no empty lines)"""
    text = "This is a single paragraph with no empty lines."
    res = chunk_func({"input": text})
    assert res["num_chunks"] == 1
    assert len(res["output"]) == 1
    assert res["output"][0] == text

def test_chunk_multiple_paragraphs():
    """Test chunking with multiple paragraphs separated by empty lines"""
    text = """First paragraph here.

Second paragraph here.

Third paragraph here."""
    res = chunk_func({"input": text})

    # Should create 3 chunks (one per paragraph)
    assert res["num_chunks"] == 3
    assert len(res["output"]) == 3
    assert res["output"][0] == "First paragraph here."
    assert res["output"][1] == "Second paragraph here."
    assert res["output"][2] == "Third paragraph here."

def test_chunk_multiline_paragraphs():
    """Test chunking with multi-line paragraphs"""
    text = """First line of paragraph 1.
Second line of paragraph 1.

First line of paragraph 2.
Second line of paragraph 2.

Paragraph 3."""
    res = chunk_func({"input": text})

    # Should create 3 chunks
    assert res["num_chunks"] == 3
    assert len(res["output"]) == 3
    assert res["output"][0] == "First line of paragraph 1.\nSecond line of paragraph 1."
    assert res["output"][1] == "First line of paragraph 2.\nSecond line of paragraph 2."
    assert res["output"][2] == "Paragraph 3."

def test_chunk_multiple_empty_lines():
    """Test that multiple consecutive empty lines are treated as one separator"""
    text = """Paragraph 1.


Paragraph 2.



Paragraph 3."""
    res = chunk_func({"input": text})

    # Should create 3 chunks regardless of multiple empty lines
    assert res["num_chunks"] == 3
    assert res["output"][0] == "Paragraph 1."
    assert res["output"][1] == "Paragraph 2."
    assert res["output"][2] == "Paragraph 3."

def test_chunk_no_trailing_empty_line():
    """Test that text without trailing empty line is handled correctly"""
    text = """Para 1.

Para 2."""
    res = chunk_func({"input": text})
    assert res["num_chunks"] == 2
    assert res["output"][0] == "Para 1."
    assert res["output"][1] == "Para 2."
