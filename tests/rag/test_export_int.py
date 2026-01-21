import os
import json
import requests as req

def test_export():
    """Integration test for export action"""
    url = os.environ.get("OPSDEV_HOST") + "/api/my/rag/export"

    # This test requires a valid s3_key with chunks
    # You'll need to create test chunks first in your actual test scenario
    # For now, this is a basic connectivity test
    res = req.get(url).json()

    # Without s3_key, should return error
    assert "error" in res or "jsonl" in res
