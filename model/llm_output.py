from pydantic import BaseModel, Field
from typing import Optional

class LLMOutput(BaseModel):
    mentioned_location: Optional[str] = Field(
        None, 
        description="Extract the specific City, District, or Subdistrict mentioned. If only vague terms like 'here', 'my house', or 'nearby' are used, return None."
    )
    raw_content: str = Field(
        ..., 
        description="The verbatim report provided by the user. Do not summarize, translate, or correct spelling."
    )
    urgency_level: Optional[str] = Field(
        None, 
        description="The urgency of the situation. Returns 'Critical' for immediate threat to life, 'High' for property damage/injury risk, 'Medium' for manageable disruptions, or 'Low' for information/inquiries."
    )