import sys
sys.path.append("packages/rag/clean")
import clean

def test_clean_empty():
    res = clean.clean({})
    assert res["output"] == ""

def test_clean_removes_number_lines():
    text = """Some text here
6
More text here"""
    res = clean.clean({"input": text})
    assert "6" not in res["output"]
    assert "Some text here" in res["output"]
    assert "More text here" in res["output"]

def test_clean_removes_strange_characters():
    text = "This has ââ strange characters"
    res = clean.clean({"input": text})
    assert "ââ" not in res["output"]
    assert "This has" in res["output"]
    assert "strange characters" in res["output"]

def test_clean_keeps_paragraph_separation():
    text = """Line 1

Line 2


Line 3"""
    res = clean.clean({"input": text})
    lines = res["output"].split('\n')
    # Should have 3 lines of text plus 2 empty lines (one between each paragraph)
    assert len(lines) == 5
    assert lines[0] == "Line 1"
    assert lines[1] == ""
    assert lines[2] == "Line 2"
    assert lines[3] == ""
    assert lines[4] == "Line 3"

def test_clean_normalizes_quotes():
    text = 'He said "hello" and \'goodbye\''
    res = clean.clean({"input": text})
    assert '"' in res["output"]
    assert "'" in res["output"]

def test_clean_converts_corrupted_bullets():
    """Test that corrupted bullet points (â from PDF) are converted to dashes"""
    text = """Introduction
â First item
â Second item
Normal text"""
    res = clean.clean({"input": text})
    # Should convert â to - at start of line
    assert "- First item" in res["output"]
    assert "- Second item" in res["output"]
    # Should not contain â anymore
    assert "â" not in res["output"]

def test_clean_removes_toc_lines():
    """Test that table of contents lines (ending in ...<number>) are removed"""
    text = """Chapter Title
Introduction....................1
Methods and Materials...........15
Results.........................42
Body text here
Line with 100 inside should stay"""
    res = clean.clean({"input": text})
    # Should remove TOC lines
    assert "Introduction" not in res["output"]
    assert "Methods and Materials" not in res["output"]
    assert "Results" not in res["output"]
    # Should keep other lines
    assert "Chapter Title" in res["output"]
    assert "Body text here" in res["output"]
    assert "Line with 100 inside should stay" in res["output"]

def test_clean_removes_figure_lines():
    """Test that lines containing 'Figure <number>' are removed"""
    text = """This is a paragraph.
Figure 1
Another paragraph here.
See Figure 12 for details.
figure 5 should also be removed
More text here."""
    res = clean.clean({"input": text})
    # Should remove Figure lines
    assert "Figure 1" not in res["output"]
    assert "Figure 12" not in res["output"]
    assert "figure 5" not in res["output"]
    # Should keep other lines
    assert "This is a paragraph." in res["output"]
    assert "Another paragraph here." in res["output"]
    assert "More text here." in res["output"]
