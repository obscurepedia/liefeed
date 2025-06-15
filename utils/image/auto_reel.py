import os, sys, subprocess, asyncio
import time
import mimetypes
import random
import librosa
import numpy as np

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt, s3_client
from utils.audio.voiceover_generator import generate_voiceover
from openai import OpenAI
from datetime import datetime, timezone
from utils.database.db import get_connection
from PIL import Image
from jinja2 import Environment, FileSystemLoader

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
    "#e1ffd5", "#fff3b0", "#ffe0b3"
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


# ── HTML SLIDE WRITER ──────────────────────────────────────────────
def write_slide(text: str, filename: str, *, fontsize: int = 80, layout: str = "headline", slide_number: str = "", background: str = "#f7f4b2", short_slug: str = None):
    # Engagement prompt CTA (rotating)
    engagement_ctas = ["👇 In the Caption", "🔥 Tap to Read", "❓ Can You Guess?"]
    cta_text = random.choice(engagement_ctas)

    styled_text = emphasize_keywords(text)

    if layout == "teaser":
        emoji = "👀"
    elif layout == "cta":
        emoji = "👉"
    else:
        emoji = "📰"

    # Set background
    if background.endswith(".png") or background.endswith(".jpg"):
        background_style = f"""
            background: linear-gradient(rgba(255,255,255,0.4), rgba(255,255,255,0.4)), url('{background}') no-repeat center center;
            background-size: cover;
        """
    else:
        background_style = f"background: {background};"

    # Add sticker and shortlink (only on CTA slide)
    sticker_html = f'<div class="sticker">{cta_text}</div>' if layout == "cta" else ""
    shortlink_html = f'<div class="short-link">liefeed.com/go/{short_slug}</div>' if layout == "cta" and short_slug else ""

    html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: 1080px;
    height: 1920px;
    {background_style}
    font-family: 'Patrick Hand', cursive;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
  }}
  .safe-zone {{
    position: relative;
    width: 100%;
    height: 100%;
    padding: 250px 40px 400px; /* top / sides / bottom */
    box-sizing: border-box;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  .text-box {{
    background-color: rgba(255,255,255,0.85);
    padding: 40px 60px;
    border-radius: 40px;
    max-width: 900px;
    text-align: center;
    box-shadow: 0 0 20px rgba(0,0,0,0.1);
  }}
  .meme {{
    font-size: {fontsize}px;
    line-height: 1.4;
    color: #111;
    font-weight: bold;
    white-space: pre-wrap;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
  }}
  .highlight {{
    font-weight: 900;
    font-size: 110%;
    color: #d10000;
  }}
  .slide-number {{
    position: absolute;
    bottom: 40px;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 36px;
    color: #555;
    font-family: sans-serif;
  }}
  .sticker {{
    position: absolute;
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%) rotate(-5deg);
    background: #fff;
    border: 3px dashed #222;
    padding: 15px 25px;
    font-size: 50px;
    font-weight: bold;
    color: #d10000;
    box-shadow: 3px 3px 0 #00000033;
    border-radius: 20px;
    font-family: sans-serif;
  }}
  .short-link {{
    position: absolute;
    bottom: 160px;  /* Moved up into safe zone */
    right: 40px;
    font-size: 36px;
    color: #333;
    background: rgba(255,255,255,0.85);
    padding: 12px 24px;
    border-radius: 12px;
    font-family: sans-serif;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.15);
  }}
</style>
<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet">
</head><body>
  <div class="safe-zone">
    <div class="text-box">
      <div class="meme">{emoji} {styled_text}</div>
    </div>
  </div>
  {sticker_html}
  {shortlink_html}
  {f'<div class="slide-number">{slide_number}</div>' if slide_number else ''}
