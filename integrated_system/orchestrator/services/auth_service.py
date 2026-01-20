"""
Authentication Service for Google OAuth and session management
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiohttp
import jwt
from models import UserSession, AuthRequest, AuthResponse
from config import settings

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service for Google OAuth and session management"""
    
    def __init__(self):
        self.google_config = settings.google_auth_config
        self.sessions: Dict[str, UserSession] = {}  # In production, use Redis
        
    async def get_google_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        if not self.google_config:
            raise ValueError("Google authentication not configured")
        
        params = {
            "client_id": self.google_config.client_id,
            "redirect_uri": self.google_config.redirect_uri,
            "scope": " ".join(self.google_config.scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        # Build URL
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"https://accounts.google.com/o/oauth2/auth?{param_string}"
        
        return auth_url
    
    async def handle_google_callback(self, code: str, state: Optional[str] = None) -> AuthResponse:
        """Handle Google OAuth callback and create user session"""
        if not self.google_config:
            return AuthResponse(
                success=False,
                message="Google authentication not configured"
            )
        
        try:
            # Exchange code for tokens
            token_data = await self._exchange_code_for_tokens(code)
            
            if not token_data:
                return AuthResponse(
                    success=False,
                    message="Failed to exchange authorization code"
                )
            
            # Get user info
            user_info = await self._get_google_user_info(token_data["access_token"])
            
            if not user_info:
                return AuthResponse(
                    success=False,
                    message="Failed to retrieve user information"
                )
            
            # Create user session
            session_id = await self._create_user_session(user_info, token_data)
            
            return AuthResponse(
                success=True,
                message="Authentication successful",
                session_id=session_id,
                user_info={
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Google OAuth callback failed: {e}")
            return AuthResponse(
                success=False,
                message=f"Authentication failed: {str(e)}"
            )
    
    async def _exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access and refresh tokens"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": self.google_config.client_id,
            "client_secret": self.google_config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.google_config.redirect_uri
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"❌ Token exchange failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Token exchange error: {e}")
            return None
    
    async def _get_google_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google"""
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user_info_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"❌ User info request failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ User info request error: {e}")
            return None
    
    async def _create_user_session(self, user_info: Dict[str, Any], token_data: Dict[str, Any]) -> str:
        """Create and store user session"""
        import uuid
        
        session_id = str(uuid.uuid4())
        
        user_session = UserSession(
            user_id=user_info.get("id", session_id),
            email=user_info.get("email", ""),
            google_access_token=token_data.get("access_token"),
            google_refresh_token=token_data.get("refresh_token"),
            preferences={
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", ""),
                "locale": user_info.get("locale", "en")
            }
        )
        
        # Store session (in production, use Redis with expiration)
        self.sessions[session_id] = user_session
        
        logger.info(f"✅ Created session for user: {user_session.email}")
        return session_id
    
    async def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """Get user session by ID"""
        session = self.sessions.get(session_id)
        
        if session:
            # Update last activity
            session.last_activity = datetime.now()
            
            # Check if session is expired
            if self._is_session_expired(session):
                await self.revoke_session(session_id)
                return None
        
        return session
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke user session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Revoke Google tokens if available
            if session.google_access_token:
                await self._revoke_google_token(session.google_access_token)
            
            # Remove session
            del self.sessions[session_id]
            
            logger.info(f"✅ Revoked session for user: {session.email}")
            return True
        
        return False
    
    async def _revoke_google_token(self, access_token: str) -> bool:
        """Revoke Google access token"""
        revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(revoke_url) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"❌ Token revocation error: {e}")
            return False
    
    def _is_session_expired(self, session: UserSession) -> bool:
        """Check if session is expired"""
        expiry_time = session.last_activity + timedelta(hours=settings.SESSION_EXPIRE_HOURS)
        return datetime.now() > expiry_time
    
    async def refresh_google_token(self, session_id: str) -> bool:
        """Refresh Google access token using refresh token"""
        session = self.sessions.get(session_id)
        
        if not session or not session.google_refresh_token:
            return False
        
        refresh_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": self.google_config.client_id,
            "client_secret": self.google_config.client_secret,
            "refresh_token": session.google_refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            async with aiohttp.ClientSession() as session_client:
                async with session_client.post(refresh_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        
                        # Update access token
                        session.google_access_token = token_data.get("access_token")
                        session.last_activity = datetime.now()
                        
                        logger.info(f"✅ Refreshed token for user: {session.email}")
                        return True
                    else:
                        logger.error(f"❌ Token refresh failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return False
    
    def create_jwt_token(self, user_session: UserSession) -> str:
        """Create JWT token for API authentication"""
        payload = {
            "user_id": user_session.user_id,
            "email": user_session.email,
            "exp": datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("❌ JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("❌ Invalid JWT token")
            return None
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.revoke_session(session_id)
        
        if expired_sessions:
            logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        active_sessions = len(self.sessions)
        
        # Count sessions by domain
        domains = {}
        for session in self.sessions.values():
            if session.email:
                domain = session.email.split('@')[-1]
                domains[domain] = domains.get(domain, 0) + 1
        
        return {
            "active_sessions": active_sessions,
            "domains": domains,
            "google_auth_enabled": bool(self.google_config)
        }

# Global auth service instance
auth_service = AuthService()