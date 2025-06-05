import os, sys, subprocess, asyncio
import time
import mimetypes
import random


from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt, s3_client
from openai import OpenAI
from datetime import datetime, timezone
from utils.database.db import get_connection
from PIL import Image


# ── CONFIG ─────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client  = OpenAI(api_key=OPENAI_API_KEY)

SLIDE_DIR     = Path("slides")
OUTPUT_VIDEO  = "reel.mp4"
SLIDE_DIR.mkdir(exist_ok=True)

track_list = os.getenv("MUSIC_TRACKS", "").split(",")
selected_track = random.choice(track_list).strip()
MUSIC_FILE = Path(__file__).resolve().parents[2] / "static" / selected_track

# --- SETTINGS ---
REEL_ROTATION_KEY = "reel_cta_counter"
FOLLOW_REEL_INTERVAL = 5

REEL_COLORS = [
    "#f7f4b2",  # pale yellow
    "#fbd5e0",  # soft pink
    "#d0f0fd",  # sky blue
    "#e1ffd5",  # mint green
    "#fff3b0",  # cream
    "#ffe0b3",  # peach
]


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


# --- HELPER TO FETCH & INCREMENT CTA COUNTER ---
def get_reel_counter():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT setting_value FROM site_settings WHERE setting_key = 'reel_counter'")
        result = cur.fetchone()
        if result:
            return int(result[0])
        else:
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

# --- HELPER TO FETCH & INCREMENT FAILED ATTEMPT COUNTER ---
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


# ── TEXT TEASER ────────────────────────────────────────────────────
def generate_teaser(article: str) -> str:
    prompt = f"""
You're a viral copywriter for a tabloid-style satire news site. Your job is to write irresistibly clicky, funny, and slightly outrageous teaser lines that make viewers desperate to click and read more.

Rules:
- MAX 15 words
- No periods
- Use emotional triggers (shock, curiosity, disbelief)
- Sound human — avoid AI awkwardness
- Always match the tone of modern social media bait
- Avoid summarizing the whole article — just tease the wildest part
- DO NOT include any CTA or link references

Article:
{article}

Now write the teaser:
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You write clickbait teaser copy for social media reels"},
            {"role": "user", "content": prompt}
        ]
    )
    return resp.choices[0].message.content.strip()


def generate_cta(teaser: str, counter: int) -> str:
    if counter % 5 == 0:
        return "Follow LieFeed for daily absurdity"
    return generate_cta_from_teaser(teaser)



def generate_cta_from_teaser(teaser: str) -> str:
    prompt = f"""
You're a viral social media copywriter.

Write a **short curiosity-driven CTA** that encourages the viewer to tap or slide to read the full satirical article.

Use this teaser as context:
"{teaser}"

Rules:
- Max 10 words
- Start with an action word: Tap, Slide, Reveal, Discover, or Read
- Create mystery or urgency (without clickbait)
- Avoid generic phrases like “click here” or “see more”
- DO NOT use punctuation or quotation marks
- Return only the CTA text
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You write curiosity-driven CTA lines for satirical news content."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=30
    )

    return resp.choices[0].message.content.strip()



def ensure_exact_1080x1920(image_path: Path):
    try:
        with Image.open(image_path) as img:
            if img.size != (1080, 1920):
                print(f"🛠️ Resizing {image_path.name} from {img.size} to (1080, 1920)")
                img = img.resize((1080, 1920), Image.LANCZOS)
                img.save(image_path)
    except Exception as e:
        print(f"❌ Failed to resize {image_path.name}: {e}")


