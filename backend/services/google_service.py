import os
import json
import base64
import email
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
TOKEN_FILE = os.path.join(DATA_DIR, "google_tokens.json")

def get_client_config() -> Optional[Dict[str, Any]]:
    """Loads client credentials from environment variables or client_secret.json."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    
    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
    
    # Check for client_secret.json in data or root directory
    secret_path = os.path.join(DATA_DIR, "client_secret.json")
    if not os.path.exists(secret_path):
        secret_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "client_secret.json")
    
    if os.path.exists(secret_path):
        with open(secret_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    return None

def get_oauth_url(redirect_uri: Optional[str] = None) -> Dict[str, str]:
    """Generates the OAuth 2.0 authorization URL."""
    config = get_client_config()
    if not config:
        return {
            "error": "Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        }
    
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=r_uri
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return {"url": auth_url, "state": state}

def handle_oauth_callback(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """Exchanges auth code for access & refresh tokens, saves securely to disk."""
    config = get_client_config()
    if not config:
        return {"success": False, "error": "Google OAuth configuration missing."}
    
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    try:
        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri=r_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save credentials securely to disk
        os.makedirs(DATA_DIR, exist_ok=True)
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None
        }
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)
            
        # Get user profile email
        email_addr = "Connected"
        try:
            oauth2_service = build("oauth2", "v2", credentials=creds)
            user_info = oauth2_service.userinfo().get().execute()
            email_addr = user_info.get("email", "Connected")
        except Exception:
            pass

        return {"success": True, "email": email_addr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_google_credentials() -> Optional[Credentials]:
    """Loads and auto-refreshes Google credentials."""
    if not os.path.exists(TOKEN_FILE):
        return None
        
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)
            
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes")
        )
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            token_data["token"] = creds.token
            token_data["expiry"] = creds.expiry.isoformat() if creds.expiry else None
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
                
        return creds
    except Exception as e:
        print(f"  [Google Credentials error]: {e}")
        return None

def get_connection_status() -> Dict[str, Any]:
    """Returns the Google connection state and user email."""
    creds = get_google_credentials()
    if not creds:
        return {"connected": False, "email": None}
    
    try:
        oauth2_service = build("oauth2", "v2", credentials=creds)
        user_info = oauth2_service.userinfo().get().execute()
        return {"connected": True, "email": user_info.get("email")}
    except Exception:
        return {"connected": True, "email": "Google Connected"}

def disconnect_google() -> bool:
    """Disconnects Google account and deletes local tokens."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            return True
        except Exception:
            return False
    return True

# ─────────────────────────────────────────────────────────────────────────────
# GMAIL TOOLS
# ─────────────────────────────────────────────────────────────────────────────

def search_emails(query: str = "", max_results: int = 5) -> List[Dict[str, Any]]:
    """Searches emails using Gmail search syntax (e.g., 'is:unread', 'from:professor', 'internship')."""
    creds = get_google_credentials()
    if not creds:
        return [{
            "status": "not_connected",
            "message": "Google account not connected. Please connect your Google account in Settings to search emails."
        }]
    
    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])
        
        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
                                                     metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "sender": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(No Subject)"),
                "date": headers.get("Date", ""),
                "snippet": msg_data.get("snippet", "")
            })
        return emails
    except Exception as e:
        return [{"status": "error", "message": f"Gmail search error: {str(e)}"}]

def read_email(message_id: str) -> Dict[str, Any]:
    """Retrieves full email content including headers and cleaned body text."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
    
    try:
        service = build("gmail", "v1", credentials=creds)
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        
        body_text = ""
        payload = msg.get("payload", {})
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        elif "body" in payload and payload["body"].get("data"):
            body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
            
        if not body_text:
            body_text = msg.get("snippet", "")
            
        return {
            "id": message_id,
            "thread_id": msg.get("threadId"),
            "sender": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", "(No Subject)"),
            "date": headers.get("Date", ""),
            "body": body_text[:4000] # Safe limit
        }
    except Exception as e:
        return {"status": "error", "message": f"Gmail read error: {str(e)}"}

def summarize_email_thread(thread_id: str) -> Dict[str, Any]:
    """Retrieves all messages in a thread for summarization."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("gmail", "v1", credentials=creds)
        thread = service.users().threads().get(userId="me", id=thread_id).execute()
        messages = thread.get("messages", [])
        
        convo_snippets = []
        for msg in messages:
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            sender = headers.get("From", "Unknown")
            date = headers.get("Date", "")
            snippet = msg.get("snippet", "")
            convo_snippets.append(f"From: {sender} ({date})\nMessage: {snippet}")
            
        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "thread_content": "\n---\n".join(convo_snippets)
        }
    except Exception as e:
        return {"status": "error", "message": f"Gmail thread error: {str(e)}"}

