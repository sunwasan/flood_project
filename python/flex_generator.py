from linebot.v3.messaging import (
    FlexMessage,
    FlexContainer,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    LocationAction
)
import os

import urllib.parse

def get_login_flex_message():
    redirect_uri = os.getenv("DOMAIN", "YOUR_DOMAIN") + "/line/login"
    encoded_redirect_uri = urllib.parse.quote(redirect_uri, safe='')
    
    # Added prompt=consent to force the consent screen to appear
    login_url = os.getenv("LINE_LOGIN_URL", "https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={}&redirect_uri={}&state={}&scope=profile%20openid%20email&prompt=consent".format(
        os.getenv("LINE_LOGIN_CHANNEL_ID", "YOUR_CHANNEL_ID"),
        encoded_redirect_uri,
        "random_state"
    ))
    print(f"Generated Login URL: {login_url}")
    
    return FlexMessage(
        alt_text="Please login",
        contents=FlexContainer.from_dict({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "Access Required",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": "Please log in to continue using this service.",
                        "wrap": True,
                        "margin": "md",
                        "align": "center",
                        "color": "#666666"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "LINE Login",
                            "uri": login_url
                        },
                        "style": "primary",
                        "margin": "lg",
                        "height": "sm"
                    }
                ]
            }
        })
    )

def get_location_request_message():
    return TextMessage(
        text="Please share your location so we can find the nearest branch.",
        quickReply=QuickReply(
            items=[
                QuickReplyItem(
                    type="action",
                    action=LocationAction(label="Send Location")
                )
            ]
        )
    )
