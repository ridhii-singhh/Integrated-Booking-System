from typing import TypedDict, Annotated, Literal
from src.llm_tools import parse_meeting_details, MeetingDetails, parse_reschedule_details, parse_cancel_details, parse_command_type, RescheduleDetails, CancelDetails
from src.calendar_tools import get_calendar_service, check_availability, find_next_available_slots, create_event, find_events_by_date, update_event, delete_event, parse_datetime_with_timezone
import datetime
import dateparser
import pytz
from tzlocal import get_localzone
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    command: str
    command_type: str
    meeting_details: MeetingDetails
    reschedule_details: RescheduleDetails
    cancel_details: CancelDetails
    calendar_service: object
    available_slots: list[datetime.datetime]
    found_events: list
    booking_confirmed: bool
    reschedule_confirmed: bool
    cancel_confirmed: bool
    final_response: str

def parse_command_node(state: AgentState):
    # First determine the command type
    command_type_result = parse_command_type(state["command"])
    state["command_type"] = command_type_result.command_type
    state["calendar_service"] = get_calendar_service()
    
    # Parse details based on command type
    if state["command_type"] == "book":
        details = parse_meeting_details(state["command"])
        state["meeting_details"] = details
    elif state["command_type"] == "reschedule":
        details = parse_reschedule_details(state["command"])
        state["reschedule_details"] = details
    elif state["command_type"] == "cancel":
        details = parse_cancel_details(state["command"])
        state["cancel_details"] = details
    
    return state

def route_command_node(state: AgentState):
    """Route to the appropriate handler based on command type."""
    # This function just updates the state, routing is handled by conditional edges
    return state

def should_route_to_booking(state: AgentState) -> Literal["ask_missing_info_node", "find_events_node"]:
    """Determine routing based on command type."""
    if state["command_type"] == "book":
        return "ask_missing_info_node"
    elif state["command_type"] in ["reschedule", "cancel"]:
        return "find_events_node"
    else:
        state["final_response"] = "I couldn't understand the command type. Please try again."
        return "ask_missing_info_node"

def ask_missing_info_node(state: AgentState):
    details = state["meeting_details"]
    if not all([details.title, details.attendees, details.date, details.time, details.duration]):
        # In a real scenario, you'd have a more sophisticated way to ask the user.
        # Here, we'll just print and exit if info is missing.
        missing_fields = [k for k, v in details.dict().items() if not v]
        state["final_response"] = f"I am missing the following information: {', '.join(missing_fields)}. Please provide it."
        return state
    
    return state
    
def check_availability_node(state: AgentState):
    details = state["meeting_details"]
    service = state["calendar_service"]
    
    # Use dateparser to handle relative dates
    parsed_date = dateparser.parse(details.date)

    if not parsed_date:
        state["final_response"] = f"I couldn't understand the date: '{details.date}'. Please try again with a clearer date format (e.g., 'YYYY-MM-DD', 'tomorrow', 'next Friday')."
        return state
    
    # Create a timezone-aware datetime object based on the user's local timezone
    start_time_str = f"{parsed_date.strftime('%Y-%m-%d')}T{details.time}"
    naive_start_time = datetime.datetime.fromisoformat(start_time_str)
    
    local_tz = get_localzone()
    # Use .replace(tzinfo=) which is compatible with all timezone objects
    local_start_time = naive_start_time.replace(tzinfo=local_tz)
    
    # Convert to UTC for all internal processing and API calls
    utc_start_time = local_start_time.astimezone(pytz.utc)

    end_time = utc_start_time + datetime.timedelta(minutes=details.duration)
    
    is_available, busy_slots = check_availability(service, utc_start_time, end_time, details.attendees)
    
    if not is_available:
        next_slots = find_next_available_slots(service, utc_start_time, details.duration, details.attendees)
        state["available_slots"] = next_slots
        return state
        
    state["available_slots"] = [utc_start_time]
    return state

