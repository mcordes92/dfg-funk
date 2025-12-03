# Python Funk System - Test API Endpoints

## Base URL
http://localhost:8000

## Authentication Endpoints

### Verify Funk Key
```bash
curl -X POST "http://localhost:8000/api/auth/verify" \
  -H "Content-Type: application/json" \
  -d "{\"funk_key\": \"YOUR_FUNK_KEY_HERE\"}"
```

### Get User Info
```bash
curl "http://localhost:8000/api/user/info/YOUR_FUNK_KEY_HERE"
```

## Channel Endpoints

### List All Channels
```bash
curl "http://localhost:8000/api/channels/list"
```

### Get User Channels
```bash
curl "http://localhost:8000/api/channels/YOUR_FUNK_KEY_HERE"
```

## Admin Endpoints

### Create User
```bash
curl -X POST "http://localhost:8000/api/admin/users" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"funk_key\": \"abc123def456\", \"allowed_channels\": [41, 42, 43]}"
```

### List All Users
```bash
curl "http://localhost:8000/api/admin/users"
```

### Get Specific User
```bash
curl "http://localhost:8000/api/admin/users/testuser"
```

### Update User
```bash
curl -X PUT "http://localhost:8000/api/admin/users/testuser" \
  -H "Content-Type: application/json" \
  -d "{\"allowed_channels\": [41, 42, 43, 44, 45], \"is_active\": true}"
```

### Delete User
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/testuser"
```

## Statistics Endpoints

### Active Users
```bash
curl "http://localhost:8000/api/stats/active-users"
```

### Traffic Statistics
```bash
curl "http://localhost:8000/api/stats/traffic"

# Filter by username
curl "http://localhost:8000/api/stats/traffic?username=testuser"
```

### Channel Usage
```bash
curl "http://localhost:8000/api/stats/channel-usage"
```

### Connection Logs
```bash
curl "http://localhost:8000/api/logs/connections?limit=50"

# Filter by username
curl "http://localhost:8000/api/logs/connections?username=testuser&limit=50"
```

## Internal Endpoints (for UDP server)

### Check Channel Permission
```bash
curl "http://localhost:8000/api/internal/check-permission/YOUR_FUNK_KEY/41"
```

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to test all endpoints directly in your browser!