</body></html>
"""

    (SLIDE_DIR / filename).write_text(html, encoding="utf-8")




# ── HTML→PNG ───────────────────────────────────────────────────────

def render_html_slide(template_name: str, context: dict, output_path: str):
    env = Environment(loader=FileSystemLoader("templates"))
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


from mutagen.mp3 import MP3

def stitch_slides(slides: list[str], music: Path, voiceover: Path, output: str):
    import tempfile

    # Get MP3 duration using mutagen
    voice_audio = MP3(str(voiceover))
    voiceover_duration = voice_audio.info.length

    args = []
    filter_parts = []
    input_count = len(slides)

    transition = 1
    slide_duration = voiceover_duration / input_count
    total_duration = voiceover_duration

    for slide in slides:
        slide_path = str(SLIDE_DIR / slide)
        args += ["-loop", "1", "-t", str(slide_duration), "-i", slide_path]

    args += ["-i", str(music)]
    args += ["-i", str(voiceover)]

    for idx in range(input_count):
        motion = "zoompan=z='min(zoom+0.001,1.1)':d=125:s=1080x1920"
        filter_parts.append(f"[{idx}:v]scale=1080:1920,format=rgba,setpts=PTS-STARTPTS,{motion}[v{idx}]")

    xfade_parts = []
    for i in range(input_count - 1):
        input_a = f"[v{i}]" if i == 0 else f"[xf{i-1}]"
        input_b = f"[v{i+1}]"
        tag = f"[xf{i}]"
        offset = (i + 1) * slide_duration
        xfade_parts.append(f"{input_a}{input_b}xfade=transition=slideleft:duration={transition}:offset={offset}{tag}")

    filter_complex = "; ".join(filter_parts + xfade_parts)
    filter_complex += (
        f"; [{input_count}:a]atrim=duration={total_duration},volume=0.2[a1];"
        f"[{input_count + 1}:a]adelay=0|0,volume=1.0[a2];"
        f"[a1][a2]amix=inputs=2:duration=first[aout]"
    )

    final_video = f"[xf{input_count - 2}]" if input_count >= 2 else "[v0]"

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_passlog:
        passlog_file = temp_passlog.name

    first_pass = [
        "ffmpeg", "-y", *args,
        "-filter_complex", filter_complex,
        "-map", final_video,
        "-map", "[aout]",
        "-c:v", "libx264", "-b:v", "12M", "-preset", "veryfast",
        "-r", "30", "-pass", "1", "-passlogfile", passlog_file,
        "-an", "-t", str(total_duration), "-f", "mp4", null_device
    ]

    second_pass = [
        "ffmpeg", "-y", *args,
        "-filter_complex", filter_complex,
        "-map", final_video,
        "-map", "[aout]",
        "-c:v", "libx264", "-b:v", "12M", "-preset", "veryfast",
        "-pass", "2", "-passlogfile", passlog_file,
        "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(total_duration),
        "-shortest", output
    ]

    subprocess.run(first_pass, check=True)
    subprocess.run(second_pass, check=True)





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
    attempts = 0
    while attempts < 10:
        post = fetch_post()
        try:
            hook, twist, cta = generate_story_teaser_slides(post["content"])

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
                print(f"⚠️ Teaser incomplete for post {post['id']}. Skipping...")
                mark_post_used(post["id"])
                increment_failed_attempt(post["id"])
                attempts += 1
                continue  # retry with a new post

            short_slug = generate_short_slug(post["title"])
            save_short_slug(post["id"], short_slug)


            base_prompt = generate_image_prompt(post["title"], post["content"])

            slide_prompts = [
                f"{base_prompt}, setup moment",
                f"{base_prompt}, mid-action twist",
                f"{base_prompt}, curiosity-building aftermath"
            ]
            slide_names = ["hook", "twist", "cta"]
            slide_images = {}

            for i, (prompt, name) in enumerate(zip(slide_prompts, slide_names), start=1):
                image_path = SLIDE_DIR / f"slide{i}_{name}.png"
                image_path.unlink(missing_ok=True)
                result = generate_image_from_prompt(prompt, str(image_path), mode="reel")
                if result is None or not image_path.exists():
                    raise ValueError(f"Image generation failed for slide {name}")
                ensure_exact_1080x1920(image_path)
                slide_images[name] = image_path.name

            break  # success, exit the loop

        except Exception as e:
            print(f"⚠️ Skipping post {post['id']} due to teaser or image issue: {e}")
            mark_post_used(post["id"])
            increment_failed_attempt(post["id"])
            attempts += 1
            post = None

    if not post:
        print("❌ Failed to generate a valid reel after 10 attempts.")
        return

    try:
        counter = get_reel_counter()

        write_slide(hook,  "slide1_hook.html",  fontsize=105, layout="headline", slide_number="1/3", background=slide_images["hook"])
        write_slide(twist, "slide2_twist.html", fontsize=95,  layout="teaser",   slide_number="2/3", background=slide_images["twist"])
        print(f"🧭 Using short_slug for CTA: {short_slug}")
        write_slide(cta, "slide3_cta.html", fontsize=85, layout="cta", slide_number="3/3", background=slide_images["cta"], short_slug=short_slug)

        narration_text = generate_narration_from_teaser(hook)
        cta_line = generate_narrated_cta()
        full_narration = f"{narration_text} {cta_line}. Visit liefeed.com/go/{short_slug}"
        voice_path = "voiceover_teaser.mp3"
        generate_voiceover(full_narration, voice_path)

        await render_html_to_png("slide1_hook.html", "slide1_hook.png")
        await render_html_to_png("slide2_twist.html", "slide2_twist.png")
        await render_html_to_png("slide3_cta.html",   "slide3_cta.png")

        stitch_slides(
            ["slide1_hook.png", "slide2_twist.png", "slide3_cta.png"],
            MUSIC_FILE, Path(voice_path), OUTPUT_VIDEO
        )

        mark_post_used(post["id"])
        increment_reel_counter()

        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"reels/{date_str}/{int(time.time())}_reel.mp4"
        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )

        full_url = f"https://liefeed.com/post/{post['slug']}"
        caption_with_link = f"Follow LieFeed for daily absurdity\n\nRead more 👉 {full_url}"
        save_reel_to_database(caption_with_link, S3_REEL_KEY)

    except Exception as e:
        print(f"❌ Error during reel generation: {e}")
        increment_failed_attempt(post["id"])




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


if __name__ == "__main__":
    asyncio.run(main())

