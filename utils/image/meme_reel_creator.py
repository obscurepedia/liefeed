import os, subprocess, uuid, textwrap, tempfile, re, html
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from utils.database.db import get_connection


# ──────────────────────────────  DB helper  ──────────────────────────────
def save_reel_to_database(caption, video_path):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pending_reels (caption, video_path, posted) VALUES (%s,%s,FALSE)",
            (caption, video_path)
        )
        conn.commit()
    conn.close()
    print(f"✅ Reel saved to database: {video_path}")


# ─────────────────────────  1) classic single‑image reel  ─────────────────────────
def create_meme_reel_ffmpeg(image_path, caption, audio_path=None, output_path=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    if audio_path and not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    output_path = output_path or f"meme_reel_{datetime.now():%Y%m%d%H%M%S}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        *(["-i", audio_path] if audio_path else []),
        "-filter_complex", "[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0015,1.1)':d=125,setsar=1[v]",
        "-map", "[v]",
        *(["-map", "1:a"] if audio_path else []),
        "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p", output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Meme reel created → {output_path}")
    save_reel_to_database(caption, output_path)


# ────────────────────────  2) VIDEO SEGMENT HELPERS  ────────────────────────
def create_meme_video_segment(image_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-filter_complex", "[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0015,1.1)':d=125,setsar=1[v]",
        "-map", "[v]", "-t", "3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Meme video segment created → {output_path}")


# ─────────────────────────  2a) Pillow → PNG renderer  ─────────────────────────

def render_summary_to_png(text, png_path, *, W=1080, H=1920):
    """Render wrapped news‑summary text onto a centred, boxed PNG slide."""
    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    font_size, line_spacing = 60, 18
    wrap_chars = 45                                     # ≈6‑7 words/line

    wrapped = textwrap.fill(text, width=wrap_chars)

    img  = Image.new("RGB", (W, H), "black")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    # ── measure text block ──
    try:
        # Pillow ≥ 10
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), wrapped, font=font, spacing=line_spacing
        )
        w, h = right - left, bottom - top
    except AttributeError:
        # Pillow < 10
        w, h = draw.multiline_textsize(wrapped, font=font, spacing=line_spacing)

    # centre position
    x, y = (W - w) // 2, (H - h) // 2
    pad  = 40

    # translucent box
    draw.rectangle((x - pad, y - pad, x + w + pad, y + h + pad),
                   fill=(0, 0, 0, 200))

    # text with thin outline
    draw.multiline_text(
        (x, y), wrapped,
        font=font, fill="white", spacing=line_spacing,
        stroke_width=2, stroke_fill="black"
    )

    img.save(png_path)
    print(f"✅ Summary slide PNG saved → {os.path.abspath(png_path)}")



# ────────────────────────  2b) PNG → 3‑second video  ────────────────────────
def create_news_summary_segment(summary_text, output_path, duration=3):
    tmp_png = f"temp_summary_{uuid.uuid4().hex}.png"
    render_summary_to_png(summary_text, tmp_png)

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", tmp_png,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ News‑summary segment created → {output_path}")
    finally:
        os.remove(tmp_png)


# ─────────────────────────────  3) full combo reel  ─────────────────────────────
def create_combined_reel(image_path, caption, news_summary, audio_path, output_path):
    tmp_id        = uuid.uuid4().hex
    meme_clip     = f"temp_meme_{tmp_id}.mp4"
    summary_clip  = f"temp_summary_{tmp_id}.mp4"
    concat_file   = f"temp_concat_{tmp_id}.txt"

    try:
        # segment 1
        create_meme_video_segment(image_path, meme_clip)

        # clean + segment 2
        clean = html.unescape(re.sub(r"<.*?>", "", news_summary))
        clean = clean.replace(":", " - ").replace("'", "").replace('"', "")
        clean = (clean[:250] + "...") if len(clean) > 250 else clean
        create_news_summary_segment(clean, summary_clip)

        # concat list
        with open(concat_file, "w") as f:
            f.write(f"file '{os.path.abspath(meme_clip)}'\n")
            f.write(f"file '{os.path.abspath(summary_clip)}'\n")

        # final join (+optional audio)
        if audio_path and os.path.exists(audio_path):
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-i", audio_path,
                "-c:v", "libx264", "-c:a", "aac", "-shortest", output_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c", "copy", output_path
            ]
        subprocess.run(cmd, check=True)
        print(f"🎬 Final combined reel created → {output_path}")

        save_reel_to_database(caption, output_path)

    finally:
        for f in (meme_clip, summary_clip, concat_file):
            if os.path.exists(f):
                os.remove(f)
