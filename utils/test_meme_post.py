import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.meme_writer import generate_and_post_meme

if __name__ == "__main__":
    print("🚀 Starting meme test...")
    generate_and_post_meme()
    print("✅ Meme test completed.")
