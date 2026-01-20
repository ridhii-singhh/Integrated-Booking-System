import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import dateparser
import pytz
from tzlocal import get_localzone
from typing import List, Tuple, Optional

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Get an authorized Google Calendar API service instance."""
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"Error loading token.json: {e}")
            os.remove("token.json")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"Token refresh failed: {e}")
                if os.path.exists("token.json"):
                    os.remove("token.json")
                creds = None
        
        if not creds:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        try:
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save token: {e}")
    
    return build("calendar", "v3", credentials=creds)

def parse_datetime(date_str: str, time_str: str) -> datetime.datetime:
    """Parse date and time strings into a timezone-aware datetime object."""
    try:
        # First try to parse the combined date and time
        combined_datetime = f"{date_str} {time_str}"
        parsed_datetime = dateparser.parse(combined_datetime)
        
        if parsed_datetime:
            # Ensure it's timezone-aware
            local_tz = get_localzone()
            if parsed_datetime.tzinfo is None:
                parsed_datetime = parsed_datetime.replace(tzinfo=local_tz)
            
            # Convert to UTC
            utc_datetime = parsed_datetime.astimezone(pytz.utc)
            return utc_datetime
        
        # Fallback: parse date and time separately
        parsed_date = dateparser.parse(date_str)
        if not parsed_date:
            raise ValueError(f"Could not parse date: '{date_str}'")
        
        # Ensure the date is timezone-aware
        local_tz = get_localzone()
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=local_tz)
        
        # Parse time and combine with date
        try:
            # Try to parse time in various formats
            time_parsed = dateparser.parse(time_str)
            if time_parsed:
                # Extract time components
                hour = time_parsed.hour
                minute = time_parsed.minute
                second = time_parsed.second
            else:
                # Try manual parsing for common formats
                if ':' in time_str:
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    second = 0
                else:
                    raise ValueError(f"Could not parse time: '{time_str}'")
            
            # Combine date and time
            combined_datetime = parsed_date.replace(
                hour=hour, 
                minute=minute, 
                second=second, 
                microsecond=0
            )
            
            # Convert to UTC
            utc_datetime = combined_datetime.astimezone(pytz.utc)
            return utc_datetime
            
        except Exception as time_error:
            raise ValueError(f"Could not parse time '{time_str}': {str(time_error)}")
            
    except Exception as e:
        raise ValueError(f"Error parsing datetime from date='{date_str}' and time='{time_str}': {str(e)}")

def check_availability(service, start_time, end_time, attendees: List[str]) -> Tuple[bool, Optional[List[dict]]]:
    """Check if a time slot is available for all attendees."""
    try:
        # Validate time range
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")
        
        # Ensure times are timezone-aware
        if start_time.tzinfo is None:
            local_tz = get_localzone()
            start_time = start_time.replace(tzinfo=local_tz)
        if end_time.tzinfo is None:
            local_tz = get_localzone()
            end_time = end_time.replace(tzinfo=local_tz)
        
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Validate attendees
        if not attendees:
            attendees = []
        
        calendars_to_check = [{"id": email} for email in attendees if email]
        calendars_to_check.append({"id": "primary"})

        body = {
            "timeMin": start_time_str,
            "timeMax": end_time_str,
            "items": calendars_to_check,
        }
        
        events_result = service.freebusy().query(body=body).execute()
        
        busy_slots = []
        for calendar_id, data in events_result["calendars"].items():
            if data["busy"]:
                busy_slots.extend(data["busy"])
        
        return len(busy_slots) == 0, busy_slots if busy_slots else None
        
    except Exception as e:
        raise ValueError(f"Error checking availability: {str(e)}")

def find_next_available_slots(service, start_time: datetime.datetime, duration_minutes: int, attendees: List[str]) -> List[datetime.datetime]:
    """Find next available time slots."""
    next_slots = []
    current_time = start_time
    
    while len(next_slots) < 3:
        end_time = current_time + datetime.timedelta(minutes=duration_minutes)
        is_available, _ = check_availability(service, current_time, end_time, attendees)
        if is_available:
            next_slots.append(current_time)
        current_time += datetime.timedelta(minutes=30)
        
    return next_slots

def create_event(service, title: str, start_time: datetime.datetime, end_time: datetime.datetime, attendees: List[str]) -> dict:
    """Create a calendar event."""
    event = {
        "summary": title,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": email} for email in attendees],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
    }
    created_event = service.events().insert(calendarId="primary", body=event, sendUpdates="all").execute()
    return created_event 


def find_events_by_date(service, target_date: str, target_time: Optional[str] = None) -> List[dict]:
    """Find events on a specific date, optionally at a specific time window (~1 hour)."""
    parsed_date = dateparser.parse(target_date)
    if not parsed_date:
        return []

    local_tz = get_localzone()
    start_of_day = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=local_tz)
    end_of_day = start_of_day + datetime.timedelta(days=1)

    utc_start = start_of_day.astimezone(pytz.utc)
    utc_end = end_of_day.astimezone(pytz.utc)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=utc_start.isoformat(),
        timeMax=utc_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    if target_time:
        time_str = f"{parsed_date.strftime('%Y-%m-%d')} {target_time}"
        target_dt = dateparser.parse(time_str)
        if target_dt:
            target_dt = target_dt.replace(tzinfo=local_tz).astimezone(pytz.utc)
            filtered = []
            for event in events:
                ev_start = event.get("start", {}).get("dateTime")
                if ev_start:
                    ev_dt = datetime.datetime.fromisoformat(ev_start.replace("Z", "+00:00"))
                    if abs((ev_dt - target_dt).total_seconds()) <= 60 * 60:
                        filtered.append(event)
            return filtered

    return events


def update_event(
    service,
    event_id: str,
    new_start_time: datetime.datetime,
    new_end_time: datetime.datetime,
    new_summary: Optional[str] = None,
    new_attendees: Optional[List[str]] = None,
) -> dict:
    """Update an existing event."""
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    event["start"] = {"dateTime": new_start_time.isoformat(), "timeZone": "UTC"}
    event["end"] = {"dateTime": new_end_time.isoformat(), "timeZone": "UTC"}
    if new_summary:
        event["summary"] = new_summary
    if new_attendees is not None:
        event["attendees"] = [{"email": email} for email in new_attendees]
    updated = service.events().update(calendarId="primary", eventId=event_id, body=event, sendUpdates="all").execute()
    return updated


def delete_event(service, event_id: str) -> bool:
    """Delete an event; returns True if successful."""
    try:
        # First get the event details to extract attendee emails
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        
        # Delete the event with email notifications
        service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()
        
        # Log the deletion for debugging
        attendees = event.get('attendees', [])
        attendee_emails = [att.get('email') for att in attendees if att.get('email')]
        print(f"Deleted event '{event.get('summary', 'Unknown')}' with attendees: {attendee_emails}")
        
        return True
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False


def parse_datetime_with_timezone(date_str: str, time_str: Optional[str] = None) -> Optional[datetime.datetime]:
    """Parse date and optional time in local tz and return UTC datetime."""
    datetime_str = f"{date_str} {time_str}" if time_str else date_str
    parsed_dt = dateparser.parse(datetime_str)
    if not parsed_dt:
        return None
    if not time_str:
        parsed_dt = parsed_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    local_tz = get_localzone()
    local_dt = parsed_dt.replace(tzinfo=local_tz)
    return local_dt.astimezone(pytz.utc)