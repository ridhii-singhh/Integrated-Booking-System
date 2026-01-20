# Booking Agent API

A FastAPI-based REST API that provides natural language meeting booking capabilities using Google Calendar integration and LLM-powered command parsing.

## Features

- **Natural Language Processing**: Book meetings using plain English commands
- **Google Calendar Integration**: Check availability and create events
- **Smart Slot Finding**: Automatically find alternative time slots when requested time is unavailable
- **Interactive Confirmation**: Two-step booking process with confirmation
- **Timezone Handling**: Automatic timezone conversion and handling

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Google Cloud Project** with Calendar API enabled
3. **Groq API Key** for LLM processing

### Installation

1. **Clone or navigate to the API folder:**
   ```bash
   cd api
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Calendar credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Download the JSON file and rename it to `credentials.json`
   - Place `credentials.json` in the `Booking_agent_api` folder

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` (if available)
   - Update `.env` with your configuration:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   API_HOST=127.0.0.1
   API_PORT=8000
   API_DEBUG=true
   ```

5. **Run the API:**
   ```bash
   python run_server.py
   ```

6. **Access the API:**
   - **API Documentation:** http://localhost:8000/docs
   - **Alternative Docs:** http://localhost:8000/redoc
   - **Health Check:** http://localhost:8000/api/v1/health

## API Endpoints

### 1. Book Meeting
**POST** `/api/v1/book`

Book a meeting using natural language command.

**Request Body:**
```json
{
  "command": "book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins"
}
```

**Response:**
```json
{
  "success": true,
  "message": "The time slot is available. Do you want to book the meeting 'progress meeting' on 2024-01-16 17:00?",
  "meeting_details": {
    "title": "progress meeting",
    "attendees": ["tejalr2125@gmail.com"],
    "date": "next tuesday",
    "time": "17:00",
    "duration": 30
  },
  "available_slots": [
    {
      "start_time": "2024-01-16T17:00:00Z",
      "end_time": "2024-01-16T17:30:00Z",
      "display_time": "2024-01-16 17:00",
      "is_available": true
    }
  ],
  "requires_confirmation": true
}
```

### 2. Confirm Booking
**POST** `/api/v1/confirm`

Confirm and finalize the booking after checking availability.

**Request Body:**
```json
{
  "command": "book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins",
  "confirmation": "yes"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Meeting 'progress meeting' booked successfully!",
  "event_link": "https://calendar.google.com/calendar/event?eid=...",
  "requires_confirmation": false
}
```

### 3. Reschedule (Preview)
**POST** `/api/v1/reschedule`

Preview meetings to be rescheduled, parsed from a natural language command.

Request Body:
```json
{
  "command": "Reschedule all meetings of 8th august 2025 to 9th august at 1pm"
}
```

Response (example):
```json
{
  "success": true,
  "message": "Found 2 meeting(s) to reschedule.",
  "events": [ { "id": "...", "summary": "...", "start": {"dateTime": "..."}, "end": {"dateTime": "..."} } ],
  "requires_confirmation": true,
  "operation": "reschedule"
}
```

### 4. Reschedule (Confirm)
**POST** `/api/v1/reschedule/confirm`

Confirm and perform the rescheduling operation.

Request Body:
```json
{
  "command": "Reschedule all meetings of 8th august 2025 to 9th august at 1pm",
  "confirmation": "yes"
}
```

### 5. Cancel (Preview)
**POST** `/api/v1/cancel`

Preview meetings to be cancelled, parsed from a natural language command.

Request Body:
```json
{
  "command": "Cancel my meeting which is at 8pm on 15th august 2025"
}
```

### 6. Cancel (Confirm)
**POST** `/api/v1/cancel/confirm`

Confirm and perform the cancellation operation.

Request Body:
```json
{
  "command": "Cancel my meeting which is at 8pm on 15th august 2025",
  "confirmation": "yes"
}
```

### 7. Health Check
**GET** `/api/v1/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123456",
  "service": "Booking Agent API"
}
```

## Command Examples

The API supports various natural language formats:

### Basic Booking
```
"book a meeting with john@example.com tomorrow at 2pm for 1 hour"
```

### With Multiple Attendees
```
"schedule a team sync with alice@company.com, bob@company.com on friday 3:30pm for 45 minutes"
```

### Relative Dates
```
"book a call with client@business.com next monday 10am for 30 mins"
```

### Time Formats
- 12-hour: `"5.00 pm"`, `"3:30pm"`, `"10 AM"`
- 24-hour: `"17:00"`, `"14:30"`

### Duration Formats
- Minutes: `"30 mins"`, `"45 minutes"`
- Hours: `"1 hour"`, `"2 hours"`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key for LLM processing | Required |
| `API_HOST` | Host to bind the server to | `127.0.0.1` |
| `API_PORT` | Port to run the server on | `8000` |
| `API_DEBUG` | Enable debug mode and auto-reload | `true` |

### Google Calendar Setup

1. **Enable Google Calendar API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project
   - Go to "APIs & Services" → "Library"
   - Search for "Google Calendar API" and enable it

2. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file and rename to `credentials.json`

3. **First Run Authentication:**
   - On first run, the API will open a browser window
   - Log in to your Google account
   - Grant calendar permissions
   - A `token.json` file will be created for future use

## Project Structure

```
api/
├── __init__.py              
├── app.py                   
├── endpoints.py           
├── models.py         
├── booking_service.py     
├── llm_service.py        
├── calendar_service.py    
├── run_server.py   
├── requirements.txt  
├── .env              
├── credentials.json     
└── README.md     
```

## Development

### Running in Development Mode

```bash
python run_server.py
```

The server will run with auto-reload enabled, so changes to the code will automatically restart the server.

### Running with uvicorn directly

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```


## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input data
- **500 Internal Server Error**: Server-side errors
- **Detailed error messages** for debugging

Common error scenarios:
- Invalid date/time format
- Missing required fields
- Google Calendar API errors
- LLM processing errors

## Troubleshooting

### Common Issues

1. **"Token has been expired or revoked"**
   - Delete `token.json` file
   - Restart the API
   - Re-authenticate with Google

2. **"credentials.json not found"**
   - Download credentials from Google Cloud Console
   - Place in the `api` folder

3. **"GROQ_API_KEY not set"**
   - Add your Groq API key to `.env` file

4. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.8+ required)