def confirm_and_book_node(state: AgentState):
    if len(state["available_slots"]) > 1:
        slots_str = ", ".join([slot.strftime('%Y-%m-%d %H:%M') for slot in state["available_slots"]])
        confirmation = input(f"The requested time is unavailable. Would you like to book one of the next available slots: {slots_str}? (yes/no): ")
        if confirmation.lower() == 'yes':
            chosen_slot_str = input(f"Please choose a slot from the list: ")
            chosen_slot = datetime.datetime.strptime(chosen_slot_str, '%Y-%m-%d %H:%M')
            state["available_slots"] = [chosen_slot]
            state["booking_confirmed"] = True
        else:
            state["booking_confirmed"] = False
            state["final_response"] = "Booking cancelled."
            return state
    else:
        confirmation = input(f"The time is available. Do you want to book the meeting? (yes/no): ")
        state["booking_confirmed"] = confirmation.lower() == 'yes'

    if state["booking_confirmed"]:
        details = state["meeting_details"]
        service = state["calendar_service"]
        start_time = state["available_slots"][0] # This is a UTC datetime object
        end_time = start_time + datetime.timedelta(minutes=details.duration)
        
        created_event = create_event(service, details.title, start_time, end_time, details.attendees)
        event_link = created_event.get('htmlLink')

        # Convert back to local time for display purposes
        local_tz = get_localzone()
        display_time = start_time.astimezone(local_tz)

        state["final_response"] = (
            f"Meeting '{details.title}' booked successfully!\n"
            f"Time: {display_time.strftime('%Y-%m-%d %H:%M %Z')}\n"
            f"Attendees: {', '.join(details.attendees)}\n"
            f"You can view the event here: {event_link}"
        )
    else:
        state["final_response"] = "Booking cancelled."

    return state

def find_events_node(state: AgentState):
    """Find events based on the command type (reschedule or cancel)."""
    service = state["calendar_service"]
    
    if state["command_type"] == "reschedule":
        details = state["reschedule_details"]
        target_date = details.target_date
        target_time = details.target_time
    else:  # cancel
        details = state["cancel_details"]
        target_date = details.target_date
        target_time = details.target_time
    
    # Find events matching the criteria
    events = find_events_by_date(service, target_date, target_time)
    state["found_events"] = events
    
    if not events:
        time_desc = f" at {target_time}" if target_time else ""
        state["final_response"] = f"No meetings found on {target_date}{time_desc}."
        return state
    
    # Display found events
    events_info = []
    for i, event in enumerate(events, 1):
        start_time = event['start'].get('dateTime')
        if start_time:
            # Convert UTC to local time for display
            utc_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            local_tz = get_localzone()
            local_dt = utc_dt.astimezone(local_tz)
            time_str = local_dt.strftime('%Y-%m-%d %H:%M %Z')
        else:
            time_str = "All day"
        
        title = event.get('summary', 'Untitled')
        events_info.append(f"{i}. {title} - {time_str}")
    
    print(f"Found {len(events)} meeting(s):")
    for info in events_info:
        print(info)
    
    return state

