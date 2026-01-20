# AI Booking Agent

This project is a backend-only AI Booking Agent that can schedule, reschedule, and cancel meetings based on natural language commands.

## Features

### Booking Meetings
Schedule new meetings with natural language commands:
```
Book a meeting with tejalrathi2510@gmail.com next Friday at 3pm for 30 minutes to discuss progress.
```

### Rescheduling Meetings
Reschedule existing meetings with flexible date/time matching:

**Reschedule all meetings on a specific date:**
```
Reschedule all meetings of 8th august 2025 to 9th august at 1pm
```

**Reschedule all meetings to a new date while preserving original times:**
```
Reschedule all meetings of 8th august 2025 to 9th august 2025
```
*Note: When rescheduling multiple meetings, you can choose to:*
*- Preserve original times on new date (e.g., 5am stays 5am, 8pm stays 8pm)*
*- Cancel rescheduling*

**Reschedule a specific meeting by time:**
```
Reschedule meeting of 8th august which is at 8 am to 7 pm
```

**Reschedule with new duration:**
```
Reschedule my meeting on next friday at 2pm to monday at 10am for 45 minutes
```

### Cancelling Meetings
Cancel meetings with flexible date/time matching:

**Cancel a specific meeting by time:**
```
Cancel my meeting which is at 8pm on 15th august 2025
```

**Cancel all meetings on a specific date:**
```
Cancel all my meetings which are on 16th august 2025
```

**Cancel meetings on relative dates:**
```
Cancel all meetings next friday
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up Google Calendar API Credentials
- Follow the [Google Calendar API Python Quickstart](https://developers.google.com/calendar/api/quickstart/python) to enable the API and download your `credentials.json`.
- Place the `credentials.json` file in the root of the project directory.
- When you run the application for the first time, you will be prompted to authorize access to your Google Calendar. A `token.json` file will be created to store your access and refresh tokens.
- **Important:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Navigate to **APIs & Services > OAuth consent screen**.
    - Under **Test users**, add your email address (e.g., `tejal25@gmail.com`) as a test user. 

### 3. Set up Groq API Key
- Create a `.env` file in the root of the project.
- Add your Groq API key to the `.env` file as follows:
```
GROQ_API_KEY=your_groq_api_key
```

## Running the Application
```bash
python main.py
```

Then, enter commands like:
- **Booking:** "Book a meeting with tejalrathi2510@gmail.com next Friday at 3pm for 30 minutes to discuss progress."
- **Rescheduling:** "Reschedule all meetings of 8th august 2025 to 9th august"
- **Cancelling:** "Cancel my meeting which is at 8pm on 15th august 2025"

## How It Works

The AI agent uses natural language processing to understand your commands and:

1. **Determines the command type** (book, reschedule, or cancel)
2. **Extracts relevant details** from your natural language input
3. **Finds matching events** (for reschedule/cancel operations)
4. **Performs the requested action** with confirmation prompts
5. **Provides feedback** on the success or failure of operations

The system supports flexible date/time formats including:
- Relative dates: "next friday", "tomorrow", "next week"
- Specific dates: "8th august 2025", "15th december"
- Time formats: "8am", "8 pm", "14:30", "2:30pm" 