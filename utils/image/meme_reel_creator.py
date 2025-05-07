import subprocess
from datetime import datetime
import os
from utils.database.db import get_connection  # ✅ New import

def save_reel_to_database(caption, video_path):
    """
    Saves a new meme reel to the pending_reels database table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pending_reels (caption, video_path, posted)
        VALUES (%s, %s, FALSE)
    """, (caption, video_path))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Reel saved to database: {video_path}")

def create_meme_reel_ffmpeg(image_path, caption, audio_path=None, output_path=None):
    """
    Creates a vertical meme Reel video with optional background audio and saves it to the database.
    
    Args:
        image_path (str): Path to the meme image.
        caption (str): Caption for the meme/reel.
        audio_path (str): Path to the background music (optional).
        output_path (str): Output filename (optional). Defaults to timestamped .mp4 file.
    """

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if audio_path and not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = f"meme_reel_{timestamp}.mp4"

    # Build the ffmpeg command
    command = [
        'ffmpeg',
        '-y',  # Overwrite output file if exists
        '-loop', '1',
        '-i', image_path,
    ]

    if audio_path:
        command += ['-i', audio_path]

    command += [
        '-filter_complex', "[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0015,1.1)':d=125,setsar=1[v]",
        '-map', '[v]',
    ]

    if audio_path:
        command += ['-map', '1:a']

    command += [
        '-c:v', 'libx264',
        '-t', '5',  # 5 seconds long
        '-pix_fmt', 'yuv420p',
        output_path
    ]

    # Run the command
    subprocess.run(command, check=True)
    print(f"✅ Meme Reel created at {output_path}")

    # ✅ After creating the video, save it to the database
    save_reel_to_database(caption, output_path)
