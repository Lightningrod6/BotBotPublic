# rate_limiter.py

import redis # Dictionary to store the time of the last command used by each user
import os
import dotenv

dotenv.load_dotenv()
redis_client = redis.Redis(host="viaduct.proxy.rlwy.net", port="50252", db=0, username="default", password="GAawJgwsGELNbByMdeTSQwwSgZkaghFe")

def check_rate_limit(user_id, command, limit=5, per=60):
    key = f"rate_limit:{command}:{str(user_id)}"

    current_count = redis_client.get(key)

    if current_count is not None:
        if int(current_count) >= limit or int(current_count) < 0:
            return False
        else:
            redis_client.incr(key)
    else:
        redis_client.set(key, 1, ex=per)
    return True