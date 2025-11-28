import redis 
from dotenv import load_dotenv
import os


model_dir = os.getenv("MODEL_DIR", "python")
os.sys.path.append(model_dir)
from login_model import UserInfo, LoginSuccessResponse
load_dotenv()



REDIS_HOST =  os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))


redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB
)


def add_user(user_info: UserInfo):
    user_id = user_info.profile.userId if user_info.profile else user_info.email
    redis_client.set(user_id, user_info.json())
    print(f"User {user_id} added to Redis.")
    
def get_user(user_id: str) -> UserInfo | None:
    user_data = redis_client.get(user_id)
    print(f"Retrieved user data for {user_id}: {user_data}")
    if user_data:
        return UserInfo.parse_raw(user_data)
    return None