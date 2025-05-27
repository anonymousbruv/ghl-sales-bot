import httpx
import logging
import requests
import psycopg2
from typing import Optional, Dict, Any, Tuple
from sales_bot.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class GHLAPI:
    def __init__(self):
        self.base_url = "https://services.leadconnectorhq.com"
        self.oauth_url = "https://marketplace.gohighlevel.com/oauth"
        self.token_url = f"{self.base_url}/oauth/token"
        self.client_id = settings.GHL_CLIENT_ID
        self.client_secret = settings.GHL_CLIENT_SECRET
        
        # Get initial tokens
        self.access_token, self.refresh_token = self.get_tokens()
        self.update_headers()
        
    def update_headers(self):
        """Update headers with current access token"""
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Version": "2021-04-15"
        }
        
    def get_tokens(self) -> Tuple[str, str]:
        """Get current tokens from Supabase"""
        try:
            conn = psycopg2.connect(settings.SUPABASE_DB_URL)
            cur = conn.cursor()
            cur.execute("SELECT access_token, refresh_token FROM tokens ORDER BY updated_at DESC LIMIT 1;")
            tokens = cur.fetchone()
            cur.close()
            conn.close()
            if not tokens:
                logger.error("No tokens found in database")
                raise ValueError("No tokens found in database")
            logger.info("Successfully retrieved tokens from database")
            return tokens[0], tokens[1]
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise ValueError(f"Failed to connect to database: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting tokens from database: {str(e)}")
            raise
            
    def update_tokens(self, new_access_token: str, new_refresh_token: str):
        """Update tokens in Supabase"""
        try:
            conn = psycopg2.connect(settings.SUPABASE_DB_URL)
            cur = conn.cursor()
            cur.execute(
                "UPDATE tokens SET access_token=%s, refresh_token=%s, updated_at=NOW() WHERE id=1;",
                (new_access_token, new_refresh_token)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            # Update instance variables
            self.access_token = new_access_token
            self.refresh_token = new_refresh_token
            self.update_headers()
            
            logger.info("Tokens updated successfully in database")
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise ValueError(f"Failed to connect to database: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating tokens in database: {str(e)}")
            raise
            
    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = requests.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            
            tokens = response.json()
            new_access_token = tokens["access_token"]
            new_refresh_token = tokens["refresh_token"]
            
            self.update_tokens(new_access_token, new_refresh_token)
            logger.info("✅ Tokens refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh tokens: {str(e)}")
            return False
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with automatic token refresh"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    f"{self.base_url}/{endpoint}",
                    headers=self.headers,
                    **kwargs
                )
                
                # If token expired, refresh and retry
                if response.status_code == 401:
                    logger.info("🔴 Access token expired! Refreshing...")
                    if self.refresh_access_token():
                        # Update headers with new token
                        self.update_headers()
                        # Retry request
                        response = await client.request(
                            method,
                            f"{self.base_url}/{endpoint}",
                            headers=self.headers,
                            **kwargs
                        )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            raise

    async def get_contact_pipeline(self, contact_id: str) -> str:
        """Get the pipeline name for a contact"""
        try:
            data = await self._make_request("GET", f"contacts/{contact_id}")
            
            # Get pipeline name from contact data
            pipeline = data.get("pipeline", {})
            if isinstance(pipeline, dict):
                pipeline_name = pipeline.get("name", "")
            else:
                pipeline_name = str(pipeline)
            
            logger.info(f"Contact {contact_id} is in pipeline: {pipeline_name}")
            return pipeline_name
                
        except Exception as e:
            logger.error(f"Error getting contact pipeline: {str(e)}")
            return ""
    
    async def send_sms(self, contact_id: str, message: str) -> bool:
        """Send SMS to a contact"""
        try:
            data = {
                "contactId": contact_id,
                "message": message,
                "type": "SMS",
                "direction": "outbound"
            }
            
            await self._make_request("POST", "conversations/messages", json=data)
            logger.info(f"SMS sent successfully to {contact_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

class GHLClient:
    def __init__(self):
        self.base_url = "https://services.leadconnectorhq.com"
        self.oauth_url = "https://marketplace.gohighlevel.com/oauth"
        
    def get_authorization_url(self, client_id: str, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL
        """
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "contacts.readonly contacts.write conversations.readonly conversations.write locations.readonly locations.write opportunities.readonly opportunities.write users.readonly users.write"
        }
        if state:
            params["state"] = state
            
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.oauth_url}/authorize?{query_string}"
        
    def exchange_code_for_token(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        """
        try:
            response = requests.post(
                f"{self.oauth_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            raise 