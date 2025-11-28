import dspy
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import redis 
import json

from insert_report import insert_db



redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST", "localhost"),
                                 port=int(os.getenv("REDIS_PORT", "6379")),
                                 db=int(os.getenv("REDIS_DB", "0")))


load_dotenv()  # Load environment variables from .env file
api_key = os.getenv("GEMINI_API_KEY")
lm = dspy.LM("gemini/gemini-2.5-flash-lite", api_key=api_key)
dspy.configure(lm=lm)
dspy.configure(verbosity="info", cache=False)

user_database: Dict[str, List[dict]] = {}

# --- 1. Data Models ---
class ReportState(BaseModel):
    province: Optional[str] = None
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    address_details: Optional[str] = None
    raw_content: Optional[str] = None
    urgency_level: Optional[str] = None
    step: str = "collecting"
    last_bot_question: Optional[str] = None  # จำคำถามล่าสุดที่บอทถาม

# --- 2. DSPy Signatures ---

class IntentRouter(dspy.Signature):
    """Analyze if the user is starting a completely new topic or continuing the current report."""
    chat_memory = dspy.InputField(desc="Previous chat history.")
    new_message = dspy.InputField(desc="The user's latest input.")
    intent = dspy.OutputField(desc="Either 'new_topic' or 'continue_report' or 'remove_report'.")

class FieldExtractor(dspy.Signature):
    """
    Extract disaster report details.
    Context Awareness: Use 'previous_question' to understand short answers.
    Example: If previous_question is "Which district?", and message is "Ladprao", then District = Ladprao.
    """
    current_state = dspy.InputField(desc="JSON of current known facts.")
    previous_question = dspy.InputField(desc="The question the bot just asked.")
    new_message = dspy.InputField(desc="User's latest reply.")
    
    province = dspy.OutputField(desc="Province name (Thailand).")
    district = dspy.OutputField(desc="District/Amphoe name. (Thailand)")
    subdistrict = dspy.OutputField(desc="Subdistrict/Tambon name. (Thailand)")
    address_details = dspy.OutputField(desc="Specific location details.")
    content_update = dspy.OutputField(desc="Details about the incident. (must be same language as input, exactly as user types, keep details as much as possible)")
    urgency_update = dspy.OutputField(desc="Urgency (Low/Medium/High/Critical).")

class QuestionGenerator(dspy.Signature):
    """
    You are a Thai Disaster Relief Bot.
    Your Goal: Collect complete location data (Province, District, Subdistrict) and incident details.
    
    CRITICAL RULES:
    1. Check 'missing_info'. You MUST ask for these missing fields first.
    2. Do NOT ask for details/urgency if Location is not complete.
    3. If everything is complete, say nothing (output empty string).
    4. Politeness: Speak Thai, be concise and urgent.
    """
    current_knowledge = dspy.InputField(desc="JSON of current state.")
    missing_info = dspy.InputField(desc="List of fields that are strictly missing.")
    question = dspy.OutputField(desc="The next question to ask in Thai.")

# --- 3. Main Logic Class ---

