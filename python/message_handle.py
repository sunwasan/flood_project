from linebot.v3.messaging import Configuration, ApiClient, MessagingApiBlob, MessagingApi, ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer
from dotenv import load_dotenv
import os
from flex_generator import get_location_request_message
from llm_qa import DisasterBot
from insert_report import insert_db
load_dotenv()


def download_image(url: str) -> bytes:
    import urllib.request
    with urllib.request.urlopen(url) as response:
        return response.read()

def get_image_data(message) -> bytes | None:
    # print(f"Getting image data for message {message.id}")
    content_provider = message.contentProvider
    if content_provider.type == "external":
        if content_provider.originalContentUrl:
            return download_image(content_provider.originalContentUrl)
    elif content_provider.type == "line":
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if channel_access_token:
            try:
                configuration = Configuration(access_token=channel_access_token)
                with ApiClient(configuration) as api_client:
                    line_bot_blob_api = MessagingApiBlob(api_client)
                    return line_bot_blob_api.get_message_content(message.id)
            except Exception as e:
                print(f"Error getting image content: {e}")
                return None
        else:
            print("LINE_CHANNEL_ACCESS_TOKEN not found")
    return None


def handle_image(message, source_type, source_id, replytoken, message_id):
    image_data = get_image_data(message)
    if image_data:
        print(f"Image data retrieved, size: {len(image_data)} bytes")
        if source_type == "user":
            user_id = source_id
            # Save the image to a file
            with open(f"data/{message_id}_image.jpg", "wb") as img_file:
                img_file.write(image_data)
            print(f"Image saved to data/{message_id}_image.jpg")
        elif source_type == "group":
            group_id, user_id = source_id
            with open(f"data/{group_id}_{user_id}_{message_id}_image.jpg", "wb") as img_file:
                img_file.write(image_data)
            print(f"Image saved to data/{group_id}_{user_id}_{message_id}_image.jpg")
    else:
        print("Failed to retrieve image data")

def handle_location(message, source_type, source_id, replytoken, message_id):
    if source_type == "user":
        user_id = source_id
        # print(f"Location message from user {user_id}: {message.address} ({message.latitude}, {message.longitude})")
        
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if channel_access_token:
            configuration = Configuration(access_token=channel_access_token)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=replytoken,
                        messages=[TextMessage(text=f"Thank you! We received your location: {message.address}")]
                    )
                )

def process_text_message(text, user_id, replytoken):
    print(f"Processing message with DisasterBot: {text}")
    try:
        disaster_bot = DisasterBot(user_id)

        response_payload = disaster_bot.forward(text)
        # print(f"DisasterBot response payload: {response_payload}")
        
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if channel_access_token:
            configuration = Configuration(access_token=channel_access_token)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                
                messages = []
                if isinstance(response_payload, str):
                    messages.append(TextMessage(text=response_payload))
                elif isinstance(response_payload, dict):
                    if response_payload.get("type") == "text":
                        messages.append(TextMessage(text=response_payload.get("text")))
                    elif response_payload.get("type") == "flex":
                        flex_content = response_payload.get("contents")
                        messages.append(FlexMessage(alt_text=response_payload.get("altText", "Flex Message"), contents=FlexContainer.from_dict(flex_content)))
                
                if messages:
                    print(f"Sending reply message: {messages}")
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=replytoken,
                            messages=messages
                        )
                    )
                    print("Reply sent successfully")
                else:
                    print("No messages to send")
        else:
            print("LINE_CHANNEL_ACCESS_TOKEN not found in .env")
    except Exception as e:
        print(f"Error in DisasterBot or sending reply: {e}")
        import traceback
        traceback.print_exc()
        
        # Attempt to send error message to user
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if channel_access_token:
            try:
                configuration = Configuration(access_token=channel_access_token)
                with ApiClient(configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=replytoken,
                            messages=[TextMessage(text="Sorry, I encountered an error processing your request.")]
                        )
                    )
            except Exception as reply_error:
                print(f"Failed to send error reply: {reply_error}")

def handle_postback(replytoken, data, source_id, email, message_id):
    # print(f"Postback data: {data}")
    # Postback data: action=submit&loc=ปทุมธานี,ธัญญบุรี,ลำผัดกูด&addr=ตรงข้ามวัดอัยยิการาม&content=น้ำท่วมชั้น 2 ไฟดับหมดเลย (The second floor is flooded and the power is out.)&urgency=Critical


    if "action=submit" in data:
        # Clear the user's state
        user_id = source_id
        if isinstance(source_id, tuple): # Handle group source_id (group_id, user_id)
             user_id = source_id[1]
        
        report_data = {
            'province': data.split("province=")[1].split("&")[0] if "province=" in data else "",
            'district': data.split("dis=")[1].split("&")[0] if "dis=" in data else "",
            'subdistrict': data.split("sub=")[1].split("&")[0] if "sub=" in data else "",
            'address_details': data.split("addr=")[1].split("&")[0] if "addr=" in data else "",
            'content': data.split("content=")[1].split("&")[0] if "content=" in data else "",
            'urgency_level': data.split("urgency=")[1].split("&")[0] if "urgency=" in data else "",
            'user_id': user_id,
            'user_email': email
        }
        
        insert_db(
            message_id=message_id,
            province=report_data['province'],
            district=report_data['district'],
            sub_district=report_data['subdistrict'],
            address=report_data['address_details'],
            content=report_data['content'],
            urgency=report_data['urgency_level'],
            reporter_line_id=report_data['user_id'],
            reporter_email=report_data['user_email']
        )      
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if channel_access_token:
            configuration = Configuration(access_token=channel_access_token)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=replytoken,
                        messages=[TextMessage(text="เราได้รับรายงานของคุณแล้ว ขอบคุณสำหรับข้อมูลค่ะ")] # TODO: Make this a flex message
                    )
                )

def handle_text(message, source_type, source_id, replytoken, message_id):
    if source_type == "user":
        user_id = source_id
        text = message.text
        print(f"Text message from user {user_id}: {text}")
        
        if "branch" in text.lower() or "location" in text.lower():
            channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
            if channel_access_token:
                configuration = Configuration(access_token=channel_access_token)
                with ApiClient(configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=replytoken,
                            messages=[get_location_request_message()]
                        )
                    )
        else:
            # Use DisasterBot for other messages
            process_text_message(text, user_id, replytoken)

    elif source_type == "group":
        group_id, user_id = source_id
        text = message.text
        print(f"Text message from user {user_id} in group {group_id}: {text}")
        # Use DisasterBot for group messages too, using user_id to track individual user state
        process_text_message(text, user_id, replytoken)



def message_handle(message, source_type, source_id, replytoken, message_id):
    if source_type == "user":
        user_id = source_id
        if message.type == "text":
            handle_text(message, source_type, source_id, replytoken, message_id)
        elif message.type == "image":
            handle_image(message, source_type, source_id, replytoken, message_id)
        elif message.type == "location":
            handle_location(message, source_type, source_id, replytoken, message_id)
        else:
            print(f"Unhandled message type from user {user_id}: {message.type}")
    elif source_type == "group":
        group_id, user_id = source_id
        if message.type == "text":
            handle_text(message, source_type, source_id, replytoken, message_id)
        elif message.type == "image":
            handle_image(message, source_type, source_id, replytoken, message_id)
        elif message.type == "location":
             # Handle location in group if needed, for now just print
             print(f"Location message from user {user_id} in group {group_id}")
        else:
            print(f"Unhandled message type from user {user_id} in group {group_id}: {message.type}")
    else:
        print(f"Unhandled source type: {source_type}")
