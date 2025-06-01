import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import time
from utils.image import auto_reel

SLEEP_INTERVAL = 60 * 60 * 24  # 24 hours in seconds

while True:
    try:
        print("🌀 Starting daily reel generation...")
        asyncio.run(auto_reel.main())
        print("✅ Reel generation complete.")
    except Exception as e:
        print(f"❌ Error during reel generation: {e}")

    print("😴 Sleeping for 24 hours...")
    time.sleep(SLEEP_INTERVAL)
