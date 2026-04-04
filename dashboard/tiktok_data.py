"""
TikTok Data Fetching for Peak Overwatch
Video list and user data display
"""

import requests
from flask import Blueprint, jsonify, session, render_template_string

data_bp = Blueprint('tiktok_data', __name__, url_prefix='/tiktok')

@data_bp.route('/videos')
def get_videos():
    """Fetch and display user's TikTok videos"""
    
    # Check authentication
    if 'tiktok_access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    access_token = session['tiktok_access_token']
    
    # Fetch videos from TikTok API
    videos = fetch_user_videos(access_token)
    if 'error' in videos:
        return jsonify(videos), 400
    
    # Get user info from session
    user_info = session.get('tiktok_user', {})
    
    # Render video display page
    return render_video_page(user_info, videos.get('data', {}).get('videos', []))

def fetch_user_videos(access_token, max_results=20):
    """Fetch user's videos from TikTok API"""
    
    video_url = "https://open.tiktokapis.com/v2/video/list/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Request body for video list
    data = {
        'max_count': max_results,
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
    
    try:
        response = requests.post(video_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            'error': 'Failed to fetch videos',
            'error_description': str(e)
        }

def render_video_page(user_info, videos):
    """Render HTML page showing user profile and videos"""
    
    # Format video data for display
    formatted_videos = []
    for video in videos[:10]:  # Show first 10 videos
        formatted_videos.append({
            'id': video.get('id', ''),
            'title': video.get('title', 'Untitled'),
            'description': video.get('description', '')[:100] + '...' if video.get('description') else 'No description',
            'cover_image': video.get('cover_image_url', ''),
            'likes': format_number(video.get('like_count', 0)),
            'views': format_number(video.get('view_count', 0)),
            'comments': format_number(video.get('comment_count', 0)),
            'shares': format_number(video.get('share_count', 0)),
            'created': format_timestamp(video.get('create_time', 0))
        })
    
    # Calculate totals
    total_videos = len(videos)
    total_views = sum(video.get('view_count', 0) for video in videos)
    total_likes = sum(video.get('like_count', 0) for video in videos)

    # Use render_template_string — NO f-string here, so Jinja2 syntax is safe
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TikTok Videos • Peak Overwatch</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            body { background: #0f172a; color: #f1f5f9; padding: 20px; }
            .video-card {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 1rem;
                transition: transform 0.2s;
            }
            .video-card:hover { transform: translateY(-2px); }
            .video-stats {
                display: flex;
                gap: 1rem;
                margin-top: 0.5rem;
                font-size: 0.9rem;
                color: #94a3b8;
            }
            .stat-item { display: flex; align-items: center; gap: 0.25rem; }
            .profile-header {
                background: linear-gradient(135deg, #1e293b, #334155);
                border-radius: 12px;
                padding: 2rem;
                margin-bottom: 2rem;
            }
            .metric-badge {
                background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-weight: 600;
            }
            .cover-image {
                width: 100%;
                height: 180px;
                object-fit: cover;
                border-radius: 8px;
                margin-bottom: 1rem;
            }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg mb-4">
            <div class="container-fluid">
                <a class="navbar-brand" href="/dashboard" style="font-weight: 700; background: linear-gradient(135deg, #00F2EA, #FF0050); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    <i class="bi bi-binoculars-fill me-2"></i>Peak Overwatch
                </a>
                <div class="d-flex align-items-center">
                    <a href="/dashboard" class="btn btn-sm btn-outline-light me-3">
                        <i class="bi bi-speedometer2 me-1"></i>Dashboard
                    </a>
                    <a href="/tiktok/logout" class="btn btn-sm btn-outline-danger">
                        <i class="bi bi-box-arrow-right me-1"></i>Logout
                    </a>
                </div>
            </div>
        </nav>
        
        <div class="container-fluid">
            <!-- Profile Header -->
            <div class="profile-header">
                <div class="row align-items-center">
                    <div class="col-auto">
                        {% if user_info.get('avatar_url') %}
                        <img src="{{ user_info.get('avatar_url') }}" alt="Avatar" width="80" height="80" class="rounded-circle">
                        {% else %}
                        <div class="rounded-circle bg-dark d-flex align-items-center justify-content-center" style="width: 80px; height: 80px;">
                            <i class="bi bi-person-fill" style="font-size: 2rem;"></i>
                        </div>
                        {% endif %}
                    </div>
                    <div class="col">
                        <h2 class="mb-1">{{ user_info.get('display_name', 'TikTok User') }}</h2>
                        <p class="text-secondary mb-0">@{{ user_info.get('open_id', 'user')[:15] }}...</p>
                    </div>
                    <div class="col-auto">
                        <div class="d-flex gap-3">
                            <div class="text-center">
                                <div class="metric-badge">{{ total_videos }}</div>
                                <div class="small mt-1">Videos</div>
                            </div>
                            <div class="text-center">
                                <div class="metric-badge">{{ total_views_fmt }}</div>
                                <div class="small mt-1">Total Views</div>
                            </div>
                            <div class="text-center">
                                <div class="metric-badge">{{ total_likes_fmt }}</div>
                                <div class="small mt-1">Total Likes</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Video Grid -->
            <h3 class="mb-3">Your TikTok Videos</h3>
            
            {% if formatted_videos %}
            <div class="row">
                {% for video in formatted_videos %}
                <div class="col-md-6 col-lg-4">
                    <div class="video-card">
                        {% if video.cover_image %}
                        <img src="{{ video.cover_image }}" alt="Cover" class="cover-image">
                        {% else %}
                        <div class="cover-image bg-dark d-flex align-items-center justify-content-center">
                            <i class="bi bi-play-circle" style="font-size: 3rem; color: #666;"></i>
                        </div>
                        {% endif %}
                        
                        <h5 class="mb-2">{{ video.title }}</h5>
                        <p class="text-secondary small mb-2">{{ video.description }}</p>
                        
                        <div class="video-stats">
                            <div class="stat-item">
                                <i class="bi bi-eye-fill"></i>
                                <span>{{ video.views }}</span>
                            </div>
                            <div class="stat-item">
                                <i class="bi bi-heart-fill text-danger"></i>
                                <span>{{ video.likes }}</span>
                            </div>
                            <div class="stat-item">
                                <i class="bi bi-chat-fill"></i>
                                <span>{{ video.comments }}</span>
                            </div>
                            <div class="stat-item">
                                <i class="bi bi-share-fill"></i>
                                <span>{{ video.shares }}</span>
                            </div>
                        </div>
                        
                        <div class="mt-2 text-secondary small">
                            <i class="bi bi-clock me-1"></i>{{ video.created }}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div class="text-center mt-4">
                <p class="text-secondary">
                    Showing {{ formatted_videos|length }} of {{ total_videos }} videos • 
                    <a href="/dashboard" class="text-decoration-none">Back to Dashboard</a>
                </p>
            </div>
            
            {% else %}
            <div class="text-center py-5">
                <div class="mb-3">
                    <i class="bi bi-camera-video-off" style="font-size: 3rem; color: #666;"></i>
                </div>
                <h4>No videos found</h4>
                <p class="text-secondary">Connect your TikTok account or create some videos to see them here.</p>
                <a href="/dashboard" class="btn btn-outline-light">Back to Dashboard</a>
            </div>
            {% endif %}
        </div>
        
        <script>
            // Add interactivity
            document.querySelectorAll('.video-card').forEach(function(card) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', function() {
                    // In production, this would open video details
                    console.log('Video clicked:', this.querySelector('h5').textContent);
                });
            });
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(
        html_template,
        user_info=user_info,
        formatted_videos=formatted_videos,
        total_videos=total_videos,
        total_views_fmt=format_number(total_views),
        total_likes_fmt=format_number(total_likes)
    )

