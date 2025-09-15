# C:\Users\pc\OneDrive\Desktop\phantom_alert_bot\line_notifier.py

import requests
import logging
import os
import json # For JSON payload
import base64 # For Imgur image upload
import config # Import config module
from typing import Optional # <--- この行を追加します

logger = logging.getLogger(__name__)

class LineNotifier:
    def __init__(self, channel_access_token: str, to_ids: list, imgur_client_id: str, imgur_client_secret: str):
        """
        Initializes the LineNotifier instance for LINE Messaging API.
        
        Args:
            channel_access_token (str): LINE Messaging API Channel Access Token.
            to_ids (list): List of LINE user IDs or group IDs to send messages to.
            imgur_client_id (str): Imgur API Client ID for image uploads.
            imgur_client_secret (str): Imgur API Client Secret for image uploads.
        """
        self.channel_access_token = channel_access_token
        self.to_ids = to_ids
        self.imgur_client_id = imgur_client_id
        self.imgur_client_secret = imgur_client_secret # Not strictly needed for anonymous upload, but good to have
        
        self.line_api_url = "https://api.line.me/v2/bot/message/push"
        self.imgur_upload_url = "https://api.imgur.com/3/image"

        # Determine if notification is enabled
        self.is_enabled = bool(self.channel_access_token and self.to_ids)
        self.imgur_enabled = bool(self.imgur_client_id and self.imgur_client_secret)

        if self.is_enabled:
            logger.info("LineNotifier for LINE Messaging API is enabled.")
            if not self.imgur_enabled:
                logger.warning("Imgur client ID or secret is not set in config.py. Image notifications will not work via LINE Messaging API.")
            else:
                logger.info("Imgur integration is enabled for LINE Messaging API.")
        else:
            logger.warning("LineNotifier for LINE Messaging API is disabled. CHANNEL_ACCESS_TOKEN or TO_IDS are not set in config.py.")

    def _upload_image_to_imgur(self, image_path: str) -> Optional[str]: # <--- Optional が正しく認識されるようになる
        """
        Uploads an image file to Imgur and returns its direct link.
        
        Args:
            image_path (str): The local file path of the image.
        Returns:
            Optional[str]: The direct URL of the uploaded image, or None if upload fails.
        """
        if not self.imgur_enabled:
            logger.error("Imgur integration is not enabled. Cannot upload image.")
            return None

        if not os.path.exists(image_path):
            logger.error(f"Image file not found for Imgur upload: {image_path}")
            return None

        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
            payload = {"image": image_data, "type": "base64"}

            logger.debug(f"Uploading image to Imgur: {image_path}")
            response = requests.post(self.imgur_upload_url, headers=headers, data=payload)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            result = response.json()
            if result and result.get('success') and result.get('data') and result['data'].get('link'):
                image_url = result['data']['link']
                logger.info(f"Image uploaded to Imgur successfully: {image_url}")
                return image_url
            else:
                logger.error(f"Imgur upload failed or returned unexpected response: {result}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during Imgur upload: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Imgur upload: {e}", exc_info=True)
            return None

    def send_line_notification(self, message: str, image_path: str = None):
        """
        Sends a message and an optional image via LINE Messaging API (push message).
        Images are first uploaded to Imgur.
        
        Args:
            message (str): The message text to send.
            image_path (str, optional): The local file path of the image to send. None if no image.
        Returns:
            bool: True if sending was successful for at least one recipient, False otherwise.
        """
        if not self.is_enabled:
            logger.debug("LineNotifier for Messaging API is disabled, skipping notification.")
            return False

        messages = []
        # Add text message
        messages.append({"type": "text", "text": message})

        # If image_path is provided, upload to Imgur and add image message
        image_url = None
        if image_path:
            if self.imgur_enabled:
                image_url = self._upload_image_to_imgur(image_path)
                if image_url:
                    # LINE Messaging API requires originalContentUrl and previewImageUrl
                    # For simplicity, use the same URL for both.
                    messages.append({
                        "type": "image",
                        "originalContentUrl": image_url,
                        "previewImageUrl": image_url
                    })
                else:
                    logger.error(f"Failed to get Imgur URL for image: {image_path}. Sending text message only.")
            else:
                logger.warning("Imgur is not enabled. Cannot send image via LINE Messaging API. Sending text message only.")


        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        
        success_count = 0
        for to_id in self.to_ids:
            payload = {
                "to": to_id,
                "messages": messages
            }

            try:
                logger.debug(f"Sending LINE Messaging API push message to {to_id} with payload: {json.dumps(payload)}")
                response = requests.post(self.line_api_url, headers=headers, data=json.dumps(payload))
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                logger.info(f"LINE Messaging API push message sent successfully to {to_id}.")
                success_count += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Network or API error sending LINE Messaging API message to {to_id}: {e}", exc_info=True)
                if response.status_code == 400:
                    logger.error(f"LINE Messaging API Error Response (400 Bad Request): {response.text}")
                elif response.status_code == 401:
                    logger.error(f"LINE Messaging API Error Response (401 Unauthorized): Check your Channel Access Token validity. {response.text}")
                elif response.status_code == 403:
                    logger.error(f"LINE Messaging API Error Response (403 Forbidden): Check your API usage limits or permissions. {response.text}")
                elif response.status_code == 404:
                    logger.error(f"LINE Messaging API Error Response (404 Not Found): Check 'to' ID. {response.text}")
                elif response.status_code == 500:
                    logger.error(f"LINE Messaging API Error Response (500 Internal Server Error): {response.text}")
            except Exception as e:
                logger.error(f"An unexpected error occurred sending LINE Messaging API message to {to_id}: {e}", exc_info=True)
        
        return success_count > 0

