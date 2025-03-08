import requests
import json
import logging
from app.config import settings

class NotificationClient:
    """
    Client for creating notifications after authentication.
    """
    
    def __init__(self):
        """
        Initialize the client with settings.
        
        Args:
            settings (Settings, optional): Application settings. If not provided,
                                         will be loaded automatically.
        """
        self.backend_url = settings.BACKEND_URL.rstrip('/')
        self.access_token = None
        
    def _login(self):
        """
        Private method to authenticate and get the access token.
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        login_endpoint = f"{self.backend_url}/api/auth/"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "email": settings.AUTH_EMAIL,
            "password": settings.AUTH_PASSWORD
        }
        
        try:
            response = requests.post(login_endpoint, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise exception for non-2xx status codes
            
            auth_data = response.json()
            self.access_token = auth_data.get("access")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def create_notification(self, client_info):
        """
        Public method to create a notification.
        
        Args:
            client_info (dict): Dictionary containing client information for the notification
                
        Returns:
            dict: Response data if successful, None otherwise
        """
        # First, authenticate
        if not self._login():
            logging.error("Authentication failed. Cannot create notification.")
            return None
            
        # Create notification
        notification_endpoint = f"{self.backend_url}/notification/create/"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Format the payload according to API requirements
        payload = {
            "type": 2,  # Type for online booking
            "message": "whatsapp",
            "link": "",
            "additional_information": client_info
        }
        
        logging.info(f"Sending notification: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            # Using requests.json parameter which handles serialization automatically
            response = requests.post(notification_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to create notification: {str(e)}")
            if hasattr(e, 'response') and e.response:
              print(f"Response status: {e.response.status_code}")
              print(f"Response text: {e.response.text}")
            return None