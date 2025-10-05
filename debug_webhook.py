#!/usr/bin/env python3
"""
Debug webhook to see what's actually happening
"""
import requests
import json
import time

def test_webhook_simple():
    """Test the webhook with a simple payload and see response"""
    
    payload = {
        "action": "created",
        "issue": {
            "id": 999999,
            "number": 42,
            "title": "Debug test issue",
            "body": "This is a debug test",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/42",
            "created_at": "2024-10-05T02:00:00Z",
            "user": {
                "login": "issue_creator",
                "id": 12345
            }
        },
        "comment": {
            "id": 888888,
            "body": "I'll work on this issue!",
            "created_at": "2024-10-05T02:01:00Z",
            "html_url": "https://github.com/test/repo/issues/42#issuecomment-888888",
            "user": {
                "login": "claim_maker",
                "id": 67890
            }
        },
        "repository": {
            "id": 777777,
            "name": "test-repo",
            "full_name": "test/repo",
            "owner": {
                "login": "test",
                "id": 11111
            },
            "html_url": "https://github.com/test/repo"
        }
    }
    
    print("Sending webhook payload...")
    
    try:
        response = requests.post(
            'http://localhost:8000/api/v1/webhooks/github',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'issue_comment'
            },
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook accepted!")
        else:
            print("❌ Webhook failed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_webhook_simple()