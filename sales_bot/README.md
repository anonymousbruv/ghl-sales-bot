# Sales Bot

SMS-based sales bot for nurturing leads in Go High Level (GHL).

## Project Structure
```
/sales_bot/
│
├── main.py                  # FastAPI entry point (sets up routes)
├── ghl_api.py              # GHL API client with OAuth and token refresh
├── config.py               # Configuration and environment variables
├── __init__.py            # Package initialization
│
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (API keys, DB URLs)
├── README.md              # Project overview & setup instructions
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with the following variables:
```
# GHL OAuth Settings
GHL_CLIENT_ID=your_client_id_here
GHL_CLIENT_SECRET=your_client_secret_here
GHL_REDIRECT_URI=your_redirect_uri_here
GHL_API_KEY=your_api_key_here

# Supabase Settings
SUPABASE_DB_URL=your_supabase_db_url_here
```

## Features

- Automated SMS responses
- OAuth token management with auto-refresh
- Secure token storage in Supabase
- Integration with GHL API v2
- Webhook handling for incoming messages
- Background task processing

## Usage

1. Start the server:
```bash
python main.py
```

2. Configure GHL webhook to point to your server's `/webhook` endpoint

3. The bot will automatically:
   - Receive webhook events from GHL
   - Process incoming messages
   - Send appropriate responses
   - Handle OAuth token refresh
   - Store tokens securely in Supabase

## API Endpoints

- `POST /webhook` - Handle GHL webhook events
- `GET /oauth/callback` - Handle OAuth callback
- `GET /ping` - Health check endpoint 