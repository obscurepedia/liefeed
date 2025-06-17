# Assuming these imports are at the top of auto_reel.py
import os, sys, subprocess, asyncio
import time
import mimetypes
import random
import librosa
import numpy as np
from pathlib import Path
from playwright.async_api import async_playwright
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt, s3_client
from utils.audio.voiceover_generator import generate_voiceover
from openai import OpenAI
from datetime import datetime, timezone
from utils.database.db import get_connection
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from mutagen.mp3 import MP3 # NEW: Import for MP3 duration
import tempfile # NEW: Import for temporary files

# ── CONFIG ─────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client  = OpenAI(api_key=OPENAI_API_KEY)

SLIDE_DIR     = Path("slides")
OUTPUT_VIDEO  = "reel.mp4"
SLIDE_DIR.mkdir(exist_ok=True)

track_list = os.getenv("MUSIC_TRACKS", "").split(",")
selected_track = random.choice(track_list).strip()
MUSIC_FILE = Path(__file__).resolve().parents[2] / "static" / selected_track

REEL_COLORS = [
    "#f7f4b2", "#fbd5e0", "#d0f0fd",
    "#e1ffd5", "#fff3b0", # Example colors, ensure you have enough
    "#ffccdd", "#ccffdd", "#ddccff", "#ffeecc", "#ccddee",
    "#aaddff", "#ffccff", "#ccffee", "#eeccff", "#ddffcc"
]

null_device = "NUL" if os.name == "nt" else "/dev/null"

# ── DB HELPERS ─────────────────────────────────────────────────────
def fetch_post():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, content, slug
            FROM posts
            WHERE used_in_reel IS NOT TRUE
              AND (reel_failed_attempts IS NULL OR reel_failed_attempts < 3)
            ORDER BY created_at ASC
            LIMIT 1
        """)
        row = cur.fetchone()
    conn.close()
    if not row:
        raise Exception("No eligible posts found (all used or failed too many times).")
    return {"id": row[0], "title": row[1], "content": row[2], "slug": row[3]}

def get_reel_counter():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT setting_value FROM site_settings WHERE setting_key = 'reel_counter'")
        result = cur.fetchone()
        if result:
            return int(result[0])
        cur.execute("INSERT INTO site_settings (setting_key, setting_value) VALUES ('reel_counter', '1')")
        conn.commit()
        return 1
    conn.close()

def increment_reel_counter():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE site_settings AS s
            SET setting_value = (s.setting_value::int + 1)::text
            WHERE s.setting_key = 'reel_counter'
        """)
        conn.commit()
    conn.close()

def mark_post_used(post_id: int):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE posts SET used_in_reel = TRUE WHERE id = %s", (post_id,))
        conn.commit()
    conn.close()

