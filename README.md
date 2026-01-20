# 🚀 Integrated Booking & Calling System

A comprehensive end-to-end system that seamlessly connects Google Calendar-based booking with Twilio-powered voice calls for meeting confirmations and management.

## 🌟 Features

### 📅 Booking Agent Integration
- **Natural Language Booking**: Book meetings using conversational commands
- **Google Calendar Sync**: Automatic calendar integration
- **Smart Scheduling**: Conflict detection and resolution
- **Meeting Management**: Book, reschedule, and cancel meetings

### 📞 Calling Agent Integration
- **Automated Confirmation Calls**: Voice confirmation for bookings
- **Real-time Voice Processing**: AI-powered conversation handling
- **Context-Aware Responses**: Tailored responses based on action type
- **Multi-language Support**: Customizable voice and language settings

### 🔧 Orchestration Features
- **Unified Web Interface**: Modern, responsive UI for all operations
- **Transaction Tracking**: Complete audit trail of all actions
- **State Management**: Reliable state persistence across services
- **Webhook Integration**: Real-time updates and notifications

## 🏗️ Architecture

```mermaid
graph TD
    A[Web UI] --> B[Orchestrator]
    B --> C[Booking Agent]
    B --> D[Enhanced Calling Agent]
    C --> E[Google Calendar API]
    D --> F[Twilio API]
    B --> G[State Manager]
    G --> H[Database]
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Account (for Calendar API)
- Twilio Account (for voice calls)
- ngrok (for webhook tunneling)

### 1. Clone and Setup

```bash
cd /Users/Documents/Project/integrated_system
python setup.py
```

### 2. Configure Environment

```bash
# Copy template and edit with your credentials
cp .env.template .env
nano .env  # Edit with your actual credentials
```

### 3. Get Required Credentials

#### Google Calendar Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Calendar API
4. Create credentials (OAuth 2.0 Client ID)
5. Add your redirect URI: `http://localhost:8080/auth/google/callback`

