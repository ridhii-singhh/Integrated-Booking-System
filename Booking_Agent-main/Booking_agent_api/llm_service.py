from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import List, Optional, Literal

load_dotenv()

class MeetingDetails(BaseModel):
    title: str = Field(..., description="The title of the meeting.")
    attendees: List[str] = Field(..., description="The email addresses of the attendees.")
    date: str = Field(..., description="The date of the meeting. This can be a relative date like 'today' or 'next Friday'.")
    time: str = Field(..., description="The time of the meeting in HH:MM 24-hour format.")
    duration: int = Field(..., description="The duration of the meeting in minutes.")


class RescheduleDetails(BaseModel):
    operation: Literal["reschedule"] = Field(..., description="The operation type.")
    target_date: str = Field(..., description="The date to find meetings on (e.g., '8th august 2025', 'next friday').")
    target_time: Optional[str] = Field(None, description="The specific time to find (e.g., '8 am'). If not provided, all meetings on that date will be considered.")
    new_date: str = Field(..., description="The new date for the meeting(s).")
    new_time: Optional[str] = Field(None, description="The new time for the meeting(s) in HH:MM 24-hour format. If not provided, keep the original time.")
    new_duration: Optional[int] = Field(None, description="The new duration in minutes. If not provided, keep the original duration.")


class CancelDetails(BaseModel):
    operation: Literal["cancel"] = Field(..., description="The operation type.")
    target_date: str = Field(..., description="The date to find meetings on (e.g., '15th august 2025', 'next friday').")
    target_time: Optional[str] = Field(None, description="The specific time to find (e.g., '8pm'). If not provided, all meetings on that date will be cancelled.")


class CommandType(BaseModel):
    command_type: Literal["book", "reschedule", "cancel"] = Field(..., description="The type of command.")

def get_llm():
    return ChatGroq(temperature=0, model_name="llama3-70b-8192", api_key=os.environ.get("GROQ_API_KEY"))

def get_parsing_chain():
    prompt = PromptTemplate.from_template(
        """
        You are an expert at extracting meeting details from a natural language command.
        Your task is to extract the title, attendees, date, time, and duration from the user's command.
        
        - Do NOT resolve relative dates like "today", "tomorrow", or "next Friday". Return the original text.
        - The time must be in 'HH:MM' 24-hour format.
        - Convert 12-hour format to 24-hour format (e.g., "5.00 pm" becomes "17:00")
        - Extract duration in minutes

        User command: {command}
        """
    )
    
    llm = get_llm()
    
    return prompt | llm.with_structured_output(MeetingDetails)

def parse_meeting_details(command):
    """Parse natural language command into structured meeting details"""
    try:
        chain = get_parsing_chain()
        return chain.invoke({"command": command})
    except Exception as e:
        raise ValueError(f"Failed to parse command: {str(e)}") 


def get_command_type_chain():
    prompt = PromptTemplate.from_template(
        """
        You are an expert at determining the type of command from natural language.
        Determine if the user wants to:
        1. "book" - schedule a new meeting
        2. "reschedule" - change the time/date of existing meeting(s)
        3. "cancel" - cancel existing meeting(s)

        Look for keywords like:
        - Book, schedule, create, set up → book
        - Reschedule, move, change time, postpone → reschedule
        - Cancel, delete, remove → cancel

        User command: {command}
        """
    )
    llm = get_llm()
    return prompt | llm.with_structured_output(CommandType)


def get_reschedule_parsing_chain():
    prompt = PromptTemplate.from_template(
        """
        You are an expert at extracting reschedule details from natural language commands.
        Extract the target date/time to find meetings and the new date/time to reschedule them to.

        - Do NOT resolve relative dates. Return the original text exactly as provided.
        - The new time must be in 'HH:MM' 24-hour format.
        - If no specific time is mentioned for finding meetings, leave target_time as null.
        - If no new time is mentioned for the new date, leave new_time as null.
        - If no new duration is mentioned, leave new_duration as null.
        - IMPORTANT: Preserve the full date text including year if provided.
        - Examples:
          * "Reschedule all meetings of 8th august 2025 to 9th august" → target_date = "8th august 2025", new_date = "9th august", new_time = null
          * "Reschedule meeting of 8th august 2025 which is at 8 am to 7 pm" → target_date = "8th august 2025", target_time = "8 am", new_date = "8th august 2025", new_time = "19:00"
          * "Reschedule my meeting on next friday at 2pm to monday at 10am" → target_date = "next friday", target_time = "2pm", new_date = "monday", new_time = "10:00"

        User command: {command}
        """
    )
    llm = get_llm()
    return prompt | llm.with_structured_output(RescheduleDetails)


def get_cancel_parsing_chain():
    prompt = PromptTemplate.from_template(
        """
        You are an expert at extracting cancel details from natural language commands.
        Extract the target date/time to find meetings to cancel.

        - Do NOT resolve relative dates. Return the original text.
        - If no specific time is mentioned, leave target_time as null.

        User command: {command}
        """
    )
    llm = get_llm()
    return prompt | llm.with_structured_output(CancelDetails)


def parse_reschedule_details(command: str) -> RescheduleDetails:
    try:
        chain = get_reschedule_parsing_chain()
        return chain.invoke({"command": command})
    except Exception as e:
        raise ValueError(f"Failed to parse reschedule command: {str(e)}")


def parse_cancel_details(command: str) -> CancelDetails:
    try:
        chain = get_cancel_parsing_chain()
        return chain.invoke({"command": command})
    except Exception as e:
        raise ValueError(f"Failed to parse cancel command: {str(e)}")


def parse_command_type(command: str) -> CommandType:
    try:
        chain = get_command_type_chain()
        return chain.invoke({"command": command})
    except Exception as e:
        raise ValueError(f"Failed to determine command type: {str(e)}")