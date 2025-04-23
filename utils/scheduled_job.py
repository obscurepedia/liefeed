import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.post_writer import generate_and_save_post

if __name__ == "__main__":
    generate_and_save_post()