def increment_failed_attempt(post_id: int):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE posts
            SET reel_failed_attempts = reel_failed_attempts + 1
            WHERE id = %s
        """, (post_id,))
        conn.commit()
    conn.close()

import hashlib
import re

def generate_short_slug(title):
    # Extract lowercase words of at least 3 letters
    words = re.findall(r'\b[a-z]{3,}\b', title.lower())
    if not words:
        words = ["post"]
    keyword = random.choice(words)[:4]  # Take first 4 letters of a word
    hash_suffix = hashlib.md5(title.encode()).hexdigest()[:3]  # Short hash to ensure uniqueness
    return f"{keyword}{hash_suffix}"



def save_short_slug(post_id, slug):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE posts SET short_slug = %s WHERE id = %s", (slug, post_id))
        conn.commit()
    conn.close()

# In auto_reel.py, locate your sanitize_prompt function and modify it as follows:

def sanitize_prompt(prompt):
    banned_keywords = [
        "Trump", "Putin", "Musk", "sexual", "celebrity", "Ukraine", "Russia",
        "politics", "political", "election", "candidate", "government",
        "violence", "bloody", "weapon", "gun", "knife", "bomb", "attack",
        "hate", "racist", "sexist", "discriminatory", "nude", "porn",
        "explicit", "gore", "drug", "alcohol", "smoking", "vaping",
        "terrorist", "terrorism", "extremist", "propaganda", "insurrection",
        "riot", "protest", "controversial", "disaster", "tragedy",
        "illness", "disease", "death", "injury", "accident", "hospital",
        "medical", "doctor", "nurse",
        "religious", "religion", "church", "mosque", "temple", "holy",
        "money", "financial", "bank", "stock market", "economy", "debt",
        "legal", "court", "judge", "police", "crime", "criminal", "prison",
        "military", "soldier", "war", "battle", "conflict",
        "children", "kid", "baby", "teenager",
        "animal cruelty", "abuse", "torture", "suffering",
        "disability", "disabled", "handicap",
        "crisis", "scandal", "controversy", "expose", "secret", "conspiracy",
        "threat", "danger", "harm", "unethical", "immoral"
    ]

    contains_banned = False
    lower_prompt = prompt.lower()

    for word in banned_keywords:
        if word.lower() in lower_prompt:
            contains_banned = True
            # Replace the matched part in the original prompt
            start = 0
            while True:
                idx = lower_prompt.find(word.lower(), start)
                if idx == -1:
                    break
                prompt = prompt[:idx] + "[REDACTED]" + prompt[idx + len(word):]
                # Adjust lower_prompt as well to avoid re-matching the redacted part
                lower_prompt = lower_prompt[:idx] + "[REDACTED]" + lower_prompt[idx + len(word):]
                start = idx + len("[REDACTED]")

    return prompt, contains_banned

def try_leonardo_then_hf(prompt, output_path):
    from utils.image.image_generator import generate_image_from_prompt

    # Force Leonardo first
    try:
        print("🎨 Trying Leonardo first...")
        result = generate_image_from_prompt(prompt, output_path, mode="reel")
        if result is not None and os.path.exists(output_path):
            return result
        raise Exception("Leonardo returned no image.")
    except Exception as e:
        print(f"⚠️ Leonardo failed: {e}")
        print("🔁 Falling back to Hugging Face...")
        # Now use generate_image_from_prompt again, but this time trigger HF logic by passing mode other than 'reel'
        try:
            return generate_image_from_prompt(prompt, output_path, mode="fallback")
        except Exception as hf_error:
            print(f"❌ Hugging Face also failed: {hf_error}")
            return None


# ── TEXT BREAKDOWN ────────────────────────────────────────────────

def generate_story_teaser_slides(post_text: str):
    prompt = f"""
You are a witty video editor converting the following satirical article into a short 3-slide video teaser.

Break it into:
1. A short, punchy HOOK
2. A mid-story TWIST
3. A SPOKEN-STYLE CTA

Each part must be 1 sentence max. Don’t spoil the ending.

Article:
{post_text}

Format:
HOOK:
TWIST:
CTA:
"""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw = resp.choices[0].message.content.strip()
        print("🔍 RAW COMPLETION:\n", raw)

        # Improved parsing logic
        hook = ""
        twist = ""
        cta = ""
        current = None

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith("HOOK"):
                current = "hook"
                continue
            elif line.upper().startswith("TWIST"):
                current = "twist"
                continue
            elif line.upper().startswith("CTA"):
                current = "cta"
                continue

            if current == "hook":
                hook = line.strip('"')
                current = None
            elif current == "twist":
                twist = line.strip('"')
                current = None
            elif current == "cta":
                cta = line.strip('"')
                current = None

        return hook, twist, cta

    except Exception as e:
        print(f"❌ OpenAI teaser generation failed: {e}")
        return "", "", ""



def generate_narration_from_teaser(teaser: str) -> str:
    prompt = f"""
Take this teaser text and turn it into a short, casual spoken sentence for narration.

Teaser: "{teaser.strip()}"

