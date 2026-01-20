import datetime
import pytz
from typing import Dict, Any, List, Optional
from llm_service import (
    parse_meeting_details,
    parse_command_type,
    parse_reschedule_details,
    parse_cancel_details,
)
from calendar_service import (
    get_calendar_service,
    parse_datetime,
    check_availability,
    find_next_available_slots,
    create_event,
    find_events_by_date,
    update_event,
    delete_event,
    parse_datetime_with_timezone,
)
from email_service import email_service
from tzlocal import get_localzone

class BookingService:
    def __init__(self):
        self.calendar_service = get_calendar_service()
    
    def process_booking_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language booking command.
        
        Args:
            command: Natural language command like "book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins"
        
        Returns:
            Dictionary with booking result
        """
        try:
            # Parse the command
            meeting_details = parse_meeting_details(command)
            
            # Validate meeting details
            if not meeting_details.title:
                return {
                    'success': False,
                    'message': "Could not extract meeting title from command",
                    'requires_confirmation': False
                }
            
            if not meeting_details.attendees:
                return {
                    'success': False,
                    'message': "No attendees found in command. Please specify at least one email address.",
                    'requires_confirmation': False
                }
            
            # Parse datetime
            try:
                start_time = parse_datetime(meeting_details.date, meeting_details.time)
                end_time = start_time + datetime.timedelta(minutes=meeting_details.duration)
            except ValueError as e:
                return {
                    'success': False,
                    'message': f"Could not parse date/time: {str(e)}. Please provide a clear date and time.",
                    'requires_confirmation': False
                }
            
            # Check availability
            try:
                is_available, busy_slots = check_availability(
                    self.calendar_service, start_time, end_time, meeting_details.attendees
                )
            except ValueError as e:
                return {
                    'success': False,
                    'message': f"Error checking calendar availability: {str(e)}",
                    'requires_confirmation': False
                }
            
            if is_available:
                # Time slot is available, ask for confirmation
                local_tz = get_localzone()
                display_time = start_time.astimezone(local_tz)
                
                return {
                    'success': True,
                    'message': f"The time slot is available. Do you want to book the meeting '{meeting_details.title}' on {display_time.strftime('%Y-%m-%d %H:%M')}?",
                    'meeting_details': meeting_details.dict(),
                    'available_slots': [{
                        'start_time': start_time,
                        'end_time': end_time,
                        'display_time': display_time.strftime('%Y-%m-%d %H:%M'),
                        'is_available': True
                    }],
                    'requires_confirmation': True,
                    'command': command
                }
            else:
                # Time slot is not available, find alternatives
                alternative_slots = find_next_available_slots(
                    self.calendar_service, start_time, meeting_details.duration, meeting_details.attendees
                )
                
                slots_info = []
                local_tz = get_localzone()
                for slot in alternative_slots:
                    display_time = slot.astimezone(local_tz)
                    end_slot = slot + datetime.timedelta(minutes=meeting_details.duration)
                    slots_info.append({
                        'start_time': slot,
                        'end_time': end_slot,
                        'display_time': display_time.strftime('%Y-%m-%d %H:%M'),
                        'is_available': True
                    })
                
                return {
                    'success': True,
                    'message': f"The requested time is unavailable. Here are alternative slots:",
                    'meeting_details': meeting_details.dict(),
                    'available_slots': slots_info,
                    'requires_confirmation': True,
                    'command': command
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Error processing command: {str(e)}",
                'requires_confirmation': False
            }
    
    def confirm_and_book(self, command: str, confirmation: str) -> Dict[str, Any]:
        """
        Confirm and book the meeting.
        
        Args:
            command: Original command
            confirmation: 'yes' or 'no'
        
        Returns:
            Dictionary with booking result
        """
        if confirmation.lower() != 'yes':
            return {
                'success': False,
                'message': 'Booking cancelled by user.',
                'event_link': None
            }
        try:
            # Re-process the command to get meeting details
            result = self.process_booking_command(command)
            
            if not result['success']:
                return result
            
            meeting_details = result['meeting_details']
            available_slots = result['available_slots']
            
            if not available_slots:
                return {
                    'success': False,
                    'message': 'No available slots found.',
                    'event_link': None
                }
            
            # Use the first available slot
            start_time = available_slots[0]['start_time']
            end_time = available_slots[0]['end_time']
            
            # Create the event
            created_event = create_event(
                self.calendar_service, 
                meeting_details['title'], 
                start_time, 
                end_time, 
                meeting_details['attendees']
            )
            
            return {
                'success': True,
                'message': f"Meeting '{meeting_details['title']}' booked successfully!",
                'event_link': created_event.get('htmlLink'),
                'event_id': created_event.get('id'),
                'start_time': created_event['start']['dateTime'],
                'end_time': created_event['end']['dateTime']
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Error booking meeting: {str(e)}",
                'event_link': None
            } 

    # ======================= Reschedule Flow =======================
    def process_reschedule_command(self, command: str) -> Dict[str, Any]:
        """Parse reschedule command and find target events and new time candidates."""
        try:
            details = parse_reschedule_details(command)

            # Find events for the target date/time
            events = find_events_by_date(
                self.calendar_service, details.target_date, details.target_time
            )

            if not events:
                time_desc = f" at {details.target_time}" if details.target_time else ""
                return {
                    'success': True,
                    'message': f"No meetings found on {details.target_date}{time_desc}.",
                    'events': [],
                    'requires_confirmation': False,
                    'operation': 'reschedule',
                    'command': command,
                }

            # Parse the new desired datetime (UTC). If only new_date is provided, this will
            # be noon local converted to UTC; we'll preserve original times during confirmation.
            new_start_dt = parse_datetime_with_timezone(details.new_date, details.new_time) if (details.new_date or details.new_time) else None
            return {
                'success': True,
                'message': f"Found {len(events)} meeting(s) to reschedule.",
                'events': events,
                'new_start_dt': new_start_dt,
                'new_date': details.new_date,
                'new_time': details.new_time,
                'new_duration': details.new_duration,
                'requires_confirmation': True,
                'operation': 'reschedule',
                'command': command,
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error processing reschedule command: {str(e)}",
                'requires_confirmation': False,
                'operation': 'reschedule',
            }

    def confirm_and_reschedule(self, command: str, confirmation: str) -> Dict[str, Any]:
        if confirmation.lower() != 'yes':
            return {
                'success': False,
                'message': 'Rescheduling cancelled by user.',
                'operation': 'reschedule'
            }

        try:
            result = self.process_reschedule_command(command)
            if not result.get('success'):
                return result

            events = result.get('events', [])
            new_start_dt = result.get('new_start_dt')
            new_duration = result.get('new_duration')
            new_date_str = result.get('new_date')
            new_time_str = result.get('new_time')

            if not events:
                return {
                    'success': False,
                    'message': 'No events found to reschedule.',
                    'operation': 'reschedule',
                }

            updated_events: List[dict] = []
            for event in events:
                original_start = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                original_end = datetime.datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                duration_minutes = int((original_end - original_start).total_seconds() // 60)
                if new_duration:
                    duration_minutes = int(new_duration)

                if new_time_str is None and new_date_str:
                    # Only new date given: preserve each event's original local time on the new date
                    local_tz = get_localzone()
                    new_date_only_utc = parse_datetime_with_timezone(new_date_str, None)
                    if not new_date_only_utc:
                        start_dt = original_start
                    else:
                        original_local = original_start.astimezone(local_tz)
                        new_local_date = new_date_only_utc.astimezone(local_tz).replace(
                            hour=original_local.hour, minute=original_local.minute, second=0, microsecond=0
                        )
                        start_dt = new_local_date.astimezone(pytz.utc)
                else:
                    # New time (and optionally new date) provided: use shared datetime for all
                    start_dt = new_start_dt if new_start_dt else original_start

                end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

                updated_event = update_event(
                    self.calendar_service,
                    event['id'],
                    start_dt,
                    end_dt,
                    event.get('summary'),
                    [att['email'] for att in event.get('attendees', [])] if event.get('attendees') else None,
                )
                updated_events.append(updated_event)

            return {
                'success': True,
                'message': f"Rescheduled {len(updated_events)} meeting(s) successfully.",
                'updated_events': updated_events,
                'operation': 'reschedule',
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error rescheduling meetings: {str(e)}",
                'operation': 'reschedule',
            }

    # ======================= Cancel Flow =======================
    def process_cancel_command(self, command: str) -> Dict[str, Any]:
        try:
            details = parse_cancel_details(command)
            events = find_events_by_date(self.calendar_service, details.target_date, details.target_time)

            if not events:
                time_desc = f" at {details.target_time}" if details.target_time else ""
                return {
                    'success': True,
                    'message': f"No meetings found on {details.target_date}{time_desc}.",
                    'events': [],
                    'requires_confirmation': False,
                    'operation': 'cancel',
                    'command': command,
                }

            return {
                'success': True,
                'message': f"Found {len(events)} meeting(s) to cancel.",
                'events': events,
                'requires_confirmation': True,
                'operation': 'cancel',
                'command': command,
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error processing cancel command: {str(e)}",
                'requires_confirmation': False,
                'operation': 'cancel',
            }

    def confirm_and_cancel(self, command: str, confirmation: str) -> Dict[str, Any]:
        if confirmation.lower() != 'yes':
            return {
                'success': False,
                'message': 'Cancellation aborted by user.',
                'operation': 'cancel',
            }

        try:
            result = self.process_cancel_command(command)
            if not result.get('success'):
                return result

            events = result.get('events', [])
            if not events:
                return {
                    'success': False,
                    'message': 'No events found to cancel.',
                    'operation': 'cancel',
                }

            deleted, failed = 0, 0
            for event in events:
                # Extract attendee emails before deleting
                attendees = event.get('attendees', [])
                attendee_emails = [att.get('email') for att in attendees if att.get('email')]
                
                # Delete the event
                ok = delete_event(self.calendar_service, event['id'])
                if ok:
                    deleted += 1
                    # Send explicit cancellation email
                    email_service.send_cancellation_email(event, attendee_emails)
                else:
                    failed += 1

            msg_parts = []
            if deleted:
                msg_parts.append(f"Cancelled {deleted} meeting(s)")
            if failed:
                msg_parts.append(f"Failed to cancel {failed} meeting(s)")

            return {
                'success': failed == 0,
                'message': "; ".join(msg_parts) if msg_parts else 'No events were cancelled.',
                'operation': 'cancel',
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error cancelling meetings: {str(e)}",
                'operation': 'cancel',
            }
        
        try:
            # Re-process the command to get meeting details
            result = self.process_booking_command(command)
            
            if not result['success']:
                return result
            
            meeting_details = result['meeting_details']
            available_slots = result['available_slots']
            
            if not available_slots:
                return {
                    'success': False,
                    'message': 'No available slots found.',
                    'event_link': None
                }
            
            # Use the first available slot
            start_time = available_slots[0]['start_time']
            end_time = available_slots[0]['end_time']
            
            # Create the event
            created_event = create_event(
                self.calendar_service, 
                meeting_details['title'], 
                start_time, 
                end_time, 
                meeting_details['attendees']
            )
            
            return {
                'success': True,
                'message': f"Meeting '{meeting_details['title']}' booked successfully!",
                'event_link': created_event.get('htmlLink'),
                'event_id': created_event.get('id'),
                'start_time': created_event['start']['dateTime'],
                'end_time': created_event['end']['dateTime']
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Error booking meeting: {str(e)}",
                'event_link': None
            } 