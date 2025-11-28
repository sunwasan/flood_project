from pprint import pp
import sys
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
import os
from model.line_webhook import WebhookPayload
from linebot.v3.messaging import Configuration, ApiClient, MessagingApiBlob, MessagingApi, ReplyMessageRequest
from dotenv import load_dotenv
from pathlib import Path

file_dir = Path(__file__).resolve().parent
project_dir = file_dir.parent
data_dir = Path(os.getenv("DATA_DIR", project_dir / "data"))
python_dir = Path(os.getenv("PYTHON_DIR", project_dir / "python"))
model_dir = Path(os.getenv("MODEL_DIR", project_dir / "model"))
data_dir.mkdir(exist_ok=True, parents=True)

sys.path.append(str(python_dir))
from message_handle import message_handle, handle_postback
from flex_generator import get_login_flex_message
from auth import add_user, get_user

sys.path.append(str(model_dir))

from login_model import UserInfo, LoginSuccessResponse


load_dotenv(project_dir / ".env")


app = FastAPI()


users = {}
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
configuration = Configuration(access_token=channel_access_token)

@app.get("/line/login")
async def login(code: str = None, state: str = None, error: str = None, error_description: str = None):
    if error:
        # print(f"Login error: {error}, description: {error_description}")
        return {"status": "error", "error": error, "description": error_description}
    if code:
        # print(f"Login code: {code}, state: {state}")
        
        client_id = os.getenv("LINE_LOGIN_CHANNEL_ID")
        client_secret = os.getenv("LINE_LOGIN_CHANNEL_SECRET")
        redirect_uri = os.getenv("DOMAIN") + "/line/login"
        
        if not client_secret:
            return {"status": "error", "message": "LINE_LOGIN_CHANNEL_SECRET not set in .env"}

        # Exchange code for token
        token_url = "https://api.line.me/oauth2/v2.1/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code != 200:
            return {"status": "error", "message": "Token exchange failed", "details": response.json()}
            
        tokens = response.json()
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        
        user_info = {}
        
        # Get Profile
        if access_token:
            profile_url = "https://api.line.me/v2/profile"
            profile_headers = {"Authorization": f"Bearer {access_token}"}
            profile_response = requests.get(profile_url, headers=profile_headers)
            if profile_response.status_code == 200:
                user_info["profile"] = profile_response.json()
                
        # Verify ID Token to get Email
        if id_token:
            verify_url = "https://api.line.me/oauth2/v2.1/verify"
            verify_data = {
                "id_token": id_token,
                "client_id": client_id
            }
            verify_response = requests.post(verify_url, data=verify_data)
            if verify_response.status_code == 200:
                claims = verify_response.json()
                user_info["id_token_claims"] = claims
                if "email" in claims:
                    user_info["email"] = claims["email"]
                
        user = UserInfo(**user_info)
        add_user(user)
        return LoginSuccessResponse(status="login success", user_info=user)
        
    return {"status": "login endpoint", "message": "No code provided"}
    

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/line/webhook")
async def webhook(payload: WebhookPayload):
    print(f"Received webhook payload: {payload}")
    event_type = payload.events[0].type if payload.events else "unknown"
    message_id = payload.events[0].replyToken if payload.events and hasattr(payload.events[0], 'replyToken') else "unknown"
    user_id = payload.events[0].source.userId if payload.events and payload.events[0].source and hasattr(payload.events[0].source, 'userId') else "unknown"
    user = get_user(user_id)
    if event_type == "message":
        message_id = payload.events[0].message.id if payload.events and hasattr(payload.events[0], 'message') else "unknown"
        source_type = payload.events[0].source.type if payload.events and payload.events[0].source else "unknown"
        message = payload.events[0].message if payload.events and hasattr(payload.events[0], 'message') else None
        source_id = payload.events[0].source.userId if payload.events and payload.events[0].source and hasattr(payload.events[0].source, 'userId') else "unknown"
        replytoken = payload.events[0].replyToken if payload.events and hasattr(payload.events[0], 'replyToken') else "unknown"
        if source_type == "user":
            user_id = source_id
        
        elif source_type == "group":
            user_id = payload.events[0].source.userId if payload.events and payload.events[0].source and hasattr(payload.events[0].source, 'userId') else "unknown"
            group_id = payload.events[0].source.groupId if payload.events and payload.events[0].source and hasattr(payload.events[0].source, 'groupId') else "unknown"
            source_id = (group_id, user_id)
            
        
        if not user:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=replytoken,
                        messages=[get_login_flex_message()]
                    )
                )
        else:
            message_handle(message, source_type, source_id, replytoken, message_id)
    elif event_type == "postback":
        replytoken = payload.events[0].replyToken
        data = payload.events[0].postback.data
        source_id = payload.events[0].source.userId if payload.events and payload.events[0].source and hasattr(payload.events[0].source, 'userId') else "unknown"
        handle_postback(replytoken, data, source_id, user.email if user else None, message_id)
    else:
        print(f"Unhandled event type: {event_type}")
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)