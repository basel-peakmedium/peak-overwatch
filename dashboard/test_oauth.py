#!/usr/bin/env python3
"""
Test TikTok OAuth configuration
"""

from urllib.parse import urlencode

# Configuration from tiktok_auth.py
TIKTOK_CLIENT_KEY = "aw83kyu0wl317cm7"
TIKTOK_REDIRECT_URI = "https://app.peakoverwatch.com/auth/callback"
TIKTOK_AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"

SCOPES = [
    "user.info.basic",
    "video.list",
    "video.insights"
]

def generate_auth_url():
    """Generate the TikTok OAuth authorization URL"""
    params = {
        'client_key': TIKTOK_CLIENT_KEY,
        'response_type': 'code',
        'scope': ','.join(SCOPES),
        'redirect_uri': TIKTOK_REDIRECT_URI,
        'state': 'test_state_123'  # In production, use random state
    }
    
    auth_url = f"{TIKTOK_AUTHORIZE_URL}?{urlencode(params)}"
    return auth_url

if __name__ == '__main__':
    print("=== TikTok OAuth Configuration Test ===\n")
    
    print("1. Client Configuration:")
    print(f"   Client Key: {TIKTOK_CLIENT_KEY}")
    print(f"   Redirect URI: {TIKTOK_REDIRECT_URI}")
    print(f"   Scopes: {', '.join(SCOPES)}")
    
    print("\n2. Generated Authorization URL:")
    auth_url = generate_auth_url()
    print(f"   {auth_url}")
    
    print("\n3. Expected Flow:")
    print("   User clicks: /tiktok/login")
    print("   Redirects to: TikTok OAuth page")
    print("   After auth, TikTok redirects to: /auth/callback?code=...&state=...")
    print("   App exchanges code for token")
    print("   User redirected to: /dashboard")
    
    print("\n4. Sandbox Testing Notes:")
    print("   - Use TikTok Developer Portal sandbox environment")
    print("   - Test with test TikTok account")
    print("   - Verify callback URL matches exactly")
    print("   - Check token exchange works")
    
    print("\n✓ Configuration ready for sandbox testing")