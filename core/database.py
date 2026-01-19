"""
Database Storage - SQLite Backend for Persistent Data

Stores:
- Targets and their status
- Action history (follows, likes, views)
- Rate limit tracking
- Session statistics

Usage:
    db = Database("outreach.db")
    db.add_target("https://instagram.com/user", "instagram")
    db.log_action("user", "instagram", "follow")
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Target:
    """Represents a target profile."""
    id: int
    url: str
    platform: str
    username: Optional[str]
    status: str  # pending, completed, failed, skipped
    followers: Optional[int]
    following: Optional[int]
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_action_at: Optional[datetime]
    notes: Optional[str]


@dataclass
class ActionLog:
    """Represents a logged action."""
    id: int
    target_id: Optional[int]
    username: str
    platform: str
    action_type: str  # view, follow, like, dm, unfollow
    status: str  # success, failed
    created_at: datetime
    details: Optional[str]


class Database:
    """
    SQLite database for outreach bot data.
    
    Tables:
    - targets: Profile URLs to process
    - action_logs: History of all actions taken
    - rate_limits: Daily/hourly action counters
    - sessions: Session metadata
    """
    
    def __init__(self, db_path: str = "outreach.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
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
    
    def _init_database(self):
        """Create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Targets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    username TEXT,
                    status TEXT DEFAULT 'pending',
                    followers INTEGER,
                    following INTEGER,
                    posts_count INTEGER,
                    bio TEXT,
                    is_private INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_action_at TIMESTAMP,
                    notes TEXT,
                    UNIQUE(url)
                )
            """)
            
            # Action logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER,
                    username TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    FOREIGN KEY (target_id) REFERENCES targets(id)
                )
            """)
            
            # Rate limits table (daily counters)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    UNIQUE(platform, action_type, date)
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    targets_processed INTEGER DEFAULT 0,
                    actions_taken INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_targets_status 
                ON targets(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_targets_platform 
                ON targets(platform)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_logs_created 
                ON action_logs(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_logs_username 
                ON action_logs(username, platform)
            """)
    
    # --------------------------------------------------
    # Target Management
    # --------------------------------------------------
    
    def add_target(self, url: str, platform: str, 
                   username: str = None) -> int:
        """
        Add a new target to the database.
        
        Args:
            url: Target URL
            platform: Platform name (instagram, tiktok)
            username: Optional username
        
        Returns:
            Target ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO targets (url, platform, username)
                    VALUES (?, ?, ?)
                """, (url, platform, username))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Already exists, return existing ID
                cursor.execute(
                    "SELECT id FROM targets WHERE url = ?", (url,)
                )
                row = cursor.fetchone()
                return row["id"] if row else 0
    
    def add_targets_bulk(self, targets: List[Dict]) -> int:
        """
        Add multiple targets at once.
        
        Args:
            targets: List of dicts with url, platform, username
        
        Returns:
            Number of targets added
        """
        added = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for target in targets:
                try:
                    cursor.execute("""
                        INSERT INTO targets (url, platform, username)
                        VALUES (?, ?, ?)
                    """, (
                        target.get("url"),
                        target.get("platform"),
                        target.get("username"),
                    ))
                    added += 1
                except sqlite3.IntegrityError:
                    continue  # Skip duplicates
        return added
    
    def get_target(self, target_id: int) -> Optional[Dict]:
        """Get a target by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM targets WHERE id = ?", (target_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_target_by_url(self, url: str) -> Optional[Dict]:
        """Get a target by URL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM targets WHERE url = ?", (url,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_pending_targets(self, platform: str = None, 
                           limit: int = 50) -> List[Dict]:
        """
        Get targets that haven't been processed yet.
        
        Args:
            platform: Filter by platform
            limit: Maximum number to return
        
        Returns:
            List of target dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if platform:
                cursor.execute("""
                    SELECT * FROM targets 
                    WHERE status = 'pending' AND platform = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (platform, limit))
            else:
                cursor.execute("""
                    SELECT * FROM targets 
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_target(self, target_id: int, **kwargs) -> bool:
        """
        Update a target's fields.
        
        Args:
            target_id: Target ID
            **kwargs: Fields to update
        
        Returns:
            True if updated
        """
        if not kwargs:
            return False
        
        # Build SET clause
        set_parts = []
        values = []
        for key, value in kwargs.items():
            set_parts.append(f"{key} = ?")
            values.append(value)
        
        values.append(target_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE targets 
                SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def mark_target_completed(self, target_id: int, 
                              profile_info: Dict = None) -> bool:
        """Mark a target as completed and store profile info."""
        updates = {"status": "completed", "last_action_at": datetime.now()}
        
        if profile_info:
            updates.update({
                "followers": profile_info.get("followers"),
                "following": profile_info.get("following"),
                "posts_count": profile_info.get("posts"),
                "bio": profile_info.get("bio"),
                "is_private": 1 if profile_info.get("is_private") else 0,
            })
        
        return self.update_target(target_id, **updates)
    
    def mark_target_failed(self, target_id: int, error: str = None) -> bool:
        """Mark a target as failed."""
        return self.update_target(
            target_id, 
            status="failed",
            notes=error,
        )
    
    # --------------------------------------------------
    # Action Logging
    # --------------------------------------------------
    
    def log_action(self, username: str, platform: str, 
                   action_type: str, status: str = "success",
                   target_id: int = None, details: str = None) -> int:
        """
        Log an action taken.
        
        Args:
            username: Target username
            platform: Platform name
            action_type: Type of action (view, follow, like, dm)
            status: success or failed
            target_id: Optional target ID
            details: Optional details
        
        Returns:
            Action log ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO action_logs 
                (target_id, username, platform, action_type, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (target_id, username, platform, action_type, status, details))
            
            # Also update rate limit counter
            self._increment_rate_limit(cursor, platform, action_type)
            
            return cursor.lastrowid
    
    def get_action_history(self, username: str = None, 
                           platform: str = None,
                           action_type: str = None,
                           limit: int = 100) -> List[Dict]:
        """Get action history with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM action_logs WHERE 1=1"
            params = []
            
            if username:
                query += " AND username = ?"
                params.append(username)
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def has_interacted_with(self, username: str, platform: str,
                            action_type: str = None) -> bool:
        """Check if we've already interacted with a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if action_type:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM action_logs
                    WHERE username = ? AND platform = ? AND action_type = ?
                """, (username, platform, action_type))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM action_logs
                    WHERE username = ? AND platform = ?
                """, (username, platform))
            
            row = cursor.fetchone()
            return row["count"] > 0
    
    # --------------------------------------------------
    # Rate Limiting
    # --------------------------------------------------
    
    def _increment_rate_limit(self, cursor, platform: str, 
                              action_type: str) -> None:
        """Increment the daily rate limit counter."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO rate_limits (platform, action_type, date, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(platform, action_type, date) 
            DO UPDATE SET count = count + 1
        """, (platform, action_type, today))
    
    def get_daily_count(self, platform: str, action_type: str,
                        date: str = None) -> int:
        """
        Get the count of actions for a specific day.
        
        Args:
            platform: Platform name
            action_type: Type of action
            date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            Action count
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT count FROM rate_limits
                WHERE platform = ? AND action_type = ? AND date = ?
            """, (platform, action_type, date))
            
            row = cursor.fetchone()
            return row["count"] if row else 0
    
    def get_hourly_count(self, platform: str, action_type: str) -> int:
        """Get the count of actions in the last hour."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM action_logs
                WHERE platform = ? AND action_type = ? 
                AND created_at >= ?
            """, (platform, action_type, one_hour_ago))
            
            row = cursor.fetchone()
            return row["count"]
    
    def can_perform_action(self, platform: str, action_type: str,
                           daily_limit: int, hourly_limit: int = None) -> bool:
        """
        Check if an action can be performed within rate limits.
        
        Args:
            platform: Platform name
            action_type: Type of action
            daily_limit: Maximum daily actions
            hourly_limit: Maximum hourly actions (optional)
        
        Returns:
            True if action is allowed
        """
        daily_count = self.get_daily_count(platform, action_type)
        if daily_count >= daily_limit:
            return False
        
        if hourly_limit:
            hourly_count = self.get_hourly_count(platform, action_type)
            if hourly_count >= hourly_limit:
                return False
        
        return True
    
    # --------------------------------------------------
    # Session Management
    # --------------------------------------------------
    
    def start_session(self, platform: str) -> int:
        """Start a new session and return session ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (platform)
                VALUES (?)
            """, (platform,))
            return cursor.lastrowid
    
    def end_session(self, session_id: int, 
                    targets_processed: int = 0,
                    actions_taken: int = 0,
                    errors: int = 0,
                    notes: str = None) -> bool:
        """End a session with statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET ended_at = CURRENT_TIMESTAMP,
                    targets_processed = ?,
                    actions_taken = ?,
                    errors = ?,
                    notes = ?
                WHERE id = ?
            """, (targets_processed, actions_taken, errors, notes, session_id))
            return cursor.rowcount > 0
    
    def get_session_stats(self, session_id: int) -> Optional[Dict]:
        """Get statistics for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------
    
    def get_statistics(self, platform: str = None) -> Dict:
        """Get overall statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Target counts
            if platform:
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM targets WHERE platform = ?
                    GROUP BY status
                """, (platform,))
            else:
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM targets
                    GROUP BY status
                """)
            
            stats["targets"] = {row["status"]: row["count"] 
                               for row in cursor.fetchall()}
            
            # Action counts (today)
            today = datetime.now().strftime("%Y-%m-%d")
            if platform:
                cursor.execute("""
                    SELECT action_type, count 
                    FROM rate_limits 
                    WHERE platform = ? AND date = ?
                """, (platform, today))
            else:
                cursor.execute("""
                    SELECT action_type, SUM(count) as count 
                    FROM rate_limits WHERE date = ?
                    GROUP BY action_type
                """, (today,))
            
            stats["actions_today"] = {row["action_type"]: row["count"] 
                                      for row in cursor.fetchall()}
            
            # Total actions
            cursor.execute("SELECT COUNT(*) as count FROM action_logs")
            stats["total_actions"] = cursor.fetchone()["count"]
            
            return stats
    
    # --------------------------------------------------
    # Import/Export
    # --------------------------------------------------
    
    def import_from_csv(self, filepath: str, platform: str) -> int:
        """
        Import targets from a CSV file.
        
        Args:
            filepath: Path to CSV file
            platform: Platform for all imported targets
        
        Returns:
            Number of targets imported
        """
        import csv
        
        targets = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url", "").strip()
                if url:
                    targets.append({
                        "url": url,
                        "platform": platform,
                        "username": row.get("username"),
                    })
        
        return self.add_targets_bulk(targets)
    
    def export_to_csv(self, filepath: str, status: str = None) -> int:
        """
        Export targets to a CSV file.
        
        Args:
            filepath: Output file path
            status: Filter by status (optional)
        
        Returns:
            Number of targets exported
        """
        import csv
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    "SELECT * FROM targets WHERE status = ?", (status,)
                )
            else:
                cursor.execute("SELECT * FROM targets")
            
            rows = cursor.fetchall()
        
        if not rows:
            return 0
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        return len(rows)