def reschedule_events_node(state: AgentState):
    """Handle rescheduling of found events."""
    events = state["found_events"]
    details = state["reschedule_details"]
    service = state["calendar_service"]
    
    if not events:
        state["final_response"] = "No events to reschedule."
        return state
    
    # Parse new date and time
    if details.new_time:
        new_datetime = parse_datetime_with_timezone(details.new_date, details.new_time)
        if not new_datetime:
            state["final_response"] = f"I couldn't understand the new date/time: '{details.new_date} {details.new_time}'. Please try again."
            return state
    else:
        # If no new time specified, we can still reschedule by preserving original times
        # Just parse the new date
        new_datetime = parse_datetime_with_timezone(details.new_date, None)
        if not new_datetime:
            state["final_response"] = f"I couldn't understand the new date: '{details.new_date}'. Please try again."
            return state
    
    # Ask for confirmation and scheduling preference
    event_count = len(events)
    if event_count == 1:
        confirmation = input(f"Do you want to reschedule this meeting? (yes/no): ")
        state["reschedule_confirmed"] = confirmation.lower() == 'yes'
        same_time = True
        preserve_times = False
    else:
        print(f"Found {event_count} meetings to reschedule.")
        if details.new_time:
            print("Options:")
            print("1. Reschedule all to the same time (may cause conflicts)")
            print("2. Stagger meetings sequentially (each meeting starts after the previous one ends + 15min buffer)")
            print("3. Preserve original times on new date (e.g., 5am stays 5am, 8pm stays 8pm)")
            print("4. Cancel rescheduling")
        else:
            print("Options:")
            print("1. Preserve original times on new date (e.g., 5am stays 5am, 8pm stays 8pm)")
            print("2. Cancel rescheduling")
        
        if details.new_time:
            choice = input("Enter your choice (1/2/3/4): ").strip()
            
            if choice == "1":
                confirmation = input(f"Do you want to reschedule all {event_count} meetings to the same time? (yes/no): ")
                state["reschedule_confirmed"] = confirmation.lower() == 'yes'
                same_time = True
                preserve_times = False
            elif choice == "2":
                confirmation = input(f"Do you want to reschedule all {event_count} meetings sequentially? (yes/no): ")
                state["reschedule_confirmed"] = confirmation.lower() == 'yes'
                same_time = False
                preserve_times = False
            elif choice == "3":
                confirmation = input(f"Do you want to reschedule all {event_count} meetings to the new date while preserving their original times? (yes/no): ")
                state["reschedule_confirmed"] = confirmation.lower() == 'yes'
                same_time = False
                preserve_times = True
            else:
                state["reschedule_confirmed"] = False
        else:
            choice = input("Enter your choice (1/2): ").strip()
            
            if choice == "1":
                confirmation = input(f"Do you want to reschedule all {event_count} meetings to the new date while preserving their original times? (yes/no): ")
                state["reschedule_confirmed"] = confirmation.lower() == 'yes'
                same_time = False
                preserve_times = True
            else:
                state["reschedule_confirmed"] = False
    
    if not state["reschedule_confirmed"]:
        state["final_response"] = "Rescheduling cancelled."
        return state
    
    # Reschedule each event
    successful_reschedules = []
    failed_reschedules = []
    
    # Reschedule each event
    successful_reschedules = []
    failed_reschedules = []
    
    base_datetime = new_datetime
    current_time = base_datetime
    
    for i, event in enumerate(events):
        try:
            # Calculate new end time
            start_time = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds() / 60
            
            # Use new duration if provided, otherwise keep original
            if details.new_duration:
                duration = details.new_duration
            
            # Calculate start time based on scheduling preference
            if same_time:
                # All events at the same time (may cause conflicts)
                event_start_time = base_datetime
            elif preserve_times:
                # Preserve original times on new date
                # Extract the time from the original event (convert from UTC to local first)
                original_start_utc = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                local_tz = get_localzone()
                original_start_local = original_start_utc.astimezone(local_tz)
                original_hour = original_start_local.hour
                original_minute = original_start_local.minute
                
                # Create new datetime with same time but new date
                # Parse the new date and convert to local timezone
                new_date_utc = parse_datetime_with_timezone(details.new_date, None)
                new_date_local = new_date_utc.astimezone(local_tz)
                new_date_only = new_date_local.replace(hour=0, minute=0, second=0, microsecond=0)
                event_start_time_local = new_date_only.replace(hour=original_hour, minute=original_minute)
                
                # Convert back to UTC for the API
                event_start_time = event_start_time_local.astimezone(pytz.utc)
            else:
                # Stagger events sequentially - each meeting starts after the previous one ends
                if i == 0:
                    # First meeting starts at the specified time
                    event_start_time = base_datetime
                else:
                    # Subsequent meetings start after the previous one ends
                    event_start_time = current_time
            
            new_end_time = event_start_time + datetime.timedelta(minutes=duration)
            
            # Update current_time for the next meeting (add 15-minute buffer)
            if not preserve_times:
                current_time = new_end_time + datetime.timedelta(minutes=15)
            
            # Update the event
            updated_event = update_event(
                service, 
                event['id'], 
                event_start_time, 
                new_end_time,
                event.get('summary'),
                [attendee['email'] for attendee in event.get('attendees', [])]
            )
            
            successful_reschedules.append(event.get('summary', 'Untitled'))
            
        except Exception as e:
            failed_reschedules.append(event.get('summary', 'Untitled'))
    
    # Prepare response with timing details
    response_parts = []
    if successful_reschedules:
        if len(successful_reschedules) == 1:
            response_parts.append(f"Successfully rescheduled: {successful_reschedules[0]}")
        else:
            if same_time:
                response_parts.append(f"Successfully rescheduled {len(successful_reschedules)} meetings to the same time")
            elif preserve_times:
                response_parts.append(f"Successfully rescheduled {len(successful_reschedules)} meetings to the new date while preserving their original times")
            else:
                response_parts.append(f"Successfully rescheduled {len(successful_reschedules)} meetings sequentially")
    
    if failed_reschedules:
        response_parts.append(f"Failed to reschedule: {', '.join(failed_reschedules)}")
    
    state["final_response"] = "\n".join(response_parts) if response_parts else "No events were rescheduled."
    return state

