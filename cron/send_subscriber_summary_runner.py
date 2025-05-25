import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from utils.email.send_subscriber_summary import main

if __name__ == "__main__":
    print("📬 Running subscriber summary...")
    main()