def create_email_draft(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Creates a draft email in Gmail without sending it."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()
        
        return {
            "status": "success",
            "draft_id": draft.get("id"),
            "to": to,
            "subject": subject,
            "message": "Draft created successfully in Gmail."
        }
    except Exception as e:
        return {"status": "error", "message": f"Gmail draft creation failed: {str(e)}"}

def send_email_direct(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Directly sends an email. IMPORTANT: Only invoke after explicit human approval."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()
        
        return {
            "status": "success",
            "message_id": sent.get("id"),
            "to": to,
            "subject": subject,
            "message": f"Email successfully sent to {to}."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE CALENDAR TOOLS
# ─────────────────────────────────────────────────────────────────────────────

def list_calendar_events(time_min: Optional[str] = None, time_max: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
    """Retrieves upcoming Google Calendar events."""
    creds = get_google_credentials()
    if not creds:
        return [{
            "status": "not_connected",
            "message": "Google account not connected. Please connect your Google account in Settings."
        }]
        
    try:
        service = build("calendar", "v3", credentials=creds)
        now_iso = datetime.utcnow().isoformat() + "Z"
        t_min = time_min or now_iso
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=t_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        items = events_result.get("items", [])
        events = []
        for it in items:
            start = it.get("start", {}).get("dateTime", it.get("start", {}).get("date"))
            end = it.get("end", {}).get("dateTime", it.get("end", {}).get("date"))
            attendees = [a.get("email") for a in it.get("attendees", []) if a.get("email")]
            events.append({
                "id": it.get("id"),
                "summary": it.get("summary", "(No Title)"),
                "description": it.get("description", ""),
                "start": start,
                "end": end,
                "attendees": attendees,
                "location": it.get("location", "")
            })
        return events
    except Exception as e:
        return [{"status": "error", "message": f"Calendar error: {str(e)}"}]

def check_calendar_availability(start_iso: str, end_iso: str) -> Dict[str, Any]:
    """Checks if there is a conflict in the primary calendar between start and end times."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("calendar", "v3", credentials=creds)
        body = {
            "timeMin": start_iso,
            "timeMax": end_iso,
            "items": [{"id": "primary"}]
        }
        res = service.freebusy().query(body=body).execute()
        busy_slots = res.get("calendars", {}).get("primary", {}).get("busy", [])
        is_free = len(busy_slots) == 0
        return {
            "available": is_free,
            "busy_count": len(busy_slots),
            "busy_slots": busy_slots
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def find_free_meeting_slots(duration_minutes: int = 30, days_ahead: int = 3) -> List[Dict[str, Any]]:
    """Scans business hours (9 AM - 5 PM) over the next N days to find available meeting slots."""
    creds = get_google_credentials()
    if not creds:
        return [{"status": "not_connected", "message": "Google account not connected."}]
        
    now = datetime.now()
    available_slots = []
    
    try:
        # Check upcoming 3 days
        for day_offset in range(days_ahead):
            check_date = now.date() + timedelta(days=day_offset)
            # Skip weekends if needed, or scan 9 AM to 5 PM
            for hour in range(9, 17):
                slot_start = datetime(check_date.year, check_date.month, check_date.day, hour, 0)
                if slot_start < now:
                    continue
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Check slot
                avail = check_calendar_availability(
                    slot_start.isoformat() + "Z",
                    slot_end.isoformat() + "Z"
                )
                if avail.get("available", False):
                    available_slots.append({
                        "start": slot_start.strftime("%Y-%m-%d %I:%M %p"),
                        "end": slot_end.strftime("%I:%M %p"),
                        "start_iso": slot_start.isoformat() + "Z",
                        "end_iso": slot_end.isoformat() + "Z"
                    })
                    if len(available_slots) >= 5:
                        return available_slots
        return available_slots
    except Exception as e:
        return [{"status": "error", "message": str(e)}]

def create_calendar_event_direct(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Directly creates a calendar event. IMPORTANT: Only invoke after explicit human approval."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("calendar", "v3", credentials=creds)
        event_body: Dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time}
        }
        if attendees:
            event_body["attendees"] = [{"email": a} for a in attendees]
            
        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return {
            "status": "success",
            "event_id": created.get("id"),
            "summary": summary,
            "start": start_time,
            "end": end_time,
            "htmlLink": created.get("htmlLink"),
            "message": f"Event '{summary}' scheduled successfully."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create event: {str(e)}"}

def update_calendar_event_direct(
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Updates an existing calendar event. Only invoke after explicit human approval."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("calendar", "v3", credentials=creds)
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        if summary:
            event["summary"] = summary
        if start_time:
            event["start"] = {"dateTime": start_time}
        if end_time:
            event["end"] = {"dateTime": end_time}
            
        updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return {
            "status": "success",
            "event_id": event_id,
            "summary": updated.get("summary"),
            "message": "Calendar event updated successfully."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to update event: {str(e)}"}

def delete_calendar_event_direct(event_id: str) -> Dict[str, Any]:
    """Deletes a calendar event. Only invoke after explicit human approval."""
    creds = get_google_credentials()
    if not creds:
        return {"status": "not_connected", "message": "Google account not connected."}
        
    try:
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {
            "status": "success",
            "event_id": event_id,
            "message": "Calendar event deleted successfully."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete event: {str(e)}"}
