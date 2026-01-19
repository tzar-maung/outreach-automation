"""
Scheduler - Run Bot at Specific Times

Features:
- Schedule runs at specific times
- Random time variation (anti-detection)
- Daily/weekly schedules
- Pause and resume
- Safe shutdown

Usage:
    scheduler = Scheduler()
    scheduler.add_daily_task("09:00", run_instagram_session)
    scheduler.add_daily_task("14:00", run_tiktok_session)
    scheduler.start()
"""
import time
import random
import signal
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    name: str
    callback: Callable
    schedule_time: str  # HH:MM format
    days: List[str]  # ['monday', 'tuesday', ...] or ['daily']
    variation_minutes: int = 30  # Random variation
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    
    def calculate_next_run(self) -> datetime:
        """Calculate the next run time with random variation."""
        now = datetime.now()
        hour, minute = map(int, self.schedule_time.split(":"))
        
        # Add random variation
        variation = random.randint(-self.variation_minutes, self.variation_minutes)
        scheduled_minute = minute + variation
        
        # Handle minute overflow
        extra_hours = scheduled_minute // 60
        scheduled_minute = scheduled_minute % 60
        scheduled_hour = (hour + extra_hours) % 24
        
        # Create today's scheduled time
        scheduled = now.replace(
            hour=scheduled_hour,
            minute=scheduled_minute,
            second=0,
            microsecond=0,
        )
        
        # If already passed today, schedule for next valid day
        if scheduled <= now:
            scheduled += timedelta(days=1)
        
        # Check if day is valid
        if 'daily' not in self.days:
            while scheduled.strftime('%A').lower() not in [d.lower() for d in self.days]:
                scheduled += timedelta(days=1)
        
        self.next_run = scheduled
        return scheduled


