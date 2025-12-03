"""
FastAPI REST API Server for Funk System Administration and Authentication
"""
from fastapi import FastAPI, HTTPException, Depends, status, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import uvicorn
import os
import secrets
import hashlib
import shutil
import json
from pathlib import Path
from dotenv import load_dotenv
from database import Database

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Funk System API",
    description="REST API for funk key authentication and channel management",
    version="1.0.0"
)

# CORS middleware for web admin interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web interface
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

# Database instance
db = Database()

# Session management
admin_sessions = {}  # {token: {"username": str, "expires": datetime}}
ADMIN_USERNAME = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "admin123")

# Pydantic models for request/response
class AdminLogin(BaseModel):
    username: str
    password: str

class FunkKeyVerify(BaseModel):
    funk_key: str = Field(..., min_length=8, description="Funk key to verify")

class UserInfo(BaseModel):
    username: str
    allowed_channels: List[int]
    is_active: bool

class ChannelInfo(BaseModel):
    channel_id: int
    name: str

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    funk_key: str = Field(..., min_length=8, description="Unique funk key")
    allowed_channels: List[int] = Field(default_factory=list, description="Channel IDs 41-72")

class UpdateUserRequest(BaseModel):
    allowed_channels: Optional[List[int]] = None
    is_active: Optional[bool] = None

class ConnectionLog(BaseModel):
    username: str
    timestamp: str
    action: str
    channel_id: Optional[int]

class TrafficStats(BaseModel):
    username: str
    channel_id: int
    packets_sent: int
    packets_received: int
    bytes_sent: int
    bytes_received: int

class VersionInfo(BaseModel):
    version: str
    release_date: str
    download_url: str
    file_size: int
    changelog: Optional[str] = None

# Web Interface
@app.get("/")
async def serve_admin_interface():
    """Serve the admin web interface (will redirect to login if not authenticated)"""
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "service": "Funk System API",
        "version": "1.0.0",
        "message": "Web interface not found. Access API docs at /docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/login")
