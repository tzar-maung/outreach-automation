"""
Google Sheets Integration

Read targets from Google Sheet and update status after DM.

Setup:
1. Create a Google Sheet with columns: username, url, status, notes
2. Make the sheet PUBLIC (View only) - or use API key
3. Get the Sheet ID from the URL

Usage:
    sheet = GoogleSheetTargets(sheet_id="YOUR_SHEET_ID")
    targets = sheet.get_targets()
    
    # After sending DM
    sheet.update_status(row=2, status="sent", notes="DM sent 2024-01-18")
"""
import csv
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# Try to import gspread (optional dependency)
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class GoogleSheetTargets:
    """
    Read targets from Google Sheets.
    
    Two modes:
    1. Public sheet (no auth) - uses CSV export URL
    2. Service account (full access) - can update status
    """
    
    def __init__(self, sheet_id: str = None, 
                 sheet_url: str = None,
                 credentials_file: str = None,
                 sheet_name: str = "Sheet1"):
        """
        Initialize Google Sheets connection.
        
        Args:
            sheet_id: Google Sheet ID (from URL)
            sheet_url: Full Google Sheet URL
            credentials_file: Path to service account JSON (optional)
            sheet_name: Name of the sheet tab
        """
        # Extract sheet ID from URL if provided
        if sheet_url and not sheet_id:
            sheet_id = self._extract_sheet_id(sheet_url)
        
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.credentials_file = credentials_file
        
        self.targets = []
        self.sheet = None  # gspread worksheet object
        
        # Connect if credentials provided
        if credentials_file and GSPREAD_AVAILABLE:
            self._connect_with_service_account()
    
    def _extract_sheet_id(self, url: str) -> str:
        """Extract sheet ID from Google Sheets URL."""
        # URL format: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        try:
            parts = url.split("/d/")[1].split("/")[0]
            return parts
        except (IndexError, AttributeError):
            return url  # Assume it's already an ID
    
    def _connect_with_service_account(self):
        """Connect using service account credentials."""
        if not GSPREAD_AVAILABLE:
            raise ImportError("gspread not installed. Run: pip install gspread google-auth")
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        
        creds = Credentials.from_service_account_file(
            self.credentials_file, scopes=scopes
        )
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(self.sheet_id)
        self.sheet = spreadsheet.worksheet(self.sheet_name)
    
    def get_targets_from_public_sheet(self) -> List[Dict]:
        """
        Get targets from a PUBLIC Google Sheet (no auth required).
        
        Sheet must be shared as "Anyone with link can view".
        
        Expected columns: username, url, status, notes, niche
        """
        import urllib.request
        
        # CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv"
        
        try:
            response = urllib.request.urlopen(csv_url)
            lines = response.read().decode('utf-8').splitlines()
            
            reader = csv.DictReader(lines)
            
            targets = []
            for row in reader:
                # Skip empty rows
                if not row.get('username') and not row.get('url'):
                    continue
                
                # Skip already processed
                status = row.get('status', '').lower()
                if status in ['sent', 'done', 'skip', 'failed']:
                    continue
                
                target = {
                    'username': row.get('username', '').strip().lstrip('@'),
                    'url': row.get('url', '').strip(),
                    'status': row.get('status', 'pending'),
                    'notes': row.get('notes', ''),
                    'niche': row.get('niche', 'content'),
                    'platform': 'instagram',
                }
                
                # Generate URL from username if not provided
                if not target['url'] and target['username']:
                    target['url'] = f"https://www.instagram.com/{target['username']}/"
                
                # Extract username from URL if not provided
                if not target['username'] and target['url']:
                    target['username'] = target['url'].rstrip('/').split('/')[-1]
                
                if target['username'] or target['url']:
                    targets.append(target)
            
            self.targets = targets
            return targets
            
        except Exception as e:
            print(f"Error reading Google Sheet: {e}")
            print("Make sure the sheet is shared as 'Anyone with link can view'")
            return []
    
    def get_targets(self) -> List[Dict]:
        """
        Get targets from Google Sheet.
        
        Uses service account if connected, otherwise public CSV export.
        """
        if self.sheet:
            return self._get_targets_with_auth()
        else:
            return self.get_targets_from_public_sheet()
    
    def _get_targets_with_auth(self) -> List[Dict]:
        """Get targets using authenticated connection."""
        if not self.sheet:
            raise Exception("Not connected. Provide credentials_file or use public sheet.")
        
        # Get all records
        records = self.sheet.get_all_records()
        
        targets = []
        for i, row in enumerate(records, start=2):  # Row 2 onwards (1 is header)
            # Skip empty or processed rows
            if not row.get('username') and not row.get('url'):
                continue
            
            status = str(row.get('status', '')).lower()
            if status in ['sent', 'done', 'skip', 'failed']:
                continue
            
            target = {
                'username': str(row.get('username', '')).strip().lstrip('@'),
                'url': str(row.get('url', '')).strip(),
                'status': row.get('status', 'pending'),
                'notes': row.get('notes', ''),
                'niche': row.get('niche', 'content'),
                'platform': 'instagram',
                'row_number': i,  # For updating later
            }
            
            # Generate URL from username if not provided
            if not target['url'] and target['username']:
                target['url'] = f"https://www.instagram.com/{target['username']}/"
            
            if target['username'] or target['url']:
                targets.append(target)
        
        self.targets = targets
        return targets
    
    def update_status(self, row: int, status: str, notes: str = None):
        """
        Update status in Google Sheet (requires service account).
        
        Args:
            row: Row number (2 = first data row)
            status: New status (sent, failed, skip)
            notes: Additional notes
        """
        if not self.sheet:
            print("Cannot update: No authenticated connection")
            return False
        
        try:
            # Find status column
            headers = self.sheet.row_values(1)
            
            status_col = None
            notes_col = None
            
            for i, header in enumerate(headers, start=1):
                if header.lower() == 'status':
                    status_col = i
                if header.lower() == 'notes':
                    notes_col = i
            
            # Update status
            if status_col:
                self.sheet.update_cell(row, status_col, status)
            
            # Update notes
            if notes_col and notes:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                existing_notes = self.sheet.cell(row, notes_col).value or ""
                new_notes = f"{existing_notes} | {status} {timestamp}" if existing_notes else f"{status} {timestamp}"
                self.sheet.update_cell(row, notes_col, new_notes)
            
            return True
            
        except Exception as e:
            print(f"Error updating sheet: {e}")
            return False
    
    def mark_sent(self, row: int):
        """Mark target as DM sent."""
        return self.update_status(row, "sent", "DM sent")
    
    def mark_failed(self, row: int, reason: str = ""):
        """Mark target as failed."""
        return self.update_status(row, "failed", reason)
    
    def mark_skipped(self, row: int, reason: str = ""):
        """Mark target as skipped."""
        return self.update_status(row, "skip", reason)
    
    def print_targets(self):
        """Print loaded targets."""
        if not self.targets:
            print("No targets loaded. Call get_targets() first.")
            return
        
        print(f"\n{'='*50}")
        print(f"TARGETS FROM GOOGLE SHEET ({len(self.targets)} total)")
        print(f"{'='*50}")
        
        for i, t in enumerate(self.targets, 1):
            print(f"{i}. @{t['username']}")
            print(f"   Niche: {t.get('niche', 'N/A')}")
            print(f"   Status: {t.get('status', 'pending')}")
        
        print(f"{'='*50}\n")