# Example usage (this part is usually called from the bot's main logic)
if __name__ == '__main__':
    # Dummy config settings for testing (replace with actual values for real testing)
    class MockConfig:
        LINE_ENABLED = True
        # Replace with your actual LINE Messaging API Channel Access Token
        LINE_MESSAGING_API_CHANNEL_ACCESS_TOKEN = "YOUR_LINE_MESSAGING_API_CHANNEL_ACCESS_TOKEN_HERE" 
        # Replace with actual user ID(s) or group ID(s) you want to send to
        LINE_MESSAGING_API_TO_IDS = ["UXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"] 
        IMGUR_CLIENT_ID = "YOUR_IMGUR_CLIENT_ID_HERE"
        IMGUR_CLIENT_SECRET = "YOUR_IMGUR_CLIENT_SECRET_HERE" # Not always needed for anonymous upload
        LOG_LEVEL = logging.DEBUG
        LOG_FILE = "test_line_messaging_api.log"
        LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure logging (only for test execution)
    logging.basicConfig(level=MockConfig.LOG_LEVEL, format=MockConfig.LOG_FORMAT)

    # Replace config module with mock
    import sys
    sys.modules['config'] = MockConfig

    notifier = LineNotifier(
        channel_access_token=MockConfig.LINE_MESSAGING_API_CHANNEL_ACCESS_TOKEN,
        to_ids=MockConfig.LINE_MESSAGING_API_TO_IDS,
        imgur_client_id=MockConfig.IMGUR_CLIENT_ID,
        imgur_client_secret=MockConfig.IMGUR_CLIENT_SECRET
    )
    
    if notifier.is_enabled:
        # Send message only
        logger.info("Sending test text message via LINE Messaging API...")
        notifier.send_line_notification("LINE Messaging APIからのテストメッセージです。")

        # Create a dummy image file for testing
        from PIL import Image, ImageDraw, ImageFont
        test_image_path = "test_chart_messaging_api.png"
        try:
            img = Image.new('RGB', (400, 200), color = (100, 150, 200))
            d = ImageDraw.Draw(img)
            try:
                fnt = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                fnt = ImageFont.load_default()
            d.text((50,80), "LINE Messaging API Test Chart", font=fnt, fill=(255,255,255))
            img.save(test_image_path)
            logger.info(f"Created dummy image: {test_image_path}")
        except ImportError:
            logger.warning("Pillow (PIL) is not installed. Cannot create dummy image for test. `pip install Pillow` to enable.")
            test_image_path = None

        if test_image_path:
            # Send with image
            logger.info("Sending test image message via LINE Messaging API...")
            notifier.send_line_notification("LINE Messaging APIからの画像付きテストメッセージです。", image_path=test_image_path)
            if os.path.exists(test_image_path):
                os.remove(test_image_path) # Delete image after test
        else:
            logger.warning("Skipping image test as Pillow is not installed.")

    else:
        logger.warning("LINE Messaging API notifier is disabled for testing.")