async def serve_login_page():
    """Serve the login page"""
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    login_path = os.path.join(web_dir, "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    raise HTTPException(status_code=404, detail="Login page not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

# Admin authentication
def verify_admin_token(authorization: Optional[str] = Header(None)):
    """Verify admin session token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    session = admin_sessions.get(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    if datetime.now() > session["expires"]:
        del admin_sessions[token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return session

@app.post("/api/admin/login")
async def admin_login(credentials: AdminLogin):
    """Admin login endpoint"""
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        # Generate session token
        token = secrets.token_urlsafe(32)
        admin_sessions[token] = {
            "username": credentials.username,
            "expires": datetime.now() + timedelta(hours=24)
        }
        return {
            "success": True,
            "token": token,
            "expires_in": 86400  # 24 hours in seconds
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/admin/logout")
async def admin_logout(session: dict = Depends(verify_admin_token), authorization: str = Header(None)):
    """Admin logout endpoint"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        if token in admin_sessions:
            del admin_sessions[token]
    return {"success": True, "message": "Logged out"}

@app.get("/api/admin/verify")
async def verify_admin_session(session: dict = Depends(verify_admin_token)):
    """Verify current admin session"""
    return {"authenticated": True, "username": session["username"]}

# Authentication endpoints
@app.post("/api/auth/verify", status_code=200)
async def verify_funk_key(request: FunkKeyVerify):
    """
    Verify a funk key and return user information
    """
    user = db.verify_user(request.funk_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid funk key or user is not active"
        )
    
    return {
        "valid": True,
        "username": user["username"],
        "allowed_channels": user["allowed_channels"],
        "is_active": user["is_active"]
    }

@app.get("/api/user/info/{funk_key}", response_model=UserInfo)
async def get_user_info(funk_key: str):
    """
    Get user information by funk key
    """
    user = db.verify_user(funk_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(
        username=user["username"],
        allowed_channels=user["allowed_channels"],
        is_active=user["is_active"]
    )

# Channel management endpoints
@app.get("/api/channels/list")
async def list_channels():
    """
    List all available channels (41-43 public, 51-69 restricted)
    """
    channels = []
    # Public channels
    for channel_id in range(41, 44):
        channels.append({
            "channel_id": channel_id,
            "name": f"Kanal {channel_id} (Allgemein)",
            "type": "public"
        })
    # Restricted channels
    for channel_id in range(51, 70):
        channels.append({
            "channel_id": channel_id,
            "name": f"Kanal {channel_id}",
            "type": "restricted"
        })
    return {"channels": channels}

@app.get("/api/channels/{funk_key}")
async def get_user_channels(funk_key: str):
    """
    Get allowed channels for a specific user
    """
    user = db.verify_user(funk_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    channels = []
    for channel_id in user["allowed_channels"]:
        channels.append({
            "channel_id": channel_id,
            "name": f"Kanal {channel_id}"
        })
    
    return {
        "username": user["username"],
        "channels": channels
    }

# User management endpoints (Admin)
@app.post("/api/admin/users", status_code=201)
async def create_user(request: CreateUserRequest, session: dict = Depends(verify_admin_token)):
    """
    Create a new user with funk key
    """
    try:
        user_id = db.create_user(
            username=request.username,
            funk_key=request.funk_key,
            allowed_channels=request.allowed_channels
        )
        
        return {
            "user_id": user_id,
            "username": request.username,
            "funk_key": request.funk_key,
            "allowed_channels": request.allowed_channels,
            "message": "User created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/api/admin/users")
async def list_users(session: dict = Depends(verify_admin_token)):
    """
    List all users
    """
    users = db.get_all_users()
    return {"users": users, "count": len(users)}

@app.get("/api/admin/users/{username}")
async def get_user(username: str, session: dict = Depends(verify_admin_token)):
    """
    Get specific user by username
    """
    user = db.get_user(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@app.put("/api/admin/users/{username}")
async def update_user(username: str, request: UpdateUserRequest, session: dict = Depends(verify_admin_token)):
    """
    Update user settings
    """
    success = db.update_user(
        username=username,
        allowed_channels=request.allowed_channels,
        is_active=request.is_active
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User updated successfully", "username": username}

@app.delete("/api/admin/users/{username}")
async def delete_user(username: str, session: dict = Depends(verify_admin_token)):
    """
    Delete a user
    """
    success = db.delete_user(username)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully", "username": username}

# Statistics and logging endpoints
@app.get("/api/stats/active-users")
async def get_active_users(session: dict = Depends(verify_admin_token)):
    """
    Get currently active users
    """
    active_users = db.get_active_users()
    return {
        "active_users": active_users,
        "count": len(active_users)
    }

@app.get("/api/stats/traffic")
async def get_traffic_stats(session: dict = Depends(verify_admin_token)):
    """
    Get traffic statistics summary (24h, 7d, 30d)
    """
    stats = db.get_traffic_summary()
    
    def format_bytes(b):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if b < 1024.0:
                return f"{b:.2f} {unit}"
            b /= 1024.0
        return f"{b:.2f} TB"
    
    # Format for display
    formatted = {}
    for period, data in stats.items():
        formatted[period] = {
            "bytes_in": data["bytes_in"],
            "bytes_out": data["bytes_out"],
            "bytes_in_formatted": format_bytes(data["bytes_in"]),
            "bytes_out_formatted": format_bytes(data["bytes_out"]),
            "total_formatted": format_bytes(data["bytes_in"] + data["bytes_out"])
        }
    
    return {
        "traffic": formatted
    }

@app.get("/api/stats/channel-usage")
async def get_channel_usage(session: dict = Depends(verify_admin_token)):
    """
    Get channel usage statistics
    """
    usage = db.get_channel_usage()
    return {
        "channel_usage": usage,
        "count": len(usage)
    }

@app.get("/api/logs/connections")
async def get_connection_logs(username: Optional[str] = None, limit: int = 100, session: dict = Depends(verify_admin_token)):
    """
    Get connection logs
    """
    logs = db.get_connection_logs(username, limit)
    return {
        "logs": logs,
        "count": len(logs)
    }

# Channel permission check endpoint (for UDP server)
@app.get("/api/internal/check-permission/{funk_key}/{channel_id}")
async def check_channel_permission(funk_key: str, channel_id: int):
    """
    Check if user has permission for specific channel
    Internal endpoint for UDP server
    """
    user = db.verify_user(funk_key)
    
    if not user:
        return {
            "allowed": False,
            "reason": "Invalid funk key or inactive user"
        }
    
    if channel_id not in user["allowed_channels"]:
        return {
            "allowed": False,
            "reason": f"User {user['username']} not authorized for channel {channel_id}"
        }
    
    return {
        "allowed": True,
        "username": user["username"]
    }

def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Start the FastAPI server
    """
    print(f"Starting Funk System API Server on {host}:{port}")
    print(f"")
    print(f"╔═══════════════════════════════════════════════════╗")
    print(f"║       🎙️  FUNK SYSTEM ADMIN DASHBOARD  🎙️        ║")
    print(f"╠═══════════════════════════════════════════════════╣")
    print(f"║  Admin-Interface: http://localhost:{port}/            ║")
    print(f"║  API Docs:        http://localhost:{port}/docs        ║")
    print(f"╠═══════════════════════════════════════════════════╣")
    print(f"║  🔐 LOGIN CREDENTIALS:                            ║")
    print(f"║     Username: {ADMIN_USERNAME:<35} ║")
    print(f"║     Password: {ADMIN_PASSWORD:<35} ║")
    print(f"╠═══════════════════════════════════════════════════╣")
    print(f"║  ⚠️  WICHTIG: Credentials in .env Datei ändern!   ║")
    print(f"║     Siehe .env.example für Details               ║")
    print(f"╚═══════════════════════════════════════════════════╝")
    print(f"")
    
    # Create updates directory if it doesn't exist
    updates_dir = Path(os.path.dirname(__file__)) / "updates"
    updates_dir.mkdir(exist_ok=True)
    print(f"📦 Updates-Verzeichnis: {updates_dir}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

# ========================================
# UPDATE SYSTEM ENDPOINTS
# ========================================

def get_updates_dir():
    """Get the updates directory path"""
    return Path(os.path.dirname(__file__)) / "updates"

def get_version_file():
    """Get the version info file path"""
    return get_updates_dir() / "version.json"

def load_version_info():
    """Load current version information"""
    version_file = get_version_file()
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_version_info(version_data):
    """Save version information"""
    version_file = get_version_file()
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)

@app.get("/api/version")
async def get_current_version():
    """Get current client version info (public endpoint)"""
    version_info = load_version_info()
    if not version_info:
        raise HTTPException(status_code=404, detail="No version available")
    return version_info

@app.get("/api/updates/download")
async def download_client():
    """Download the latest client EXE (public endpoint)"""
    version_info = load_version_info()
    if not version_info:
        raise HTTPException(status_code=404, detail="No version available")
    
    exe_path = get_updates_dir() / "DFG-Funk-Client.exe"
    if not exe_path.exists():
        raise HTTPException(status_code=404, detail="Client EXE not found")
    
    return FileResponse(
        path=str(exe_path),
        filename="DFG-Funk-Client.exe",
        media_type="application/octet-stream"
    )

@app.post("/api/admin/updates/upload")
async def upload_client(
    file: UploadFile = File(...),
    version: str = Header(...),
    changelog: Optional[str] = Header(None),
    admin_token: str = Depends(verify_admin_token)
):
    """Upload a new client EXE version (admin only)"""
    
    # Validate file
    if not file.filename.endswith('.exe'):
        raise HTTPException(status_code=400, detail="Only .exe files allowed")
    
    # Save uploaded file
    updates_dir = get_updates_dir()
    exe_path = updates_dir / "DFG-Funk-Client.exe"
    
    try:
        with open(exe_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        file_size = exe_path.stat().st_size
        
        # Save version info
        version_data = {
            "version": version,
            "release_date": datetime.now().isoformat(),
            "download_url": "/api/updates/download",
            "file_size": file_size,
            "changelog": changelog or "Keine Änderungen angegeben"
        }
        save_version_info(version_data)
        
        return {
            "success": True,
            "message": f"Version {version} erfolgreich hochgeladen",
            "file_size": file_size,
            "version_info": version_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/admin/updates/info")
async def get_update_info(admin_token: str = Depends(verify_admin_token)):
    """Get current update information (admin only)"""
    version_info = load_version_info()
    
    exe_path = get_updates_dir() / "DFG-Funk-Client.exe"
    exe_exists = exe_path.exists()
    exe_size = exe_path.stat().st_size if exe_exists else 0
    
    return {
        "version_info": version_info,
        "exe_exists": exe_exists,
        "exe_size": exe_size,
        "updates_dir": str(get_updates_dir())
    }

if __name__ == "__main__":
    start_api_server()