def cancel_events_node(state: AgentState):
    """Handle cancellation of found events."""
    events = state["found_events"]
    service = state["calendar_service"]
    
    if not events:
        state["final_response"] = "No events to cancel."
        return state
    
    # Ask for confirmation
    event_count = len(events)
    action = "cancel" if event_count == 1 else f"cancel all {event_count} meetings"
    confirmation = input(f"Do you want to {action}? (yes/no): ")
    state["cancel_confirmed"] = confirmation.lower() == 'yes'
    
    if not state["cancel_confirmed"]:
        state["final_response"] = "Cancellation cancelled."
        return state
    
    # Cancel each event
    successful_cancellations = []
    failed_cancellations = []
    
    for event in events:
        try:
            success = delete_event(service, event['id'])
            if success:
                successful_cancellations.append(event.get('summary', 'Untitled'))
            else:
                failed_cancellations.append(event.get('summary', 'Untitled'))
        except Exception as e:
            failed_cancellations.append(event.get('summary', 'Untitled'))
    
    # Prepare response
    response_parts = []
    if successful_cancellations:
        response_parts.append(f"Successfully cancelled: {', '.join(successful_cancellations)}")
    if failed_cancellations:
        response_parts.append(f"Failed to cancel: {', '.join(failed_cancellations)}")
    
    state["final_response"] = "\n".join(response_parts) if response_parts else "No events were cancelled."
    return state

def should_ask_for_info(state: AgentState) -> Literal["ask_missing_info_node", "check_availability_node"]:
    details = state["meeting_details"]
    if not all([details.title, details.attendees, details.date, details.time, details.duration]):
        return "ask_missing_info_node"
    return "check_availability_node"

def did_availability_check_succeed(state: AgentState) -> Literal["confirm_and_book_node", END]:
    """
    Determines the next step after checking availability.
    If date parsing failed, the check is skipped and we end.
    Otherwise, we proceed to confirmation.
    """
    if "available_slots" in state:
        return "confirm_and_book_node"
    return END

def should_proceed_with_events(state: AgentState) -> Literal["reschedule_events_node", "cancel_events_node", END]:
    """Determine next step after finding events."""
    if not state.get("found_events"):
        return END
    
    if state["command_type"] == "reschedule":
        return "reschedule_events_node"
    elif state["command_type"] == "cancel":
        return "cancel_events_node"
    else:
        return END

workflow = StateGraph(AgentState)
workflow.add_node("parse_command_node", parse_command_node)
workflow.add_node("route_command_node", route_command_node)
workflow.add_node("ask_missing_info_node", ask_missing_info_node)
workflow.add_node("check_availability_node", check_availability_node)
workflow.add_node("confirm_and_book_node", confirm_and_book_node)
workflow.add_node("find_events_node", find_events_node)
workflow.add_node("reschedule_events_node", reschedule_events_node)
workflow.add_node("cancel_events_node", cancel_events_node)

workflow.set_entry_point("parse_command_node")
workflow.add_edge("parse_command_node", "route_command_node")
workflow.add_conditional_edges("route_command_node", should_route_to_booking, {
    "ask_missing_info_node": "ask_missing_info_node",
    "find_events_node": "find_events_node"
})

workflow.add_conditional_edges("ask_missing_info_node", should_ask_for_info, {
    "ask_missing_info_node": "ask_missing_info_node",
    "check_availability_node": "check_availability_node"
})

workflow.add_conditional_edges("check_availability_node", did_availability_check_succeed, {
    "confirm_and_book_node": "confirm_and_book_node",
    END: END
})

workflow.add_edge("confirm_and_book_node", END)

workflow.add_conditional_edges("find_events_node", should_proceed_with_events, {
    "reschedule_events_node": "reschedule_events_node",
    "cancel_events_node": "cancel_events_node",
    END: END
})

workflow.add_edge("reschedule_events_node", END)
workflow.add_edge("cancel_events_node", END)

app = workflow.compile() 