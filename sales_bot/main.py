from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from sales_bot.config import get_settings
from sales_bot.ghl_api import GHLAPI, GHLClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="GHL Sales Bot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings
settings = get_settings()

# Initialize GHL client
ghl_client = GHLClient()

# Initialize GHL API
ghl_api = GHLAPI()

# Add your test pipeline name here
TEST_PIPELINE = "Test (Sales Bot)"  # Exact match from GHL

class Message(BaseModel):
    type: int
    body: str

class WebhookData(BaseModel):
    id: str  # Opportunity ID
    contact_id: str  # Contact ID
    phone: str
    message: Message
    pipeline_name: str

async def process_message(contact_id: str, message: str) -> None:
    """Process incoming message and send response"""
    try:
        # Get contact's pipeline
        pipeline = await ghl_api.get_contact_pipeline(contact_id)
        logger.info(f"Contact {contact_id} is in pipeline: {pipeline}")
        
        # Send response based on pipeline
        if pipeline.lower() == "sales":
            response = "Thank you for your interest! A sales representative will contact you shortly."
        else:
            response = "Thank you for your message. How can we help you today?"
            
        # Send SMS response
        success = await ghl_api.send_sms(contact_id, response)
        if success:
            logger.info(f"Response sent to {contact_id}")
        else:
            logger.error(f"Failed to send response to {contact_id}")
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook requests"""
    try:
        # Parse webhook data
        data = await request.json()
        logger.info(f"Received webhook: {json.dumps(data, indent=2)}")
        
        # Process message asynchronously
        if data.get("type") == "message":
            contact_id = data.get("contactId")
            message = data.get("message", {}).get("text", "")
            if contact_id and message:
                asyncio.create_task(process_message(contact_id, message))
                
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy"})

@app.get("/oauth/callback")
async def oauth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback"""
    try:
        # Exchange code for token
        tokens = ghl_client.exchange_code_for_token(
            code=code,
            client_id=settings.GHL_CLIENT_ID,
            client_secret=settings.GHL_CLIENT_SECRET,
            redirect_uri=settings.GHL_REDIRECT_URI
        )
        
        # Update tokens in database
        ghl_api.update_tokens(
            tokens["access_token"],
            tokens["refresh_token"]
        )
        
        return HTMLResponse(content="""
            <html>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window now.</p>
                </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/authorize")
async def oauth_authorize():
    """Generate OAuth authorization URL"""
    try:
        auth_url = ghl_client.get_authorization_url(
            client_id=settings.GHL_CLIENT_ID,
            redirect_uri=settings.GHL_REDIRECT_URI
        )
        return JSONResponse(content={"authorization_url": auth_url})
        
    except Exception as e:
        logger.error(f"Error generating authorization URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting webhook server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 