# ── HTML SLIDE WRITER ──────────────────────────────────────────────
def write_slide(text: str, filename: str, *, fontsize: int = 80, layout: str = "headline", slide_number: str = "", background_color: str = "#f7f4b2"):
    if layout == "teaser":
        align_css = "align-items: center; justify-content: flex-start; padding-top: 150px;"
        font_weight = "normal"
        emoji = "👀"
    elif layout == "cta":
        align_css = "align-items: center; justify-content: flex-start; padding-top: 180px;"
        font_weight = "bold"
        emoji = "👉"
    else:  # headline
        align_css = "align-items: center; justify-content: center; padding: 60px;"
        font_weight = "bold"
        emoji = "📰"

    # Wrap content in a bubble for teaser/cta
    if layout == "cta" or layout == "teaser":
        inner_html = f"""
        <div style="background-color: rgba(0, 0, 0, 0.05); padding: 40px 60px; border-radius: 40px;">
            <div class="meme">{emoji} {text}</div>
        </div>
        """
    else:
        inner_html = f'<div class="meme"><span style="font-size: 100px;">{emoji}</span><br><br>{text}</div>'

    html = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
      html,body {{
        margin: 0;
        padding: 0;
        width: 1080px;
        height: 1920px;
        background: {background_color};
        font-family: 'Patrick Hand', cursive;
        display: flex;
        justify-content: center;
        position: relative;
        {align_css}
      }}
      .meme {{
        width: 80%;
        max-width: 900px;
        font-size: {fontsize}px;
        line-height: 1.4;
        text-align: center;
        color: #111;
        white-space: pre-wrap;
        font-weight: {font_weight};
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
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet">
    </head><body>
      {inner_html}
      {f'<div class="slide-number">{slide_number}</div>' if slide_number else ''}
    </body></html>
    """

    (SLIDE_DIR / filename).write_text(html, encoding="utf-8")



# ── HTML→PNG ───────────────────────────────────────────────────────
async def render_html_to_png(html_file: str, png_file: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width":1080,"height":1920})
        await page.goto(f"file:///{(SLIDE_DIR/html_file).resolve()}")
        await page.wait_for_timeout(800)
        await page.screenshot(
            path=SLIDE_DIR / png_file,
            clip={"x":0,"y":0,"width":1080,"height":1920}
        )
        await browser.close()


def stitch_slides(slides: list[str], music: Path, output: str):
    args = []
    filter_parts = []
    input_count = len(slides)

    duration = 4  # seconds each slide is on screen
    transition = 1  # duration of each fade

    for idx, slide in enumerate(slides):
        slide_path = str(SLIDE_DIR / slide)
        args += ["-loop", "1", "-t", str(duration + transition), "-i", slide_path]

    args += ["-i", str(music)]  # Add background music

    # Ensure input images are scaled *before* transitions
    for idx in range(input_count):
        zoom_filter = ""
        if idx == 1:
            # Apply zoom only to slide 2
            zoom_filter = ",zoompan=z='min(zoom+0.0005,1.1)':d=125:s=1080x1920"
        filter_parts.append(
            f"[{idx}:v]scale=1080:1920,format=rgba,setpts=PTS-STARTPTS{zoom_filter}[v{idx}]"
        )

    # Create xfade sequence
    xfade_parts = []
    for i in range(input_count - 1):
        input_a = f"[v{i}]" if i == 0 else f"[xf{i-1}]"
        input_b = f"[v{i+1}]"
        tag = f"[xf{i}]"
        offset = duration * (i + 1)
        xfade_parts.append(
            f"{input_a}{input_b}xfade=transition=fade:duration={transition}:offset={offset}{tag}"
        )

    filter_complex = "; ".join(filter_parts + xfade_parts)
    final_video = f"[xf{input_count - 2}]" if input_count >= 2 else "[v0]"

    cmd = [
        "ffmpeg", "-y", *args,
        "-filter_complex", filter_complex,
        "-map", final_video,
        "-map", f"{input_count}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", output
    ]

    subprocess.run(cmd, check=True)




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
    post = fetch_post()
    try:
        teaser = generate_teaser(post["content"])
        prompt = generate_image_prompt(post["title"], post["content"])

        bg_color = random.choice(REEL_COLORS)

        # 1. Generate reel image straight into slides/
        slide2_path = SLIDE_DIR / "slide2_image.png"
        slide2_path.parent.mkdir(exist_ok=True)
        slide2_path.unlink(missing_ok=True)

        result = generate_image_from_prompt(prompt, str(slide2_path), mode="reel")

        if result is None or not slide2_path.exists():
            print("⚠️ Skipping post due to image generation failure.")
            return  # or continue to next post in loop if part of a batch
            
        time.sleep(1)
        ensure_exact_1080x1920(slide2_path)

        if not slide2_path.exists():
            raise FileNotFoundError("slide2_image.png did not get created")

        with Image.open(slide2_path) as img:
            print(f"📏 Final image size for slide2: {img.size}")

        # 2. Create headline, teaser, CTA slides
        write_slide(post["title"], "slide1_headline.html", fontsize=120, layout="headline", background_color=bg_color)
        write_slide(teaser, "slide3_teaser.html", fontsize=90, layout="teaser", slide_number="3/4", background_color=bg_color)

        counter = get_reel_counter()
        cta_only = generate_cta(teaser, counter)
        write_slide(cta_only, "slide4_cta.html", fontsize=90, layout="cta", slide_number="4/4", background_color=bg_color)

        # 3. Render HTML → PNG
        await render_html_to_png("slide1_headline.html", "slide1_headline.png")
        await render_html_to_png("slide3_teaser.html",   "slide3_teaser.png")
        await render_html_to_png("slide4_cta.html",      "slide4_cta.png")

        # 4. Stitch video
        stitch_slides(
            ["slide1_headline.png", "slide2_image.png",
             "slide3_teaser.png",   "slide4_cta.png"],
            MUSIC_FILE, OUTPUT_VIDEO
        )

        slide2_path.unlink(missing_ok=True)

        # 5. Finalize housekeeping
        print(f"🧾 Attempting to mark post ID {post['id']} as used...")
        mark_post_used(post["id"])
        increment_reel_counter()
        print(f"✅ Reel created: {OUTPUT_VIDEO}")

        # Upload to S3
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        S3_REEL_KEY = f"reels/{date_str}/{int(time.time())}_reel.mp4"
        s3_client.upload_file(
            OUTPUT_VIDEO,
            "liefeed-images",
            S3_REEL_KEY,
            ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
        )

        reel_url = f"https://liefeed-images.s3.us-east-1.amazonaws.com/{S3_REEL_KEY}"
        print(f"📤 Uploaded reel to S3: {reel_url}")

        full_url = f"https://liefeed.com/post/{post['slug']}"
        caption_with_link = f"{cta_only}\n\nRead more 👉 {full_url}"
        save_reel_to_database(caption_with_link, S3_REEL_KEY)
        print(f"✅ Reel created and saved to database.")

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