class DisasterBot(dspy.Module):
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        
        # Define Modules
        self.router = dspy.Predict(IntentRouter)
        self.extractor = dspy.ChainOfThought(FieldExtractor) 
        self.asker = dspy.ChainOfThought(QuestionGenerator)  
        
        self.retrieve_user_messages()
        
    def retrieve_user_messages(self):
        messages = redis_client.get(f"user:{self.user_id}:messages")
        if messages:
            self.messages = json.loads(messages)
        else:
            self.messages = []
        return self.messages
    
    def update_user_messages(self, new_state_dict: dict):
            # 1. บันทึกลง Database กลาง
            if self.user_id not in user_database:
                user_database[self.user_id] = []
            user_database[self.user_id].append(new_state_dict)
            redis_client.set(f"user:{self.user_id}:messages", json.dumps(user_database[self.user_id]))
            # print(self.messages)
            # 2. --- FIX: อัปเดตความจำในตัว instance ทันที ---
            self.messages.append(new_state_dict)

    def _merge_content(self, old_text: Optional[str], new_text: Optional[str]) -> str:
            """Smartly merges text, filtering out 'None' strings and duplicates."""
            
            # Helper to clean strings and return None if it's a "null" value
            def clean(text):
                if not text: return None
                s = str(text).strip()
                if s.lower() in ["none", "null", "n/a", "unknown", "no", ""]:
                    return None
                return s

            old_clean = clean(old_text)
            new_clean = clean(new_text)

            # Logic for combination
            if not old_clean and not new_clean: return None
            if not new_clean: return old_clean
            if not old_clean: return new_clean

            # Check for duplicates
            if new_clean in old_clean: return old_clean
            if old_clean in new_clean: return new_clean

            return f"{old_clean} {new_clean}"
        
    def _has_value(self, val):
        """Helper to check if a value is truly present (not None, not 'None', not empty)."""
        if val is None: return False
        s = str(val).strip().lower()
        return s not in ["", "none", "null", "n/a", "unknown", "ไม่ทราบ"]

    def generate_flex_json(self, state: ReportState):
        """Helper to build LINE Flex Message"""
        color = "#ff0000" if state.urgency_level == "" else "#1DB446"
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "CONFIRM REPORT", "weight": "bold", "size": "xl", "color": color},
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": [
                            {"type": "text", "text": f"📍 Location: {state.province}, {state.district}, {state.subdistrict}, {state.address_details}", "wrap": True},
                            {"type": "text", "text": f"📝 Event: {state.raw_content}", "wrap": True},
                            {"type": "text", "text": f"🚨 Urgency: {state.urgency_level}", "wrap": True},
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": color,
                        "action": {
                            "type": "postback",
                            "label": "SUBMIT REPORT",
                            "data": f"action=submit&province={state.province}&dis={state.district}&sub={state.subdistrict}&addr={state.address_details}&content={state.raw_content}&urgency={state.urgency_level}"
                            
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "margin": "sm",
                        "action": {
                            "type": "message",
                            "label": "Cancel",
                            "text": "Cancel"
                        }
                    }
                ]
            }
        }
        

    def clear_state(self):
        self.messages = []
        redis_client.delete(f"user:{self.user_id}:messages")

    def remove_report(self):
        """Remove the current report and clear state."""
        self.clear_state()
        return {'type': 'text', 'text': "ยกเลิกการรายงานเรียบร้อยแล้ว หากต้องการรายงานใหม่ กรุณาเริ่มต้นใหม่ได้เลยค่ะ"}

    def forward(self, user_message: str):
        # 1. Load History & Determine Context
        
        intent = self.router(chat_memory=self.messages, new_message=user_message)
        if intent.intent == "remove_report":
            return self.remove_report()
        
        
        last_state_dict = self.messages[-1] if self.messages else None
        
        is_new_topic = False
        if not last_state_dict:
            is_new_topic = True
        elif last_state_dict.get('step') == "complete":
            is_new_topic = True
        else:
            is_new_topic = False 
            
        # 2. Setup Current State Object
        if is_new_topic:
            previous_question = "None (Start)"
            last_state = ReportState() # Empty state
        else:
            last_state = ReportState.model_validate(last_state_dict)
            previous_question = last_state.last_bot_question or "None"

        # 3. Extract Information
        extraction = self.extractor(
            current_state=last_state.model_dump_json(),
            previous_question=previous_question,
            new_message=user_message
        )
        
        # 4. Merge Data (Keep old data if new is None)
        new_state = last_state.copy(update={
            "province": extraction.province if self._has_value(extraction.province) else last_state.province,
            "district": extraction.district if self._has_value(extraction.district) else last_state.district,
            "subdistrict": extraction.subdistrict if self._has_value(extraction.subdistrict) else last_state.subdistrict,
            "address_details": extraction.address_details if self._has_value(extraction.address_details) else last_state.address_details,
            "raw_content": self._merge_content(last_state.raw_content, extraction.content_update),
            "urgency_level": extraction.urgency_update if self._has_value(extraction.urgency_update) else last_state.urgency_level,
        })


        missing_fields = []
        if not self._has_value(new_state.province): missing_fields.append("จังหวัด (Province)")
        if not self._has_value(new_state.district): missing_fields.append("อำเภอ (District)")
        if not self._has_value(new_state.subdistrict): missing_fields.append("ตำบล (Subdistrict)")
        
        # Content check
        if not self._has_value(new_state.raw_content) or len(new_state.raw_content) < 3:
            missing_fields.append("รายละเอียดเหตุการณ์ (Details)")

        # Decide Step
        if len(missing_fields) == 0:
            new_state.step = "complete"
        else:
            new_state.step = "collecting"

        # 6. Generate Response
        # final_response_text = ""
        
        if new_state.step != "complete":
            # Generate question specifically for missing fields
            print(f"DEBUG: Missing fields -> {missing_fields}")
            question_gen = self.asker(
                current_knowledge=new_state.model_dump_json(),
                missing_info=", ".join(missing_fields)
            )
            next_question = question_gen.question
            
            new_state.last_bot_question = next_question
            response = {'type': 'text', 'text': next_question}
        else:
            response = {'type': 'flex', 'contents': self.generate_flex_json(new_state)}

            new_state.last_bot_question = None

        # 7. Save to DB
        self.update_user_messages(new_state.model_dump())
        
        return response