#### Twilio Setup
1. Sign up at [Twilio](https://www.twilio.com/)
2. Get your Account SID and Auth Token
3. Purchase a phone number
4. Set up webhook URLs (use ngrok)

### 4. Setup ngrok (for Twilio webhooks)

```bash
# Install ngrok
npm install -g ngrok
# or download from https://ngrok.com/

# Start tunnel
ngrok http 8001

# Copy the HTTPS URL to your .env file as TWILIO_WEBHOOK_BASE_URL
```

### 5. Start All Services

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

### 6. Access the System

Open your browser and navigate to: `http://localhost:8080`

## 📖 Detailed Setup Guide

### Environment Configuration

Edit your `.env` file with the following required values:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_from_cloud_console
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Security
SECRET_KEY=your-super-secret-key-for-jwt-tokens
```

### Service Ports

- **Orchestrator**: `http://localhost:8080` (Main UI)
- **Booking Agent**: `http://localhost:8000` (API)
- **Enhanced Calling Agent**: `http://localhost:8001` (API)

## 🎯 Usage Examples

### 1. Book a Meeting with Call Confirmation

```javascript
// Via Web UI or API
{
  "booking_command": "Book a progress meeting with john@example.com tomorrow at 2 PM for 1 hour",
  "trigger_call": true,
  "user_phone": "+1234567890",
  "call_delay_minutes": 1
}
```

**System Flow:**
1. 📅 Processes booking via Booking Agent
2. 📞 Triggers confirmation call via Calling Agent
3. 🎤 User confirms/denies via voice
4. ✅ Updates calendar based on response

### 2. Reschedule with Notification

```javascript
{
  "reschedule_command": "Move my meeting with Sarah from Friday 3 PM to Monday 10 AM",
  "trigger_call": true,
  "user_phone": "+1234567890"
}
```

### 3. Cancel Meeting

```javascript
{
  "cancel_command": "Cancel my meeting with the marketing team on Tuesday",
  "trigger_call": true,
  "user_phone": "+1234567890"
}
```

## 🔧 API Reference

### Orchestrator Endpoints

#### Book Meeting
```http
POST /api/v1/integrated-booking
Content-Type: application/json

{
  "booking_command": "string",
  "trigger_call": true,
  "user_phone": "+1234567890",
  "call_delay_minutes": 1
}
```

#### Reschedule Meeting
```http
POST /api/v1/integrated-reschedule
Content-Type: application/json

{
  "reschedule_command": "string",
  "trigger_call": true,
  "user_phone": "+1234567890"
}
```

#### Cancel Meeting
```http
POST /api/v1/integrated-cancel
Content-Type: application/json

{
  "cancel_command": "string",
  "trigger_call": true,
  "user_phone": "+1234567890"
}
```

#### Get Transaction Status
```http
GET /api/v1/transaction/{transaction_id}
```

#### List Transactions
```http
GET /api/v1/transactions?limit=50&offset=0
```

### Enhanced Calling Agent Endpoints

#### Trigger Custom Call
```http
POST /api/v1/trigger-call
Content-Type: application/json

{
  "target_phone": "+1234567890",
  "call_script": "Custom message script",
  "context": {
    "transaction_id": "uuid",
    "action_type": "confirmation"
  }
}
```

#### Control Active Call
```http
POST /api/v1/call-control
Content-Type: application/json

{
  "call_sid": "twilio_call_sid",
  "action": "status|update|cancel",
  "message": "Optional message for update"
}
```

## 🛠️ Development

### Project Structure

```
integrated_system/
├── orchestrator/           # Main coordination service
│   ├── main.py            # FastAPI application
│   ├── models.py          # Pydantic models
│   ├── config.py          # Configuration management
│   ├── services/          # Service clients
│   │   ├── booking_service.py
│   │   ├── calling_service.py
│   │   └── state_manager.py
│   └── static/            # Web UI files
│       └── index.html
├── enhanced_calling_agent/ # Enhanced calling service
│   └── app.py             # Extended calling agent
├── .env.template          # Environment template
├── setup.py              # Setup script
├── start.sh              # Linux/Mac startup
├── start.bat             # Windows startup
└── README.md             # This file
```

### Running in Development Mode

```bash
# Start each service separately for development

# Terminal 1 - Booking Agent
cd ../Booking_Agent-main/Booking_agent_api
python app.py

# Terminal 2 - Enhanced Calling Agent
cd enhanced_calling_agent
python app.py

# Terminal 3 - Orchestrator
cd orchestrator
python main.py
```

### Adding Custom Features

1. **Custom Call Scripts**: Modify `config.py` call script templates
2. **Additional APIs**: Extend `main.py` with new endpoints
3. **UI Enhancements**: Modify `static/index.html`
4. **New Integrations**: Add service clients in `services/`

## 📊 Monitoring & Logs

### Health Checks

- **System Health**: `GET /api/v1/health`
- **Transaction Stats**: `GET /api/v1/transactions`
- **Service Status**: Each service has `/health` endpoint

### Logging

Logs are available in:
- **Orchestrator**: `orchestrator/logs/`
- **Calling Agent**: `enhanced_calling_agent/logs/`
- **Console Output**: Real-time logs in terminal

## 🔒 Security Considerations

### Production Deployment

1. **Change Default Secrets**:
   ```bash
   SECRET_KEY=your-strong-production-secret
   ```

2. **Use HTTPS**:
   ```bash
   TWILIO_WEBHOOK_BASE_URL=https://your-domain.com
   ```

3. **Database Security**:
   ```bash
   DATABASE_URL=postgresql://user:pass@host/db
   ```

4. **Rate Limiting**: Enabled by default in production

### Authentication

- **Google OAuth**: Secure calendar access
- **JWT Tokens**: Session management
- **Webhook Validation**: Twilio signature verification

## 🚨 Troubleshooting

### Common Issues

#### 1. Twilio Webhook Errors
```bash
# Check ngrok is running
ngrok http 8001

# Verify webhook URL in Twilio console
# Should be: https://your-ngrok-url.ngrok-free.app/outgoing-call
```

#### 2. Google Calendar Permission Denied
- Verify OAuth credentials in Google Cloud Console
- Check redirect URI matches: `http://localhost:8080/auth/google/callback`
- Ensure Calendar API is enabled

#### 3. Database Connection Issues
```bash
# Check SQLite permissions
ls -la orchestrator/data/

# For PostgreSQL, verify connection string
DATABASE_URL=postgresql://user:pass@localhost/integrated_system
```

#### 4. Service Communication Errors
```bash
# Verify all services are running
curl http://localhost:8000/api/v1/health  # Booking Agent
curl http://localhost:8001/health         # Calling Agent
curl http://localhost:8080/api/v1/health  # Orchestrator
```

### Debug Mode

Enable debug logging:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📈 Performance Optimization

### Production Settings

```bash
# .env for production
ENVIRONMENT=production
DEBUG=false
USE_MEMORY_STORAGE=false
RATE_LIMIT_ENABLED=true
```

