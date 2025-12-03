import sqlite3
import hashlib
import secrets
import os
from datetime import datetime
from contextlib import contextmanager


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "funkserver.db")
        self.db_path = db_path
        
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    funk_key TEXT UNIQUE NOT NULL,
                    allowed_channels TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT
                )
            """)
            
            # Channels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Connection logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER,
                    action TEXT,
                    ip_address TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (channel_id) REFERENCES channels(id)
                )
            """)
            
            # Traffic statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER,
                    packets_sent INTEGER DEFAULT 0,
                    bytes_sent INTEGER DEFAULT 0,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (channel_id) REFERENCES channels(id)
                )
            """)
            
            # Initialize default channels if empty
            cursor.execute("SELECT COUNT(*) FROM channels")
            if cursor.fetchone()[0] == 0:
                # Add public channels (41-43)
                cursor.execute("INSERT INTO channels (id, name, description) VALUES (41, 'Allgemein 1', 'Öffentlicher Kanal')")
                cursor.execute("INSERT INTO channels (id, name, description) VALUES (42, 'Allgemein 2', 'Öffentlicher Kanal')")
                cursor.execute("INSERT INTO channels (id, name, description) VALUES (43, 'Allgemein 3', 'Öffentlicher Kanal')")
                # Add restricted channels (51-69)
                for i in range(51, 70):
                    cursor.execute(f"INSERT INTO channels (id, name, description) VALUES ({i}, 'Kanal {i}', 'Privater Kanal')")
            
            # Create default admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                admin_key = secrets.token_hex(16)
                cursor.execute("""
                    INSERT INTO users (username, funk_key, allowed_channels) 
                    VALUES ('admin', ?, '41,42,43,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69')
                """, (admin_key,))
                print(f"🔑 Admin Funk-Schlüssel erstellt: {admin_key}")
                print("   Bitte speichern Sie diesen Schlüssel!")
    
    # User Management
    def create_user(self, username, funk_key=None, allowed_channels="41"):
        """Create new user with funk key"""
        if funk_key is None:
            funk_key = secrets.token_hex(16)
        
        # Convert list to comma-separated string if needed
        if isinstance(allowed_channels, list):
            allowed_channels = ','.join(map(str, allowed_channels))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, funk_key, allowed_channels)
                VALUES (?, ?, ?)
            """, (username, funk_key, allowed_channels))
            return cursor.lastrowid
    
    def verify_user(self, funk_key):
        """Verify user by funk key and return as dict"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, allowed_channels, is_active 
                FROM users WHERE funk_key = ? AND is_active = 1
            """, (funk_key,))
            row = cursor.fetchone()
            if row:
                # Convert allowed_channels string to list of integers
                allowed_channels = [int(ch.strip()) for ch in row['allowed_channels'].split(',') if ch.strip()]
                return {
                    'id': row['id'],
                    'username': row['username'],
                    'allowed_channels': allowed_channels,
                    'is_active': bool(row['is_active'])
                }
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()
    
    def get_user(self, username):
        """Get user by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                allowed_channels = [int(ch.strip()) for ch in row['allowed_channels'].split(',') if ch.strip()]
                return dict(row, allowed_channels=allowed_channels)
            return None
    
    def get_all_users(self):
        """Get all users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            users = []
            for row in rows:
                user = dict(row)
                user['allowed_channels'] = [int(ch.strip()) for ch in row['allowed_channels'].split(',') if ch.strip()]
                users.append(user)
            return users
    
    def update_user(self, username, allowed_channels=None, is_active=None):
        """Update user details by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if allowed_channels is not None:
                if isinstance(allowed_channels, list):
                    allowed_channels = ','.join(map(str, allowed_channels))
                updates.append("allowed_channels = ?")
                params.append(allowed_channels)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(1 if is_active else 0)
            
            if updates:
                params.append(username)
                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE username = ?", params)
                return cursor.rowcount > 0
            return False
    
    def delete_user(self, username):
        """Delete user by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            return cursor.rowcount > 0
    
    def update_last_seen(self, user_id):
        """Update user's last seen timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", 
                         (datetime.now().isoformat(), user_id))
    
    # Channel Management
    def get_all_channels(self):
        """Get all channels"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM channels WHERE is_active = 1 ORDER BY id")
            return cursor.fetchall()
    
    def get_channel(self, channel_id):
        """Get channel by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
            return cursor.fetchone()
    
    def update_channel(self, channel_id, name=None, description=None, is_active=None):
        """Update channel details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            
            if updates:
                params.append(channel_id)
                cursor.execute(f"UPDATE channels SET {', '.join(updates)} WHERE id = ?", params)
    
    # Logging
    def log_connection(self, user_id, channel_id, action, ip_address):
        """Log connection event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO connection_logs (user_id, channel_id, action, ip_address)
                VALUES (?, ?, ?, ?)
            """, (user_id, channel_id, action, ip_address))
    
    def log_traffic(self, user_id, channel_id, packets_sent, bytes_sent):
        """Log traffic statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traffic_stats (user_id, channel_id, packets_sent, bytes_sent)
                VALUES (?, ?, ?, ?)
            """, (user_id, channel_id, packets_sent, bytes_sent))
    
    # Statistics
    def get_connection_logs(self, username=None, limit=100):
        """Get recent connection logs, optionally filtered by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute("""
                    SELECT cl.*, u.username, c.name as channel_name
                    FROM connection_logs cl
                    LEFT JOIN users u ON cl.user_id = u.id
                    LEFT JOIN channels c ON cl.channel_id = c.id
                    WHERE u.username = ?
                    ORDER BY cl.timestamp DESC
                    LIMIT ?
                """, (username, limit))
            else:
                cursor.execute("""
                    SELECT cl.*, u.username, c.name as channel_name
                    FROM connection_logs cl
                    LEFT JOIN users u ON cl.user_id = u.id
                    LEFT JOIN channels c ON cl.channel_id = c.id
                    ORDER BY cl.timestamp DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_traffic_stats(self, username=None):
        """Get traffic statistics, optionally filtered by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute("""
                    SELECT ts.*, u.username, c.name as channel_name
                    FROM traffic_stats ts
                    LEFT JOIN users u ON ts.user_id = u.id
                    LEFT JOIN channels c ON ts.channel_id = c.id
                    WHERE u.username = ?
                    ORDER BY ts.timestamp DESC
                """, (username,))
            else:
                cursor.execute("""
                    SELECT ts.*, u.username, c.name as channel_name
                    FROM traffic_stats ts
                    LEFT JOIN users u ON ts.user_id = u.id
                    LEFT JOIN channels c ON ts.channel_id = c.id
                    ORDER BY ts.timestamp DESC
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_users(self):
        """Get currently active users (seen in last 5 minutes)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.*, 
                       (SELECT channel_id FROM connection_logs 
                        WHERE user_id = u.id AND action = 'connect' 
                        ORDER BY timestamp DESC LIMIT 1) as current_channel
                FROM users u
                WHERE u.last_seen >= datetime('now', '-5 minutes')
                AND u.is_active = 1
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_channel_usage(self):
        """Get channel usage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id,
                    c.name,
                    COUNT(DISTINCT cl.user_id) as unique_users,
                    COUNT(*) as total_connections
                FROM channels c
                LEFT JOIN connection_logs cl ON c.id = cl.channel_id
                WHERE cl.timestamp >= datetime('now', '-24 hours')
                GROUP BY c.id, c.name
                ORDER BY unique_users DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def record_traffic(self, bytes_in, bytes_out):
        """Record incoming and outgoing traffic"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traffic_stats (user_id, channel_id, packets_sent, bytes_sent)
                VALUES (0, 0, ?, ?)
            """, (bytes_out, bytes_in))
    
    def get_traffic_summary(self):
        """Get traffic summary for 24h, 7d, and 30d"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 24 hours
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(bytes_sent), 0) as bytes_in,
                    COALESCE(SUM(packets_sent), 0) as bytes_out
                FROM traffic_stats
                WHERE timestamp >= datetime('now', '-24 hours')
            """)
            stats_24h = dict(cursor.fetchone())
            
            # 7 days
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(bytes_sent), 0) as bytes_in,
                    COALESCE(SUM(packets_sent), 0) as bytes_out
                FROM traffic_stats
                WHERE timestamp >= datetime('now', '-7 days')
            """)
            stats_7d = dict(cursor.fetchone())
            
            # 30 days
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(bytes_sent), 0) as bytes_in,
                    COALESCE(SUM(packets_sent), 0) as bytes_out
                FROM traffic_stats
                WHERE timestamp >= datetime('now', '-30 days')
            """)
            stats_30d = dict(cursor.fetchone())
            
            return {
                "24h": stats_24h,
                "7d": stats_7d,
                "30d": stats_30d
            }
