from typing import Optional, Dict, Any
from pydantic import BaseModel

class Profile(BaseModel):
    userId: str
    displayName: str
    statusMessage: Optional[str] = None
    pictureUrl: Optional[str] = None

class IdTokenClaims(BaseModel):
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    amr: list[str]
    name: str
    picture: Optional[str] = None
    email: Optional[str] = None

class UserInfo(BaseModel):
    profile: Optional[Profile] = None
    id_token_claims: Optional[IdTokenClaims] = None
    email: Optional[str] = None

class LoginSuccessResponse(BaseModel):
    status: str
    user_info: UserInfo
