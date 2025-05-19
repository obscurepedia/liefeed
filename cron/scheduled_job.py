import sys
import os
import random
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai.post_writer import generate_and_save_post
from utils.social.post_facebook_comments import post_queued_comments

if __name__ == "__main__":
    delay_minutes = random.randint(0, 30)
    print(f"🕒 Random delay: waiting {delay_minutes} minutes before posting article...")
    time.sleep(delay_minutes * 60)

    generate_and_save_post()

    print("⏳ Waiting 5 minutes before posting comment...")
    time.sleep(5 * 60)

    print("💬 Running comment posting...")
    post_queued_comments()