Voiceover:
"""
    resp = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()


def generate_narrated_cta() -> str:
    options = [
        "Want more? The link’s just below.",
        "You’ll find the full story in the caption.",
        "Check the caption for the rest.",
        "It gets better — scroll down for the link."
    ]
    return random.choice(options)


def ensure_exact_1080x1920(image_path: Path):
    try:
        with Image.open(image_path) as img:
            if img.size != (1080, 1920):
                img = img.resize((1080, 1920), Image.LANCZOS)
                img.save(image_path)
    except Exception as e:
        print(f"❌ Failed to resize {image_path.name}: {e}")



def extract_beat_timestamps(audio_path: str, max_beats: int = 4):
    y, sr = librosa.load(audio_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Return only the first `max_beats + 1` timestamps for n slides (need n+1 marks)
    return beat_times[:max_beats + 1].tolist()

import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import stopwords

# Ensure necessary resources are downloaded
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

def emphasize_keywords(text):
    words = word_tokenize(text)
    tagged = pos_tag(words)

    # POS tags to prioritize: nouns (NN, NNP, NNS), verbs (VB*), adjectives (JJ*)
    priority_tags = {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS'}
    
    # Identify candidate indices
    candidate_indices = [i for i, (_, tag) in enumerate(tagged) if tag in priority_tags]

    if not candidate_indices:
        return text  # fallback to original if no good matches

    num_to_emphasize = min(2, len(candidate_indices))
    selected_indices = random.sample(candidate_indices, num_to_emphasize)

    for i in selected_indices:
        words[i] = f'<span class="highlight">{words[i]}</span>'

    return " ".join(words)

# ── SLIDE WRITER ───────────────────────────────────────────────────
CURRENT_DIR = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader(CURRENT_DIR / "templates"))
template = env.get_template("slide_template.html")

# In your auto_reel.py file, locate the write_slide function and update it as follows:

def write_slide(text: str, filename: str, fontsize: int, layout: str, slide_number: str, background: str = None, background_color: str = None, short_slug: str = None):
    """
    Writes HTML content for a slide based on a template.
    """
    # Initialize variables that will be passed to the template
    template_text = text # This will be the main content of the slide
    template_sticker_text = None
    template_emoji_prefix = "" # This will be used to prepend emoji if needed

    if layout == "cta":
        # For the CTA slide, the user wants ONLY the main CTA text.
        # So, no sticker and no emoji prefix from the template.
        template_sticker_text = None
        template_emoji_prefix = ""

    elif layout == "link_only":
        # For the link_only slide, the 'text' argument already contains the emoji and the link.
        # So, no separate sticker or emoji prefix is needed from the template.
        template_sticker_text = None
        template_emoji_prefix = ""
        # The template_text will be "👇 liefeed.com/go/" + short_slug, as passed in the call.

    html_content = template.render(
        text=template_text, # This carries the actual content (including emoji for slide 4)
        fontsize=fontsize,
        layout=layout,
        slide_number=slide_number,
        background_image=background,
        background_color=background_color,
        sticker_text=template_sticker_text, # Will be None for both relevant layouts
        emoji=template_emoji_prefix, # Will be "" for both relevant layouts
        short_slug=short_slug # Still passed, but template won't use it directly for rendering content
    )
    (SLIDE_DIR / filename).write_text(html_content, encoding="utf-8")


# ── HTML→PNG ───────────────────────────────────────────────────────

def render_html_slide(template_name: str, context: dict, output_path: str):
    global CURRENT_DIR # If CURRENT_DIR is defined globally, ensure it's accessible.
    env = Environment(loader=FileSystemLoader(CURRENT_DIR / "templates"))
    template = env.get_template(template_name)
    rendered_html = template.render(context)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)


async def render_html_to_png(html_file: str, png_file: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width":1080,"height":1920})
        await page.goto(f"file:///{(SLIDE_DIR/html_file).resolve()}")
        await page.wait_for_load_state('networkidle')
        await page.screenshot(
            path=SLIDE_DIR / png_file,
            clip={"x":0,"y":0,"width":1080,"height":1920}
        )
        await browser.close()


# ── FFmpeg Stitcher ────────────────────────────────────────────────
def stitch_slides(slides: list[str], music: Path, voiceover: Path, output: str):
    """
    Stitches generated slide images, music, and voiceover into a final video reel.

    Args:
        slides (list[str]): List of PNG filenames for each slide.
        music (Path): Path to the background music file.
        voiceover (Path): Path to the voiceover audio file.
        output (str): Output filename for the final MP4 video.
    """
    print("🎬 Stitching slides...")
    voice_audio = MP3(str(voiceover))
    voiceover_duration = voice_audio.info.length

    input_count = len(slides) # This will now be 4
    transition = 1 # duration of transition between slides (seconds)

    # Define durations for each slide
    # First 3 slides share the voiceover duration, last slide gets extra time
    narrated_slide_count = 3 # HOOK, TWIST, CTA text slides are narrated
    
    # Avoid division by zero if voiceover_duration is extremely short or 0
    if voiceover_duration > 0 and narrated_slide_count > 0:
        duration_per_narrated_slide = voiceover_duration / narrated_slide_count
    else:
        duration_per_narrated_slide = 2.0 # Default short duration if no voiceover or narrated slides

    link_slide_extra_duration = 4.0 # Seconds for the link slide to stay on screen

    individual_slide_durations = [duration_per_narrated_slide] * narrated_slide_count
    individual_slide_durations.append(link_slide_extra_duration) # Add duration for the 4th slide

    # Calculate total video duration by summing all individual slide durations
    total_visual_duration = sum(individual_slide_durations)

    # Ensure total video duration is at least as long as the voiceover
    total_visual_duration = max(total_visual_duration, voiceover_duration)

    args = []
    filter_parts = []
    
    # Add input arguments for each slide image
    for i, slide in enumerate(slides):
        slide_path = str(SLIDE_DIR / slide)
        current_slide_duration = individual_slide_durations[i]
        args += ["-loop", "1", "-t", str(current_slide_duration), "-i", slide_path]

        # Apply zoompan or other motion effect
        motion = "zoompan=z='min(zoom+0.001,1.1)':d=125:s=1080x1920"
        filter_parts.append(f"[{i}:v]scale=1080:1920,format=rgba,setpts=PTS-STARTPTS,{motion}[v{i}]")

    # Add music and voiceover inputs (indices input_count and input_count + 1)
    args += ["-i", str(music)]
    args += ["-i", str(voiceover)]

    # X-fade transitions for 4 slides (3 transitions)
    xfade_parts = []
    accumulated_offset = 0.0 # Use float for precise accumulation
    for i in range(input_count - 1): # This loop will run for i=0, 1, 2 (for 4 slides)
        input_a = f"[v{i}]" if i == 0 else f"[xf{i-1}]"
        input_b = f"[v{i+1}]"
        tag = f"[xf{i}]"
        
        # Calculate offset for each transition based on individual slide durations
        accumulated_offset += individual_slide_durations[i]
        xfade_parts.append(f"{input_a}{input_b}xfade=transition=slideleft:duration={transition}:offset={accumulated_offset}{tag}")

    filter_complex = "; ".join(filter_parts + xfade_parts)

    # Determine the final video stream from the last xfade output (for 4 slides, it's xf2)
    final_video_stream = f"[xf{input_count - 2}]"

    # Audio mixing: music and voiceover
    # Ensure background music lasts for the total visual duration
    filter_complex += (
        f"; [{input_count}:a]atrim=duration={total_visual_duration},volume=0.2[a1];" # Music input is at index `input_count`
        f"[{input_count + 1}:a]adelay=0|0,volume=1.0[a2];" # Voiceover input is at index `input_count + 1`
        f"[a1][a2]amix=inputs=2:duration=first[aout]"
    )

    # Use null_device for the first pass output to discard video but log pass data
    if sys.platform == "win32":
        null_device = "NUL"
    else:
        null_device = "/dev/null"

    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as temp_passlog:
        passlog_file = temp_passlog.name

    first_pass = [
        "ffmpeg", "-y", *args,
        "-filter_complex", filter_complex,
        "-map", final_video_stream,
        "-map", "[aout]",
        "-c:v", "libx264", "-b:v", "12M", "-preset", "veryfast",
        "-r", "30", "-pass", "1", "-passlogfile", passlog_file,
        "-an", "-t", str(total_visual_duration), "-f", "mp4", null_device
    ]

    second_pass = [
        "ffmpeg", "-y", *args,
        "-filter_complex", filter_complex,
        "-map", final_video_stream,
        "-map", "[aout]",
        "-c:v", "libx264", "-b:v", "12M", "-preset", "veryfast",
        "-pass", "2", "-passlogfile", passlog_file,
        "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(total_visual_duration), # Set total video duration here
        "-shortest", output
    ]

    try:
        subprocess.run(first_pass, check=True)
        subprocess.run(second_pass, check=True)
        print(f"✅ Reel generated at: {output}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        print(f"FFmpeg stdout: {e.stdout.decode()}")
        print(f"FFmpeg stderr: {e.stderr.decode()}")
        raise
    finally:
        # Clean up pass log file
        if os.path.exists(passlog_file):
            os.remove(passlog_file)



def save_reel_to_database(caption, s3_key):
    """
    Saves a new reel to the pending_reels database table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pending_reels (caption, video_path, posted)
        VALUES (%s, %s, FALSE)
    """, (caption, s3_key))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Reel saved to database: {s3_key}")

# ── MAIN PIPELINE ─────────────────────────────────────────────────
async def main():
    """
    Main pipeline to generate and upload a satirical news reel.
    """
    attempts = 0
    post = None # Initialize post to None
    while attempts < 10:
        fetched_post = fetch_post()
        if not fetched_post:
            print("⚠️ No new posts available for reel generation. Exiting.")
            return # Exit if no posts left to try

        try:
            hook, twist, cta = generate_story_teaser_slides(fetched_post["content"])

            # Clean extra quotes
            hook = hook.strip('"')
            twist = twist.strip('"')
            cta = cta.strip('"')

            print("📋 Teaser breakdown:")
            print(f"HOOK:  {hook!r}")
            print(f"TWIST: {twist!r}")
            print(f"CTA:   {cta!r}")

            # If any of the teaser parts are blank, skip the post
            if not hook.strip() or not twist.strip() or not cta.strip():
                print(f"⚠️ Teaser incomplete for post {fetched_post['id']}. Skipping...")
                mark_post_used(fetched_post["id"])
                increment_failed_attempt(fetched_post["id"])
                attempts += 1
                continue  # retry with a new post

            post = fetched_post # Assign to 'post' for the rest of the try block
            
            short_slug = generate_short_slug(post["title"])
            save_short_slug(post["id"], short_slug)

            base_prompt = generate_image_prompt(post["title"], post["content"])

            # === NEW LOGIC START: Check base prompt for banned words ===
            # Sanitize the base prompt and get the flag
            base_prompt, contains_banned_words_in_base = sanitize_prompt(base_prompt)

            if contains_banned_words_in_base:
                print(f"⚠️ Base prompt for post {fetched_post['id']} contains banned words. Skipping this post to avoid API rejections.")
                mark_post_used(fetched_post["id"])
                increment_failed_attempt(fetched_post["id"])
                attempts += 1
                post = None # Reset post for next attempt
                continue # Skip to the next iteration of the while loop (fetch a new post)
            # === NEW LOGIC END ===

            # Generate 3 images: hook, twist, and one image for both CTA text and the final link slide
            slide_prompts = [
                f"{base_prompt}, setup moment", # base_prompt is now the cleaned version
                f"{base_prompt}, mid-action twist",
                f"{base_prompt}, curiosity-building aftermath", # This image will be used for slide 3
                f"{base_prompt}, clear focus on the call-to-action"
            ]
            slide_names = ["hook", "twist", "cta", "link"] # Names corresponding to the image use
            slide_images = {} # Stores image filenames

            for i, (prompt, name) in enumerate(zip(slide_prompts, slide_names), start=1):
                print(f"🎨 Generating image for slide {i} ({name})...")
                image_path = SLIDE_DIR / f"slide{i}_{name}.png"
                image_path.unlink(missing_ok=True)  # Clean up old image if exists

                # Sanitize each individual slide prompt (will redact words, but decision to skip was already made)
                clean_prompt, _ = sanitize_prompt(prompt) # Use clean_prompt, ignore the flag here
                print(f"🧪 Prompt sent to image generator: {clean_prompt}")

                result = try_leonardo_then_hf(clean_prompt, str(image_path))

                if result is None or not image_path.exists():
                    raise ValueError(f"Image generation failed for slide {name} (Leonardo & HF)")

                ensure_exact_1080x1920(image_path)
                slide_images[name] = image_path.name  # Store just the filename


        except Exception as e:
            print(f"⚠️ Skipping post {fetched_post['id']} due to teaser or image issue: {e}")
            mark_post_used(fetched_post["id"])
            increment_failed_attempt(fetched_post["id"])
            attempts += 1
            post = None # Reset post for next attempt


    if not post:
        print("❌ Failed to generate a valid reel after 10 attempts.")
        return # Exit if no valid post was found after all attempts

    try:
        # Counter management (if needed for unique naming beyond slug)
        # counter = get_reel_counter() # Uncomment if you use this

        # Slide 1: Hook (1/4)
        write_slide(hook, "slide1_hook.html", fontsize=105, layout="headline", slide_number="1/4", background=slide_images["hook"])
        
        # Slide 2: Twist (2/4)
        write_slide(twist, "slide2_twist.html", fontsize=95, layout="teaser", slide_number="2/4", background=slide_images["twist"])
        
        # Slide 3: CTA Text (3/4) - uses 'cta' image as background
        print(f"🧭 Using short_slug for CTA on slide 3: {short_slug}")
        write_slide(cta, "slide3_cta.html", fontsize=85, layout="cta", slide_number="3/4", background=slide_images["cta"], short_slug=short_slug)

        # Slide 4: Dedicated Link (4/4) - uses the *same* 'cta' image as background
        print(f"🧭 Using short_slug for final link slide 4: {short_slug}")
        write_slide(
            "👇 liefeed.com/go/" + short_slug, # Prominent emoji and the link text
            "slide4_link.html",
            fontsize=85, # Adjust as needed for prominence
            layout="link_only", # New layout type for specific styling
            slide_number="4/4",
            background=slide_images["link"], 
            short_slug=short_slug # Pass short_slug for link rendering in template
        )

        # Voiceover Generation
        narration_text = generate_narration_from_teaser(hook)
        cta_line = generate_narrated_cta()
        # NEW: Remove the direct link mention from the voiceover, as it's now prominently on the dedicated 4th slide
        full_narration = f"{narration_text} {cta_line}" 
        voice_path = "voiceover_teaser.mp3"
        generate_voiceover(full_narration, voice_path)

        # Render HTML to PNG for all 4 slides
        await render_html_to_png("slide1_hook.html", "slide1_hook.png")
        await render_html_to_png("slide2_twist.html", "slide2_twist.png")
        await render_html_to_png("slide3_cta.html", "slide3_cta.png")
        await render_html_to_png("slide4_link.html", "slide4_link.png") # Render the new 4th slide

        # Stitch all 4 slides together
        stitch_slides(
            ["slide1_hook.png", "slide2_twist.png", "slide3_cta.png", "slide4_link.png"], # Updated list to include 4th slide
            MUSIC_FILE, Path(voice_path), OUTPUT_VIDEO
        )

        mark_post_used(post["id"])
        increment_reel_counter() # Increment the reel counter if you use it for unique filenames/tracking

        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"reels/{date_str}/{int(time.time())}_reel.mp4"
        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )
        print(f"✅ Uploaded to S3: {S3_REEL_KEY}")

        full_url = f"https://liefeed.com/post/{post['slug']}"
        caption_with_link = f"Follow LieFeed for daily absurdity\n\nRead more 👉 {full_url}"
        save_reel_to_database(caption_with_link, S3_REEL_KEY)
        print(f"✅ Reel saved to database.")

    except Exception as e:
        print(f"❌ Error during reel generation: {e}")
        if post: # Only increment failed attempt if a post was successfully fetched initially
            increment_failed_attempt(post["id"])
        # Optionally, mark post as failed or retry logic here
    print("✅ Reel generation complete.")



async def generate_quiz_ad_reel():
    try:
        # === Static Headlines for Spot-the-Fake ===
        real_headline = "Florida Man Rescues Iguana with CPR"
        fake_headline = "NASA Discovers Moon Made of Cheese Dust"
        teaser = "Only 3% Guess Correctly — Can You Spot the Fake?"
        quiz_url = "https://liefeed.com/quiz/start"

        bg_color = random.choice(REEL_COLORS)

        # === Slide 1: Headline Challenge ===
        challenge_text = f"One of these is real\nOne is fake\n\n- {real_headline}\n- {fake_headline}"
        write_slide(challenge_text, "slide1_headlines.html", fontsize=75, layout="headline", background_color=bg_color)

        # === Slide 2: AI Meme Image ===
        prompt = f"A surreal scene showing someone confused, holding two newspapers, one absurd, one real"
        slide2_path = SLIDE_DIR / "slide2_image.png"
        slide2_path.parent.mkdir(exist_ok=True)
        slide2_path.unlink(missing_ok=True)

        result = generate_image_from_prompt(prompt, str(slide2_path), mode="reel")

        if result is None or not slide2_path.exists():
            raise FileNotFoundError("slide2_image.png was not created")

        time.sleep(1)
        ensure_exact_1080x1920(slide2_path)

        # === Slide 3: Teaser ===
        write_slide(teaser, "slide3_teaser.html", fontsize=90, layout="teaser", slide_number="3/4", background_color=bg_color)

        # === Slide 4: CTA ===
        cta_text = "Tap to Start the Quiz"
        write_slide(cta_text, "slide4_cta.html", fontsize=90, layout="cta", slide_number="4/4", background_color=bg_color)

        # === Render Slides ===
        await render_html_to_png("slide1_headlines.html", "slide1_headlines.png")
        await render_html_to_png("slide3_teaser.html", "slide3_teaser.png")
        await render_html_to_png("slide4_cta.html", "slide4_cta.png")

        print(f"🎵 Selected music file: {MUSIC_FILE}")
        print(f"🎧 Exists? {MUSIC_FILE.exists()}")


        # === Stitch Video ===
        stitch_slides(
            ["slide1_headlines.png", "slide2_image.png", "slide3_teaser.png", "slide4_cta.png"],
            MUSIC_FILE,
            OUTPUT_VIDEO
        )

        # === Upload to S3 + Save to DB ===
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"quiz_ads/spot_the_fake/{date_str}_{int(time.time())}_quiz_ad.mp4"

        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )

        reel_url = f"https://liefeed-images.s3.us-east-1.amazonaws.com/{S3_REEL_KEY}"
        caption_with_link = f"{teaser}\n\nTake the quiz 👉 {quiz_url}"
        save_reel_to_database(caption_with_link, S3_REEL_KEY)

        print("✅ Quiz ad reel generated successfully.")

    except Exception as e:
        print(f"❌ Failed to generate quiz ad reel: {e}")

async def generate_quiz_confusion_reel():
    try:
        # === Headlines for Real vs Fake Confusion ===
        headlines = [
            "Scientists teach parrots to video call each other",
            "Texas town elects goat as honorary mayor",
            "AI bot wins international poetry contest",
        ]
        teaser = "Take the quiz. Stop at Q3 if you dare."
        quiz_url = "https://liefeed.com/quiz/start"

        bg_color = random.choice(REEL_COLORS)

        # === Slide 1: Challenge Prompt ===
        write_slide("Can you tell which of these\nheadlines is real?", "confusion_slide1.html",
                    fontsize=80, layout="headline", background_color=bg_color)

        # === Slide 2: Flash 2–3 headlines in rapid succession ===
        rapid_headlines = "\n".join(f"• {h}" for h in headlines)
        write_slide(rapid_headlines, "confusion_slide2.html",
                    fontsize=60, layout="teaser", slide_number="2/3", background_color=bg_color)

        # === Slide 3: Teaser / CTA ===
        write_slide(teaser, "confusion_slide3.html",
                    fontsize=85, layout="cta", slide_number="3/3", background_color=bg_color)

        # === Render Slides to PNG ===
        await render_html_to_png("confusion_slide1.html", "confusion_slide1.png")
        await render_html_to_png("confusion_slide2.html", "confusion_slide2.png")
        await render_html_to_png("confusion_slide3.html", "confusion_slide3.png")

        # === Stitch into Reel ===
        stitch_slides(
            ["confusion_slide1.png", "confusion_slide2.png", "confusion_slide3.png"],
            MUSIC_FILE,
            OUTPUT_VIDEO
        )

        # === Upload to S3 and Save ===
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"quiz_ads/confusion_reel/{date_str}_{int(time.time())}_confusion_ad.mp4"

        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )

        reel_url = f"https://liefeed-images.s3.us-east-1.amazonaws.com/{S3_REEL_KEY}"
        caption = f"Can you still tell what’s real?\n\nTake the quiz 👉 {quiz_url}"
        save_reel_to_database(caption, S3_REEL_KEY)

        print("✅ Confusion quiz ad reel generated successfully.")

    except Exception as e:
        print(f"❌ Failed to generate confusion quiz reel: {e}")

async def generate_quiz_spy_reel():
    try:
        # === Spy Theme Setup ===
        teaser = "Simulation Active. Classify these headlines."
        quiz_url = "https://liefeed.com/quiz/start"
        bg_color = "#dddddd"  # Dark, classified-style background

        # === Slide 1: Agent Briefing ===
        intro_text = "🕵️ Agent Briefing\n\nYour mission:\nClassify real vs fake headlines"
        write_slide(intro_text, "spy_slide1.html",
                    fontsize=75, layout="headline", background_color=bg_color)

        # === Slide 2: Redacted / Glitched Headlines ===
        redacted_headlines = [
            "••• DISCOVERS INVISIBLE COWS",
            "NASA ••• MOON LANDING IN QUESTION",
            "FLORIDA MAN ••• IGUANA CPR HEROICS"
        ]
        glitch_text = "\n".join(redacted_headlines)
        write_slide(glitch_text, "spy_slide2.html",
                    fontsize=60, layout="teaser", slide_number="2/3", background_color=bg_color)

        # === Slide 3: Simulation Activation ===
        final_slide = "🔴 SIMULATION ACTIVE\nBegin your mission now"
        write_slide(final_slide, "spy_slide3.html",
                    fontsize=85, layout="cta", slide_number="3/3", background_color=bg_color)

        # === Render Slides ===
        await render_html_to_png("spy_slide1.html", "spy_slide1.png")
        await render_html_to_png("spy_slide2.html", "spy_slide2.png")
        await render_html_to_png("spy_slide3.html", "spy_slide3.png")

        # === Stitch Together ===
        stitch_slides(
            ["spy_slide1.png", "spy_slide2.png", "spy_slide3.png"],
            MUSIC_FILE,
            OUTPUT_VIDEO
        )

        # === Upload to S3 and Save ===
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"quiz_ads/spy_reel/{date_str}_{int(time.time())}_spy_ad.mp4"

        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )

        reel_url = f"https://liefeed-images.s3.us-east-1.amazonaws.com/{S3_REEL_KEY}"
        caption = f"🕵️‍♂️ Your mission: Classify these headlines\n\nBegin the quiz 👉 {quiz_url}"
        save_reel_to_database(caption, S3_REEL_KEY)

        print("✅ Spy-themed quiz ad reel generated successfully.")

    except Exception as e:
        print(f"❌ Failed to generate spy quiz reel: {e}")


# ── Entry Point ──────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())