# --------------------------------------------------
# Simple CSV Alternative
# --------------------------------------------------

def download_sheet_as_csv(sheet_id: str, output_file: str = "data/targets.csv") -> bool:
    """
    Download a public Google Sheet as CSV.
    
    Args:
        sheet_id: Google Sheet ID or full URL
        output_file: Where to save the CSV
    
    Returns:
        True if successful
    """
    import urllib.request
    
    # Extract ID from URL if needed
    if "docs.google.com" in sheet_id:
        sheet_id = sheet_id.split("/d/")[1].split("/")[0]
    
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        # Download
        response = urllib.request.urlopen(csv_url)
        content = response.read().decode('utf-8')
        
        # Save to file
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Count rows
        lines = content.strip().split('\n')
        print(f"Downloaded {len(lines)-1} targets to {output_file}")
        
        return True
        
    except Exception as e:
        print(f"Error downloading sheet: {e}")
        print("Make sure the sheet is shared as 'Anyone with link can view'")
        return False


# --------------------------------------------------
# Example Sheet Template
# --------------------------------------------------

SHEET_TEMPLATE = """
To use Google Sheets with this bot:

1. Create a new Google Sheet
2. Add these columns in Row 1:
   username | url | status | notes | niche

3. Add your targets:
   fashiongirl1 | https://www.instagram.com/fashiongirl1 | | | fashion
   fitnessbabe2 | https://www.instagram.com/fitnessbabe2 | | | fitness
   beautyblogger3 | | | | beauty

4. Share the sheet:
   - Click "Share" button
   - Change to "Anyone with the link can view"
   - Copy the link

5. Use with bot:
   python -m outreach_bot.main --sheet "YOUR_SHEET_URL" --dm --max-targets 10

The 'status' column will show:
   - (blank) = pending
   - sent = DM sent successfully
   - failed = DM failed
   - skip = skipped (rate limit, etc.)
"""

def print_sheet_template():
    """Print instructions for setting up Google Sheet."""
    print(SHEET_TEMPLATE)
