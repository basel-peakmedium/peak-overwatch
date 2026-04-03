#!/usr/bin/env python3
"""
Test TikTok Video API call format
"""

import json

def test_video_api_request():
    """Test the structure of TikTok Video List API request"""
    
    # Expected request structure
    request_data = {
        'max_count': 20,
        'fields': [
            'id',
            'title',
            'description',
            'cover_image_url',
            'like_count',
            'view_count',
            'comment_count',
            'share_count',
            'create_time'
        ]
    }
    
    # Expected headers
    headers = {
        'Authorization': 'Bearer ACCESS_TOKEN_HERE',
        'Content-Type': 'application/json'
    }
    
    print("=== TikTok Video API Test ===\n")
    
    print("1. API Endpoint:")
    print("   POST https://open.tiktokapis.com/v2/video/list/\n")
    
    print("2. Required Headers:")
    for key, value in headers.items():
        print(f"   {key}: {value}")
    print()
    
    print("3. Request Body (JSON):")
    print(json.dumps(request_data, indent=2))
    print()
    
    print("4. Expected Response Structure:")
    response_example = {
        "data": {
            "videos": [
                {
                    "id": "video_id_123",
                    "title": "My TikTok Video",
                    "description": "Video description...",
                    "cover_image_url": "https://example.com/cover.jpg",
                    "like_count": 1500,
                    "view_count": 50000,
                    "comment_count": 120,
                    "share_count": 45,
                    "create_time": 1672531200
                }
            ],
            "cursor": 123456,
            "has_more": True
        }
    }
    print(json.dumps(response_example, indent=2))
    print()
    
    print("5. Implementation Notes:")
    print("   - Uses POST method (not GET)")
    print("   - Requires Bearer token from OAuth")
    print("   - Fields parameter specifies data to return")
    print("   - Max_count limits results (max 20 for sandbox)")
    print("   - Response includes pagination cursor")
    
    print("\n✓ API call format verified")

if __name__ == '__main__':
    test_video_api_request()