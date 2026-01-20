import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import dateparser
import pytz
from tzlocal import get_localzone

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def check_availability(service, start_time, end_time, attendees):
    # isoformat() on a timezone-aware object includes the timezone automatically
    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()
    
    # Check the calendars of all attendees plus the primary calendar of the user
    calendars_to_check = [{"id": email} for email in attendees]
    calendars_to_check.append({"id": "primary"})

    body = {
        "timeMin": start_time_str,
        "timeMax": end_time_str,
        "items": calendars_to_check,
    }
    
    events_result = service.freebusy().query(body=body).execute()
    
    # If any of the calendars have busy slots, the time is unavailable
    for calendar_id, data in events_result["calendars"].items():
        if data["busy"]:
            return False, data["busy"]
            
    return True, None

def find_next_available_slots(service, start_time, duration_minutes, attendees):
    next_slots = []
    current_time = start_time
    
    while len(next_slots) < 3:
        end_time = current_time + datetime.timedelta(minutes=duration_minutes)
        is_available, _ = check_availability(service, current_time, end_time, attendees)
        if is_available:
            next_slots.append(current_time)
        current_time += datetime.timedelta(minutes=30)
        
    return next_slots

def create_event(service, title, start_time, end_time, attendees):
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

def find_events_by_date(service, target_date, target_time=None):
    """
    Find events on a specific date, optionally at a specific time.
    
    Args:
        service: Google Calendar service
        target_date: Date string (e.g., "8th august 2025", "next friday")
        target_time: Optional time string (e.g., "8 am", "8pm")
    
    Returns:
        List of events matching the criteria
    """
    # Parse the target date
    parsed_date = dateparser.parse(target_date)
    if not parsed_date:
        return []
    
    # Set the time range for the entire day
    local_tz = get_localzone()
    start_of_day = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day = start_of_day.replace(tzinfo=local_tz)
    end_of_day = start_of_day + datetime.timedelta(days=1)
    
    # Convert to UTC
    utc_start = start_of_day.astimezone(pytz.utc)
    utc_end = end_of_day.astimezone(pytz.utc)
    
    # Get events for the day
    events_result = service.events().list(
        calendarId='primary',
        timeMin=utc_start.isoformat(),
        timeMax=utc_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # If a specific time is provided, filter events at that time
    if target_time:
        # Parse the target time
        time_str = f"{parsed_date.strftime('%Y-%m-%d')} {target_time}"
        target_datetime = dateparser.parse(time_str)
        if target_datetime:
            target_datetime = target_datetime.replace(tzinfo=local_tz)
            target_utc = target_datetime.astimezone(pytz.utc)
            
            # Find events that start at or around the target time (within 1 hour)
            filtered_events = []
            for event in events:
                event_start = event['start'].get('dateTime')
                if event_start:
                    event_start_dt = datetime.datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                    time_diff = abs((event_start_dt - target_utc).total_seconds() / 60)
                    if time_diff <= 60:  # Within 1 hour
                        filtered_events.append(event)
            return filtered_events
    
    return events

def update_event(service, event_id, new_start_time, new_end_time, new_summary=None, new_attendees=None):
    """
    Update an existing event with new details.
    
    Args:
        service: Google Calendar service
        event_id: ID of the event to update
        new_start_time: New start time (UTC datetime)
        new_end_time: New end time (UTC datetime)
        new_summary: Optional new title
        new_attendees: Optional list of new attendee emails
    
    Returns:
        Updated event
    """
    # Get the current event
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    # Update the event details
    event['start'] = {"dateTime": new_start_time.isoformat(), "timeZone": "UTC"}
    event['end'] = {"dateTime": new_end_time.isoformat(), "timeZone": "UTC"}
    
    if new_summary:
        event['summary'] = new_summary
    
    if new_attendees:
        event['attendees'] = [{"email": email} for email in new_attendees]
    
    # Update the event
    updated_event = service.events().update(
        calendarId='primary',
        eventId=event_id,
        body=event,
        sendUpdates='all'
    ).execute()
    
    return updated_event

def delete_event(service, event_id):
    """
    Delete an event.
    
    Args:
        service: Google Calendar service
        event_id: ID of the event to delete
    
    Returns:
        True if successful
    """
    try:
        service.events().delete(
            calendarId='primary',
            eventId=event_id,
            sendUpdates='all'
        ).execute()
        return True
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False

def parse_datetime_with_timezone(date_str, time_str=None):
    """
    Parse a date and optional time string into a timezone-aware datetime.
    
    Args:
        date_str: Date string (e.g., "8th august 2025")
        time_str: Optional time string (e.g., "8 am")
    
    Returns:
        UTC datetime object
    """
    if time_str:
        datetime_str = f"{date_str} {time_str}"
    else:
        datetime_str = date_str
    
    parsed_dt = dateparser.parse(datetime_str)
    if not parsed_dt:
        return None
    
    # For date-only parsing (no time specified), ensure we get the correct date
    # by setting the time to noon to avoid timezone conversion issues
    if not time_str:
        parsed_dt = parsed_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    
    local_tz = get_localzone()
    local_dt = parsed_dt.replace(tzinfo=local_tz)
    return local_dt.astimezone(pytz.utc) 