class Scheduler:
    """
    Task scheduler with human-like timing.
    
    Features:
    - Multiple scheduled tasks
    - Random time variation
    - Day-of-week filtering
    - Graceful shutdown
    - State persistence
    """
    
    def __init__(self, state_file: str = None):
        """
        Initialize scheduler.
        
        Args:
            state_file: Optional file to persist state
        """
        self.tasks: Dict[str, ScheduledTask] = {}
        self.state_file = Path(state_file) if state_file else None
        self.running = False
        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Load state if exists
        if self.state_file and self.state_file.exists():
            self._load_state()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    # --------------------------------------------------
    # Task Management
    # --------------------------------------------------
    
    def add_task(self, name: str, callback: Callable,
                 schedule_time: str, days: List[str] = None,
                 variation_minutes: int = 30) -> ScheduledTask:
        """
        Add a scheduled task.
        
        Args:
            name: Unique task name
            callback: Function to call
            schedule_time: Time in HH:MM format
            days: Days to run (e.g., ['monday', 'wednesday'])
            variation_minutes: Random variation range
        
        Returns:
            Created task
        """
        if days is None:
            days = ['daily']
        
        task = ScheduledTask(
            name=name,
            callback=callback,
            schedule_time=schedule_time,
            days=days,
            variation_minutes=variation_minutes,
        )
        task.calculate_next_run()
        
        self.tasks[name] = task
        self._save_state()
        
        return task
    
    def add_daily_task(self, schedule_time: str, callback: Callable,
                       name: str = None, variation_minutes: int = 30) -> ScheduledTask:
        """Convenience method to add a daily task."""
        if name is None:
            name = f"daily_{schedule_time.replace(':', '')}_{id(callback)}"
        
        return self.add_task(
            name=name,
            callback=callback,
            schedule_time=schedule_time,
            days=['daily'],
            variation_minutes=variation_minutes,
        )
    
    def add_weekday_task(self, schedule_time: str, callback: Callable,
                         name: str = None) -> ScheduledTask:
        """Add a task that runs Monday-Friday."""
        if name is None:
            name = f"weekday_{schedule_time.replace(':', '')}_{id(callback)}"
        
        return self.add_task(
            name=name,
            callback=callback,
            schedule_time=schedule_time,
            days=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
        )
    
    def remove_task(self, name: str) -> bool:
        """Remove a task by name."""
        if name in self.tasks:
            del self.tasks[name]
            self._save_state()
            return True
        return False
    
    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self._save_state()
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            self._save_state()
            return True
        return False
    
    # --------------------------------------------------
    # Scheduler Control
    # --------------------------------------------------
    
    def start(self, blocking: bool = True):
        """
        Start the scheduler.
        
        Args:
            blocking: If True, run in current thread (blocks)
        """
        self.running = True
        self._shutdown_event.clear()
        
        if blocking:
            self._run_loop()
        else:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
    
    def stop(self):
        """Stop the scheduler gracefully."""
        print("\n⏹️ Stopping scheduler...")
        self.running = False
        self._shutdown_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self._save_state()
        print("✅ Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        print(f"🚀 Scheduler started with {len(self.tasks)} tasks")
        self._print_upcoming_tasks()
        
        while self.running:
            self._check_and_run_tasks()
            
            # Sleep for 1 minute (check tasks every minute)
            if self._shutdown_event.wait(timeout=60):
                break
    
    def _check_and_run_tasks(self):
        """Check all tasks and run if due."""
        now = datetime.now()
        
        for name, task in self.tasks.items():
            if not task.enabled:
                continue
            
            if task.next_run and now >= task.next_run:
                print(f"\n⏰ Running task: {name}")
                self._execute_task(task)
    
    def _execute_task(self, task: ScheduledTask):
        """Execute a task and update its state."""
        try:
            task.callback()
            task.last_run = datetime.now()
            task.run_count += 1
            print(f"✅ Task completed: {task.name}")
        except Exception as e:
            print(f"❌ Task failed: {task.name} - {e}")
        finally:
            task.calculate_next_run()
            self._save_state()
            print(f"📅 Next run: {task.next_run.strftime('%Y-%m-%d %H:%M')}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.stop()
    
    # --------------------------------------------------
    # State Persistence
    # --------------------------------------------------
    
    def _save_state(self):
        """Save scheduler state to file."""
        if not self.state_file:
            return
        
        state = {
            "tasks": {}
        }
        
        for name, task in self.tasks.items():
            state["tasks"][name] = {
                "schedule_time": task.schedule_time,
                "days": task.days,
                "variation_minutes": task.variation_minutes,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
            }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Load scheduler state from file."""
        if not self.state_file or not self.state_file.exists():
            return
        
        with open(self.state_file, "r") as f:
            state = json.load(f)
        
        # Restore task metadata (callbacks must be re-added)
        for name, task_data in state.get("tasks", {}).items():
            if name in self.tasks:
                task = self.tasks[name]
                task.last_run = (
                    datetime.fromisoformat(task_data["last_run"])
                    if task_data.get("last_run") else None
                )
                task.run_count = task_data.get("run_count", 0)
                task.enabled = task_data.get("enabled", True)
    
    # --------------------------------------------------
    # Information
    # --------------------------------------------------
    
    def get_upcoming_tasks(self, count: int = 10) -> List[Dict]:
        """Get list of upcoming task runs."""
        upcoming = []
        
        for name, task in self.tasks.items():
            if task.enabled and task.next_run:
                upcoming.append({
                    "name": name,
                    "next_run": task.next_run,
                    "schedule_time": task.schedule_time,
                    "days": task.days,
                })
        
        # Sort by next run time
        upcoming.sort(key=lambda x: x["next_run"])
        return upcoming[:count]
    
    def _print_upcoming_tasks(self):
        """Print upcoming tasks."""
        upcoming = self.get_upcoming_tasks(5)
        
        if not upcoming:
            print("📭 No tasks scheduled")
            return
        
        print("\n📋 Upcoming tasks:")
        for task in upcoming:
            print(f"  • {task['name']}: {task['next_run'].strftime('%Y-%m-%d %H:%M')}")
        print()
    
    def get_task_status(self) -> Dict:
        """Get status of all tasks."""
        status = {
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "running": self.running,
            "tasks": {},
        }
        
        for name, task in self.tasks.items():
            status["tasks"][name] = {
                "enabled": task.enabled,
                "schedule_time": task.schedule_time,
                "days": task.days,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
            }
        
        return status
    
    def run_task_now(self, name: str) -> bool:
        """Manually trigger a task to run immediately."""
        if name not in self.tasks:
            return False
        
        task = self.tasks[name]
        print(f"🔄 Manually running task: {name}")
        self._execute_task(task)
        return True


# --------------------------------------------------
# Convenience Functions
# --------------------------------------------------

def create_random_schedule(base_time: str, count: int = 3,
                          spread_hours: int = 4) -> List[str]:
    """
    Create multiple random schedule times spread around a base time.
    
    Args:
        base_time: Base time in HH:MM format
        count: Number of times to generate
        spread_hours: Hours to spread times across
    
    Returns:
        List of time strings
    """
    hour, minute = map(int, base_time.split(":"))
    base_minutes = hour * 60 + minute
    spread_minutes = spread_hours * 60
    
    times = []
    for _ in range(count):
        offset = random.randint(-spread_minutes // 2, spread_minutes // 2)
        new_minutes = base_minutes + offset
        
        # Clamp to valid range
        new_minutes = max(0, min(23 * 60 + 59, new_minutes))
        
        new_hour = new_minutes // 60
        new_minute = new_minutes % 60
        times.append(f"{new_hour:02d}:{new_minute:02d}")
    
    return sorted(times)


def get_active_hours() -> tuple:
    """
    Get typical active social media hours.
    
    Returns:
        Tuple of (start_hour, end_hour)
    """
    # Most social media activity: 9 AM - 9 PM
    return (9, 21)


def is_active_hour() -> bool:
    """Check if current time is within active hours."""
    start, end = get_active_hours()
    current_hour = datetime.now().hour
    return start <= current_hour <= end
