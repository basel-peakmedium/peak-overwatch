"""
TikTok OAuth Integration for Peak Overwatch
Sandbox environment setup
"""

import os
import json
import requests
from flask import Blueprint, redirect, request, session, jsonify, url_for
from urllib.parse import urlencode

# TikTok OAuth Configuration
TIKTOK_CLIENT_KEY = "aw83kyu0wl317cm7"
TIKTOK_CLIENT_SECRET = "q90wtmbdxdnxMlOYsHhwcmxLgTUNVkby"
TIKTOK_REDIRECT_URI = "https://app.peakoverwatch.com/auth/callback"
TIKTOK_AUTH_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"

# Scopes for TikTok API
SCOPES = [
    "user.info.basic",  # Get basic user info
    "video.list",       # List user's videos
    "video.insights"    # Get video insights
]

# Create Blueprint
tiktok_bp = Blueprint('tiktok', __name__)

@tiktok_bp.route('/tiktok/login')
def tiktok_login():
    """Redirect user to TikTok OAuth authorization page"""
    
    # Generate state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    
    # Build authorization URL
    params = {
        'client_key': TIKTOK_CLIENT_KEY,
        'response_type': 'code',
        'scope': ','.join(SCOPES),
        'redirect_uri': TIKTOK_REDIRECT_URI,
        'state': state,
    }
    
    auth_url = f"{TIKTOK_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(auth_url)

@tiktok_bp.route('/auth/callback')
def auth_callback():
    """Handle TikTok OAuth callback"""
    
    # Check for errors
    error = request.args.get('error')
    if error:
        return jsonify({
            'error': 'OAuth failed',
            'error_description': request.args.get('error_description', 'Unknown error')
        }), 400
    
    # Verify state for CSRF protection
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        return jsonify({'error': 'Invalid state parameter'}), 400
    
    # Get authorization code
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No authorization code received'}), 400
    
    # Exchange code for access token
    token_data = exchange_code_for_token(code)
    if 'error' in token_data:
        return jsonify(token_data), 400
    
    # Store tokens in session
    session['tiktok_access_token'] = token_data.get('access_token')
    session['tiktok_refresh_token'] = token_data.get('refresh_token')
    session['tiktok_expires_in'] = token_data.get('expires_in')
    
    # Get user info
    user_info = get_user_info(token_data['access_token'])
    if user_info:
        session['tiktok_user'] = user_info
    
    # Redirect to dashboard or user profile
    return redirect('/dashboard')

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    
    token_url = TIKTOK_AUTH_URL
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache'
    }
    
    data = {
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': TIKTOK_REDIRECT_URI
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            'error': 'Token exchange failed',
            'error_description': str(e)
        }

def get_user_info(access_token):
    """Get basic user information from TikTok API"""
    
    user_url = "https://open.tiktokapis.com/v2/user/info/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'fields': 'open_id,union_id,avatar_url,display_name'
    }
    
    try:
        response = requests.get(user_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('data', {}).get('user', {})
    except requests.exceptions.RequestException:
        return None

def refresh_access_token(refresh_token):
    """Refresh expired access token"""
    
    token_url = TIKTOK_AUTH_URL
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache'
    }
    
    data = {
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            'error': 'Token refresh failed',
            'error_description': str(e)
        }

@tiktok_bp.route('/tiktok/logout')
def logout():
    """Clear TikTok session data"""
    session.pop('tiktok_access_token', None)
    session.pop('tiktok_refresh_token', None)
    session.pop('tiktok_user', None)
    session.pop('oauth_state', None)
    return redirect('/')

@tiktok_bp.route('/tiktok/user')
def get_current_user():
    """Get current logged in user info"""
    if 'tiktok_user' in session:
        return jsonify(session['tiktok_user'])
    return jsonify({'error': 'Not authenticated'}), 401