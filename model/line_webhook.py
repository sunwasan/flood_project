from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field

class DeliveryContext(BaseModel):
    isRedelivery: bool

class Source(BaseModel):
    type: Literal['user', 'group', 'room']
    userId: Optional[str] = None
    groupId: Optional[str] = None
    roomId: Optional[str] = None

class ContentProvider(BaseModel):
    type: Literal['line', 'external']
    originalContentUrl: Optional[str] = None
    previewImageUrl: Optional[str] = None

class Emoji(BaseModel):
    index: int
    length: int
    productId: str
    emojiId: str

class Mentionee(BaseModel):
    index: int
    length: int
    userId: str

class Mention(BaseModel):
    mentionees: List[Mentionee]

class MessageContent(BaseModel):
    id: str
    type: str

class TextMessageContent(MessageContent):
    type: Literal['text']
    text: str
    emojis: Optional[List[Emoji]] = None
    mention: Optional[Mention] = None
    quoteToken: Optional[str] = None

class ImageMessageContent(MessageContent):
    type: Literal['image']
    contentProvider: ContentProvider
    imageSet: Optional[Dict[str, Any]] = None

class StickerMessageContent(MessageContent):
    type: Literal['sticker']
    packageId: str
    stickerId: str
    stickerResourceType: Optional[str] = None
    keywords: Optional[List[str]] = None

class LocationMessageContent(MessageContent):
    type: Literal['location']
    title: str
    address: str
    latitude: float
    longitude: float

class BaseEvent(BaseModel):
    type: str
    mode: Literal['active', 'standby']
    timestamp: int
    source: Optional[Source] = None
    webhookEventId: str
    deliveryContext: DeliveryContext

class MessageEvent(BaseEvent):
    type: Literal['message']
    replyToken: str
    message: Union[TextMessageContent, ImageMessageContent, StickerMessageContent, LocationMessageContent, MessageContent]

class FollowEvent(BaseEvent):
    type: Literal['follow']
    replyToken: str

class UnfollowEvent(BaseEvent):
    type: Literal['unfollow']

class JoinEvent(BaseEvent):
    type: Literal['join']
    replyToken: str

class LeaveEvent(BaseEvent):
    type: Literal['leave']

class Postback(BaseModel):
    data: str
    params: Optional[Dict[str, Any]] = None

class PostbackEvent(BaseEvent):
    type: Literal['postback']
    replyToken: str
    postback: Postback

class Beacon(BaseModel):
    hwid: str
    type: str
    dm: Optional[str] = None

class BeaconEvent(BaseEvent):
    type: Literal['beacon']
    replyToken: str
    beacon: Beacon

class WebhookPayload(BaseModel):
    destination: str
    events: List[Union[MessageEvent, FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent, PostbackEvent, BeaconEvent, BaseEvent]]
