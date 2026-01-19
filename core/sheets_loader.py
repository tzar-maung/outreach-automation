"""
Google Sheets Integration

Read targets from a Google Sheet instead of CSV.

Setup (EASIEST - No API needed):
1. Create your Google Sheet with columns: username, url, niche
2. Click Share -> Anyone with the link -> Viewer
3. Copy the URL
4. Run: python -m outreach_bot.main --sheet "YOUR_URL" --dm

OR export as CSV and use directly.
"""
import csv
import urllib.request
import urllib.error
from typing import List, Dict, Optional
from pathlib import Path


class GoogleSheetsLoader:
    """
    Load targets from Google Sheets.
    
    Requires: pip install gspread google-auth
    """
    
    def __init__(self, credentials_file: str = "credentials.json"):
        """
        Initialize with Google service account credentials.
        
        Args:
            credentials_file: Path to service account JSON file
        """
        self.credentials_file = credentials_file
        self.client = None
        
    def connect(self):
        """Connect to Google Sheets API."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly'
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scopes
            )
            
            self.client = gspread.authorize(creds)
            return True
            
        except ImportError:
            print("ERROR: Install required packages:")
            print("  pip install gspread google-auth")
            return False
            
        except Exception as e:
            print(f"ERROR: Could not connect to Google Sheets: {e}")
            return False
    
    def load_targets(self, sheet_name: str, 
                     worksheet_name: str = "Sheet1") -> List[Dict]:
        """
        Load targets from a Google Sheet.
        
        Expected columns: url, username, niche, notes (optional)
        
        Args:
            sheet_name: Name of the Google Sheet
            worksheet_name: Name of the worksheet tab
        
        Returns:
            List of target dictionaries
        """
        if not self.client:
            if not self.connect():
                return []
        
        try:
            # Open sheet
            sheet = self.client.open(sheet_name)
            worksheet = sheet.worksheet(worksheet_name)
            
            # Get all records
            records = worksheet.get_all_records()
            
            targets = []
            for row in records:
                # Skip empty rows
                if not row.get('url') and not row.get('username'):
                    continue
                
                # Build URL if only username provided
                url = row.get('url', '')
                username = row.get('username', '')
                
                if not url and username:
                    url = f"https://www.instagram.com/{username.lstrip('@')}/"
                
                if not username and url:
                    username = url.rstrip('/').split('/')[-1]
                
                targets.append({
                    'url': url,
                    'username': username,
                    'platform': row.get('platform', 'instagram'),
                    'niche': row.get('niche', ''),
                    'notes': row.get('notes', ''),
                    'followers': row.get('followers', 0),
                    'status': row.get('status', 'pending'),
                })
            
            print(f"Loaded {len(targets)} targets from Google Sheet")
            return targets
            
        except Exception as e:
            print(f"ERROR loading sheet: {e}")
            return []
    
    def update_status(self, sheet_name: str, username: str, 
                      status: str, worksheet_name: str = "Sheet1"):
        """
        Update the status of a target in the sheet.
        
        Args:
            sheet_name: Name of the Google Sheet
            username: Username to update
            status: New status (e.g., "dm_sent", "followed", "error")
        """
        if not self.client:
            return False
        
        try:
            sheet = self.client.open(sheet_name)
            worksheet = sheet.worksheet(worksheet_name)
            
            # Find the row with this username
            cell = worksheet.find(username)
            if cell:
                # Find status column (assume it's column F or create it)
                status_col = 6  # Column F
                worksheet.update_cell(cell.row, status_col, status)
                return True
                
        except Exception as e:
            print(f"Could not update status: {e}")
        
        return False


def load_from_public_sheet(sheet_url: str) -> List[Dict]:
    """
    Load targets from a PUBLIC Google Sheet (no auth needed).
    
    The sheet must be:
    1. Set to "Anyone with the link can view"
    2. Have columns: url, username, niche (optional)
    
    Args:
        sheet_url: The Google Sheet URL or share link
    
    Returns:
        List of target dictionaries
    """
    try:
        # Extract sheet ID from URL
        if '/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            sheet_id = sheet_url
        
        # Build CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Download CSV using urllib
        response = urllib.request.urlopen(csv_url, timeout=30)
        content = response.read().decode('utf-8')
        
        # Parse CSV
        lines = content.strip().split('\n')
        reader = csv.DictReader(lines)
        
        targets = []
        for row in reader:
            url = row.get('url', '').strip()
            username = row.get('username', '').strip().lstrip('@')
            
            # Skip empty rows
            if not url and not username:
                continue
            
            # Skip rows marked as done/sent
            status = row.get('status', '').lower()
            if status in ['sent', 'done', 'skip', 'error']:
                continue
            
            if not url and username:
                url = f"https://www.instagram.com/{username}/"
            
            if not username and url:
                username = url.rstrip('/').split('/')[-1]
            
            if url or username:
                targets.append({
                    'url': url,
                    'username': username,
                    'platform': row.get('platform', 'instagram'),
                    'niche': row.get('niche', ''),
                    'notes': row.get('notes', ''),
                    'followers': int(row.get('followers', 0) or 0),
                })
        
        print(f"[OK] Loaded {len(targets)} targets from Google Sheet")
        return targets
        
    except urllib.error.HTTPError as e:
        print(f"ERROR: Could not access Google Sheet (HTTP {e.code})")
        print("Make sure the sheet is set to 'Anyone with the link can view'")
        return []
    except Exception as e:
        print(f"ERROR loading sheet: {e}")
        return []


def export_sheet_to_csv(sheet_url: str, output_file: str = "data/targets.csv"):
    """
    Download a public Google Sheet and save as CSV.
    
    This is the EASIEST method - no API setup needed!
    
    Args:
        sheet_url: Google Sheet URL
        output_file: Where to save the CSV
    """
    targets = load_from_public_sheet(sheet_url)
    
    if not targets:
        return False
    
    # Save to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ['url', 'platform', 'username', 'notes', 'niche', 'followers']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for target in targets:
            writer.writerow({
                'url': target['url'],
                'platform': target.get('platform', 'instagram'),
                'username': target['username'],
                'notes': target.get('notes', ''),
                'niche': target.get('niche', ''),
                'followers': target.get('followers', 0),
            })
    
    print(f"Saved {len(targets)} targets to {output_file}")
    return True


# --------------------------------------------------
# Simple CSV-based approach (recommended)
# --------------------------------------------------

def create_template_csv(output_file: str = "data/targets.csv"):
    """
    Create a template CSV file that user can fill in.
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    template = """url,platform,username,notes,niche,followers
https://www.instagram.com/example1,instagram,example1,Found on explore,fitness,5000
https://www.instagram.com/example2,instagram,example2,Friend recommended,beauty,8000
"""
    
    with open(output_path, 'w') as f:
        f.write(template)
    
    print(f"Template created: {output_file}")
    print("\nEdit this file to add your targets!")
    print("Required columns: url OR username")
    print("Optional columns: niche, notes, followers")


def load_targets_from_csv(filepath: str = "data/targets.csv") -> List[Dict]:
    """
    Load targets from CSV file.
    
    This is the simplest method - just edit the CSV!
    """
    try:
        targets = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Skip comments and empty rows
                url = row.get('url', '').strip()
                if not url or url.startswith('#'):
                    continue
                
                username = row.get('username', '')
                if not username:
                    username = url.rstrip('/').split('/')[-1]
                
                targets.append({
                    'url': url,
                    'username': username,
                    'platform': row.get('platform', 'instagram'),
                    'niche': row.get('niche', ''),
                    'notes': row.get('notes', ''),
                    'followers': int(row.get('followers', 0) or 0),
                })
        
        print(f"Loaded {len(targets)} targets from {filepath}")
        return targets
        
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        print("Create it with: python -m outreach_bot.main --create-template")
        return []
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []
