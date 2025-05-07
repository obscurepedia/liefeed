import sys
import os
import random
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image.meme_writer import generate_and_post_meme

if __name__ == "__main__":
    delay_minutes = random.randint(0, 30)  # Wait between 0 and 30 minutes
    print(f"🕒 Random delay: waiting {delay_minutes} minutes before posting meme...")
    time.sleep(delay_minutes * 60)  # Delay in seconds
    generate_and_post_meme()