def format_number(num):
    """Format large numbers with K/M suffixes"""
    if num >= 1000000:
        return f'{num/1000000:.1f}M'
    elif num >= 1000:
        return f'{num/1000:.1f}K'
    return str(num)

def format_timestamp(timestamp):
    """Format TikTok timestamp to readable date"""
    from datetime import datetime
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%b %d, %Y')
    except:
        return 'Unknown date'

@data_bp.route('/stats')
def get_stats():
    """Get video statistics summary"""
    if 'tiktok_access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    access_token = session['tiktok_access_token']
    videos = fetch_user_videos(access_token)
    
    if 'error' in videos:
        return jsonify(videos), 400
    
    video_list = videos.get('data', {}).get('videos', [])
    
    stats = {
        'total_videos': len(video_list),
        'total_views': sum(v.get('view_count', 0) for v in video_list),
        'total_likes': sum(v.get('like_count', 0) for v in video_list),
        'total_comments': sum(v.get('comment_count', 0) for v in video_list),
        'total_shares': sum(v.get('share_count', 0) for v in video_list),
        'average_views': sum(v.get('view_count', 0) for v in video_list) / max(len(video_list), 1),
        'average_likes': sum(v.get('like_count', 0) for v in video_list) / max(len(video_list), 1),
    }
    
    return jsonify(stats)
