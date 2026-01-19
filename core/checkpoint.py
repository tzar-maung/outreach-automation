"""
Session Recovery & Checkpoint System

Ensures no work is lost if the bot crashes:
- Auto-save progress every N targets
- Resume from where you left off
- Track processed vs pending targets
- Handle graceful and unexpected shutdowns

Usage:
    checkpoint = CheckpointManager("session_001", platform="instagram")
    checkpoint.set_targets(targets)
    
    for target in checkpoint.get_pending():
        checkpoint.mark_processing(target)
        # ... process ...
        checkpoint.mark_completed(target, result)
"""
import json
import signal
import atexit
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class TargetStatus(Enum):
    """Status of a target."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TargetState:
    """State of a single target."""
    url: str
    status: str = TargetStatus.PENDING.value
    attempts: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass 
class SessionState:
    """Complete session state."""
    session_id: str
    platform: str
    created_at: str
    updated_at: str
    status: str = "running"  # running, paused, completed, crashed
    
    # Progress
    total_targets: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    
    # Current position
    current_index: int = 0
    current_target: Optional[str] = None
    
    # All targets
    targets: Dict[str, Dict] = field(default_factory=dict)
    
    # Statistics
    session_stats: Dict[str, int] = field(default_factory=dict)
    
    # Notes
    notes: List[str] = field(default_factory=list)


class CheckpointManager:
    """
    Manages session checkpoints for crash recovery.
    
    Features:
    - Auto-save at configurable intervals
    - Resume from last checkpoint
    - Graceful shutdown handling
    - Progress tracking
    """
    
    def __init__(self, session_id: str = None, 
                 platform: str = "instagram",
                 checkpoint_dir: str = "checkpoints",
                 auto_save_interval: int = 30):
        """
        Initialize checkpoint manager.
        
        Args:
            session_id: Unique session ID (auto-generated if None)
            platform: Target platform
            checkpoint_dir: Directory for checkpoint files
            auto_save_interval: Auto-save interval in seconds
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        
        self.session_id = session_id
        self.platform = platform
        self.checkpoint_file = self.checkpoint_dir / f"{session_id}.json"
        
        # Initialize or load state
        self.state: Optional[SessionState] = None
        self._load_or_create()
        
        # Auto-save thread
        self.auto_save_interval = auto_save_interval
        self._stop_auto_save = threading.Event()
        self._auto_save_thread: Optional[threading.Thread] = None
        
        # Start auto-save
        if auto_save_interval > 0:
            self._start_auto_save()
        
        # Register shutdown handlers
        self._register_shutdown_handlers()
    
    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------
    
    def _load_or_create(self):
        """Load existing checkpoint or create new one."""
        if self.checkpoint_file.exists():
            self._load()
            print(f"📂 Loaded existing session: {self.session_id}")
            print(f"   Progress: {self.state.processed}/{self.state.total_targets}")
        else:
            self._create_new()
            print(f"📝 Created new session: {self.session_id}")
    
    def _create_new(self):
        """Create a new session state."""
        now = datetime.now().isoformat()
        self.state = SessionState(
            session_id=self.session_id,
            platform=self.platform,
            created_at=now,
            updated_at=now,
        )
    
    def _load(self):
        """Load state from checkpoint file."""
        try:
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
            
            self.state = SessionState(**data)
            self.state.status = "resumed"
            
        except Exception as e:
            print(f"⚠️ Could not load checkpoint: {e}")
            self._create_new()
    
    # --------------------------------------------------
    # Target Management
    # --------------------------------------------------
    
    def set_targets(self, targets: List[str]):
        """
        Set the list of targets for this session.
        
        Only adds new targets that aren't already tracked.
        
        Args:
            targets: List of target URLs
        """
        for url in targets:
            if url not in self.state.targets:
                self.state.targets[url] = asdict(TargetState(url=url))
        
        self.state.total_targets = len(self.state.targets)
        self.save()
    
    def get_pending(self) -> List[str]:
        """Get list of pending (not yet processed) targets."""
        pending = []
        
        for url, data in self.state.targets.items():
            if data["status"] in [TargetStatus.PENDING.value, TargetStatus.PROCESSING.value]:
                pending.append(url)
        
        return pending
    
    def get_failed(self) -> List[str]:
        """Get list of failed targets."""
        return [
            url for url, data in self.state.targets.items()
            if data["status"] == TargetStatus.FAILED.value
        ]
    
    def get_completed(self) -> List[str]:
        """Get list of completed targets."""
        return [
            url for url, data in self.state.targets.items()
            if data["status"] == TargetStatus.COMPLETED.value
        ]
    
    # --------------------------------------------------
    # Status Updates
    # --------------------------------------------------
    
    def mark_processing(self, url: str):
        """Mark a target as currently being processed."""
        if url not in self.state.targets:
            self.state.targets[url] = asdict(TargetState(url=url))
        
        self.state.targets[url]["status"] = TargetStatus.PROCESSING.value
        self.state.targets[url]["started_at"] = datetime.now().isoformat()
        self.state.targets[url]["attempts"] += 1
        
        self.state.current_target = url
        self._update_timestamp()
    
    def mark_completed(self, url: str, result: Dict = None):
        """Mark a target as successfully completed."""
        if url not in self.state.targets:
            return
        
        self.state.targets[url]["status"] = TargetStatus.COMPLETED.value
        self.state.targets[url]["completed_at"] = datetime.now().isoformat()
        self.state.targets[url]["result"] = result
        
        self.state.processed += 1
        self.state.successful += 1
        self.state.current_index += 1
        self.state.current_target = None
        
        self._update_timestamp()
        self.save()
    
    def mark_failed(self, url: str, error: str = None):
        """Mark a target as failed."""
        if url not in self.state.targets:
            return
        
        self.state.targets[url]["status"] = TargetStatus.FAILED.value
        self.state.targets[url]["completed_at"] = datetime.now().isoformat()
        self.state.targets[url]["error"] = error
        
        self.state.processed += 1
        self.state.failed += 1
        self.state.current_index += 1
        self.state.current_target = None
        
        self._update_timestamp()
        self.save()
    
    def mark_skipped(self, url: str, reason: str = None):
        """Mark a target as skipped."""
        if url not in self.state.targets:
            return
        
        self.state.targets[url]["status"] = TargetStatus.SKIPPED.value
        self.state.targets[url]["completed_at"] = datetime.now().isoformat()
        self.state.targets[url]["error"] = reason
        
        self.state.processed += 1
        self.state.skipped += 1
        self.state.current_index += 1
        self.state.current_target = None
        
        self._update_timestamp()
    
    def is_processed(self, url: str) -> bool:
        """Check if a target has been processed."""
        if url not in self.state.targets:
            return False
        
        status = self.state.targets[url]["status"]
        return status in [
            TargetStatus.COMPLETED.value,
            TargetStatus.FAILED.value,
            TargetStatus.SKIPPED.value,
        ]
    
    # --------------------------------------------------
    # Session Control
    # --------------------------------------------------
    
    def pause(self, note: str = None):
        """Pause the session."""
        self.state.status = "paused"
        if note:
            self.add_note(f"Paused: {note}")
        self.save()
    
    def resume(self):
        """Resume a paused session."""
        self.state.status = "running"
        self.add_note("Resumed")
        self.save()
    
    def complete(self, note: str = None):
        """Mark session as completed."""
        self.state.status = "completed"
        if note:
            self.add_note(note)
        self._stop_auto_save.set()
        self.save()
    
    def add_note(self, note: str):
        """Add a timestamped note to the session."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.state.notes.append(f"[{timestamp}] {note}")
    
    def update_stats(self, key: str, value: int = 1):
        """Update session statistics."""
        if key not in self.state.session_stats:
            self.state.session_stats[key] = 0
        self.state.session_stats[key] += value
    
    # --------------------------------------------------
    # Persistence
    # --------------------------------------------------
    
    def save(self):
        """Save checkpoint to file."""
        self._update_timestamp()
        
        try:
            data = asdict(self.state)
            
            with open(self.checkpoint_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
        except Exception as e:
            print(f"⚠️ Failed to save checkpoint: {e}")
    
    def _update_timestamp(self):
        """Update the last modified timestamp."""
        self.state.updated_at = datetime.now().isoformat()
    
    # --------------------------------------------------
    # Auto-Save
    # --------------------------------------------------
    
    def _start_auto_save(self):
        """Start auto-save background thread."""
        self._auto_save_thread = threading.Thread(
            target=self._auto_save_loop,
            daemon=True
        )
        self._auto_save_thread.start()
    
    def _auto_save_loop(self):
        """Background auto-save loop."""
        while not self._stop_auto_save.wait(timeout=self.auto_save_interval):
            self.save()
    
    # --------------------------------------------------
    # Shutdown Handling
    # --------------------------------------------------
    
    def _register_shutdown_handlers(self):
        """Register handlers for graceful shutdown."""
        atexit.register(self._on_shutdown)
        
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            pass  # May fail on some platforms
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n⚠️ Shutdown signal received...")
        self._on_shutdown()
        raise KeyboardInterrupt()
    
    def _on_shutdown(self):
        """Handle shutdown - save final state."""
        self._stop_auto_save.set()
        
        if self.state.status == "running":
            self.state.status = "interrupted"
        
        self.save()
        print(f"✅ Session saved: {self.checkpoint_file}")
    
    # --------------------------------------------------
    # Progress Information
    # --------------------------------------------------
    
    def get_progress(self) -> Dict:
        """Get current progress information."""
        total = self.state.total_targets
        processed = self.state.processed
        
        return {
            "session_id": self.session_id,
            "status": self.state.status,
            "total": total,
            "processed": processed,
            "successful": self.state.successful,
            "failed": self.state.failed,
            "skipped": self.state.skipped,
            "remaining": total - processed,
            "progress_percent": (processed / total * 100) if total > 0 else 0,
            "current_target": self.state.current_target,
        }
    
    def print_progress(self):
        """Print formatted progress."""
        p = self.get_progress()
        
        print(f"\n{'='*50}")
        print(f"📊 Session: {p['session_id']}")
        print(f"{'='*50}")
        print(f"Status: {p['status']}")
        print(f"Progress: {p['processed']}/{p['total']} ({p['progress_percent']:.1f}%)")
        print(f"  ✅ Successful: {p['successful']}")
        print(f"  ❌ Failed: {p['failed']}")
        print(f"  ⏭️  Skipped: {p['skipped']}")
        print(f"  📋 Remaining: {p['remaining']}")
        
        if p['current_target']:
            print(f"Current: {p['current_target']}")
        
        print(f"{'='*50}\n")
    
    def print_progress_bar(self):
        """Print a simple progress bar."""
        p = self.get_progress()
        
        total = p['total']
        done = p['processed']
        
        if total == 0:
            return
        
        bar_width = 40
        filled = int(bar_width * done / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(f"\r[{bar}] {done}/{total} ({p['progress_percent']:.1f}%)", end="", flush=True)


# --------------------------------------------------
# Session Finder
# --------------------------------------------------

class SessionFinder:
    """Find and list existing sessions."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
    
    def list_sessions(self) -> List[Dict]:
        """List all available sessions."""
        sessions = []
        
        if not self.checkpoint_dir.exists():
            return sessions
        
        for file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                
                sessions.append({
                    "session_id": data.get("session_id"),
                    "platform": data.get("platform"),
                    "status": data.get("status"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "total": data.get("total_targets", 0),
                    "processed": data.get("processed", 0),
                    "file": str(file),
                })
                
            except Exception:
                continue
        
        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return sessions
    
    def find_resumable(self, platform: str = None) -> List[Dict]:
        """Find sessions that can be resumed."""
        resumable = []
        
        for session in self.list_sessions():
            if session["status"] in ["running", "interrupted", "paused"]:
                if platform is None or session["platform"] == platform:
                    remaining = session["total"] - session["processed"]
                    if remaining > 0:
                        resumable.append(session)
        
        return resumable
    
    def print_sessions(self):
        """Print all sessions in a table."""
        sessions = self.list_sessions()
        
        if not sessions:
            print("No sessions found.")
            return
        
        print(f"\n{'='*80}")
        print("📁 Available Sessions")
        print(f"{'='*80}")
        print(f"{'ID':<30} {'Platform':<12} {'Status':<12} {'Progress':<15}")
        print(f"{'-'*80}")
        
        for s in sessions:
            progress = f"{s['processed']}/{s['total']}"
            status_icon = {
                "running": "🟢",
                "completed": "✅",
                "interrupted": "🟡",
                "paused": "⏸️",
                "crashed": "🔴",
            }.get(s["status"], "❓")
            
            print(f"{s['session_id']:<30} {s['platform']:<12} "
                  f"{status_icon} {s['status']:<10} {progress:<15}")
        
        print(f"{'='*80}\n")


# --------------------------------------------------
# Context Manager
# --------------------------------------------------

class CheckpointContext:
    """
    Context manager for easy checkpoint usage.
    
    Usage:
        with CheckpointContext("my_session", "instagram") as checkpoint:
            checkpoint.set_targets(targets)
            for target in checkpoint.get_pending():
                # process...
                checkpoint.mark_completed(target)
    """
    
    def __init__(self, session_id: str = None, platform: str = "instagram", **kwargs):
        self.session_id = session_id
        self.platform = platform
        self.kwargs = kwargs
        self.checkpoint: Optional[CheckpointManager] = None
    
    def __enter__(self) -> CheckpointManager:
        self.checkpoint = CheckpointManager(
            session_id=self.session_id,
            platform=self.platform,
            **self.kwargs
        )
        return self.checkpoint
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.checkpoint.state.status = "crashed"
            self.checkpoint.add_note(f"Crashed: {exc_type.__name__}: {exc_val}")
        else:
            if self.checkpoint.state.processed >= self.checkpoint.state.total_targets:
                self.checkpoint.complete("All targets processed")
        
        self.checkpoint.save()
        return False  # Don't suppress exceptions
