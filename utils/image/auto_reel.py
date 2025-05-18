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



# ── CONFIG ─────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client  = OpenAI(api_key=OPENAI_API_KEY)

SLIDE_DIR     = Path("slides")
OUTPUT_VIDEO  = "reel.mp4"
SLIDE_DIR.mkdir(exist_ok=True)

track_list = os.getenv("MUSIC_TRACKS", "").split(",")
selected_track = random.choice(track_list).strip()
MUSIC_FILE = Path(__file__).resolve().parent.parent / "static" / selected_track

# --- SETTINGS ---
REEL_ROTATION_KEY = "reel_cta_counter"
FOLLOW_REEL_INTERVAL = 5

# ── DB HELPERS ─────────────────────────────────────────────────────
def fetch_post():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, content
            FROM posts
            WHERE used_in_reel IS NOT TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
    conn.close()
    if not row:
        raise Exception("No unused posts found.")
    return {"id": row[0], "title": row[1], "content": row[2]}

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
            WHERE s.setting_key = 'reel_cta_counter'
        """)
        conn.commit()
    conn.close()


def mark_post_used(post_id: int):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE posts SET used_in_reel = TRUE WHERE id = %s", (post_id,))
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


# ── HTML SLIDE WRITER ──────────────────────────────────────────────
def write_slide(text: str, filename: str, *, fontsize: int = 80, layout: str = "headline", slide_number: str = ""):
    if layout == "teaser":
        align_css = "align-items: center; justify-content: center; padding: 60px;"
    elif layout == "cta":
        align_css = "align-items: center; justify-content: center; padding: 60px;"
    else:
        align_css = "align-items: flex-start; justify-content: center; padding-top: 100px;"
        
    font_weight = "bold" if layout == "cta" else "normal"

    # Add emoji based on layout type
    if layout == "headline":
        emoji = "📰"
    elif layout == "teaser":
        emoji = "👀"
    elif layout == "cta":
        emoji = "👉"
    else:
        emoji = ""


    # Wrap CTA text with a subtle background bubble
    if layout == "headline":
        inner_html = f'<div class="meme"><span style="font-size: 100px;">{emoji}</span><br><br>{text}</div>'
    elif layout == "cta":
        inner_html = f"""
        <div style="background-color: rgba(0, 0, 0, 0.05); padding: 40px 60px; border-radius: 40px;">
            <div class="meme">{emoji} {text}</div>
        </div>
        """
    else:
        inner_html = f'<div class="meme">{emoji} {text}</div>'


    html = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
      html,body {{
        margin: 0;
        padding: 0;
        width: 1080px;
        height: 1920px;
        background: #f7f4b2;
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

def pad_to_1080x1920(src: Path, dst: Path):
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-filter_complex",
        (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,boxblur=10:1[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto"
        ),
        "-frames:v", "1",          # single-frame PNG output
        "-q:v", "3",
        str(dst)
    ]
    subprocess.run(cmd, check=True)



def stitch_slides(slides: list[str], music: Path, output: str):
    args = []
    filters = []

    for idx, slide in enumerate(slides):
        slide_path = str(SLIDE_DIR / slide)
        args += ["-loop", "1", "-t", "4", "-i", slide_path]
        filters.append(f"[{idx}:v]scale=1080:1920,setsar=1[v{idx}]")

    # Combine all video inputs
    filter_complex = "; ".join(filters) + f"; {' '.join([f'[v{i}]' for i in range(len(slides))])}concat=n={len(slides)}:v=1:a=0[outv]"

    cmd = [
        "ffmpeg", "-y", *args, "-i", str(music),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", f"{len(slides)}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", output
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
    post   = fetch_post()
    teaser = generate_teaser(post["content"])
    prompt = generate_image_prompt(post["title"], post["content"])

    # 1. Generate reel image straight into slides/
    slide2_path = SLIDE_DIR / "slide2_image.png"
    slide2_path.parent.mkdir(exist_ok=True)

    # if an old slide exists, delete it so we don't hit "file exists"
    slide2_path.unlink(missing_ok=True)

    generate_image_from_prompt(
        prompt,
        str(slide2_path),      # write directly here
        mode="reel"
    )

    # ✅ Check if slide was actually created
    if not slide2_path.exists():
        raise FileNotFoundError("slide2_image.png did not get created")

    

    # 2. Create headline, teaser, CTA slides
    write_slide(post["title"], "slide1_headline.html", fontsize=120, layout="headline")
    write_slide(teaser, "slide3_teaser.html", fontsize=72, layout="teaser", slide_number="3/4")

    counter   = get_reel_counter()
    cta_only  = generate_cta(teaser, counter)
    write_slide(cta_only,      "slide4_cta.html",    fontsize=72,  layout="cta")

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

    # ✅ Use it for stitching/uploading reel, then clean up at the END of main()
    slide2_path.unlink(missing_ok=True)

    # 5. Finalize housekeeping
    print(f"🧾 Attempting to mark post ID {post['id']} as used...")
    mark_post_used(post["id"])
    increment_reel_counter()
    print(f"✅ Reel created: {OUTPUT_VIDEO}")

    
    # Generate the S3 key with a date-based subfolder
    date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    S3_REEL_KEY = f"reels/{date_str}/{int(time.time())}_reel.mp4"

    # Upload the reel to S3
    s3_client.upload_file(
        OUTPUT_VIDEO,
        "liefeed-images",  # Replace with your actual bucket if different
        S3_REEL_KEY,
        ExtraArgs={'ContentType': mimetypes.guess_type(OUTPUT_VIDEO)[0] or 'video/mp4'}
    )

    # Generate and print the public S3 URL
    reel_url = f"https://liefeed-images.s3.us-east-1.amazonaws.com/{S3_REEL_KEY}"
    print(f"📤 Uploaded reel to S3: {reel_url}")
    
    # Save to DB
    save_reel_to_database(cta_only, S3_REEL_KEY)
    print(f"✅ Reel created and saved to database.")



if __name__ == "__main__":
    asyncio.run(main())


