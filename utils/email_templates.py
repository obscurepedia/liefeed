from utils.token_utils import generate_unsubscribe_token

def generate_newsletter_html(posts, recipient_email, satirical_spin):
    token = generate_unsubscribe_token(recipient_email)
    unsubscribe_url = f"https://liefeed.com/unsubscribe/{token}"

    featured_post = posts[0]
    more_posts = posts[1:5]

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 30px; background-color: #f9f9f9; color: #333;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05);">

            <img src="https://liefeed.com/static/logo.png" alt="LieFeed Logo" style="max-width: 180px; display: block; margin: 0 auto 10px auto;">
            <p style="text-align: center; font-size: 20px; color: #555; margin-bottom: 20px; font-weight: 500;">
                Today’s Made-Up Headlines, Delivered Fresh.
            </p>

            <h2 style="color: #d32f2f; margin-bottom: 10px;">{featured_post['title']}</h2>
    """

    if featured_post.get('image'):
        html += f"""
            <img src="{featured_post['image']}" alt="Featured Image" style="width: 100%; max-height: 300px; object-fit: cover; border-radius: 5px; margin: 15px 0;">
        """

    html += featured_post['content']  # Already paragraph-formatted in the sender script

    html += f"""
            <p style="margin-top: 20px;">
                👉 <a href="https://liefeed.com/{featured_post['slug']}" style="color: #0077cc;">Read it on LieFeed</a>
            </p>

            <hr style="margin: 30px 0;">

            <h3>🗞️ More News You May Have Missed</h3>
            <ul style="list-style-type: none; padding: 0;">
    """

    for post in more_posts:
        html += f"<li style='margin: 15px 0; display: flex; align-items: center;'>"
        if post.get("image"):
            html += f"<img src='{post['image']}' alt='Thumbnail' style='width: 60px; height: 60px; object-fit: cover; margin-right: 10px; border-radius: 4px;'>"
        html += f"<a href='https://liefeed.com/{post['slug']}' style='text-decoration: none; color: #0077cc; font-size: 16px;'>{post['title']}</a></li>"

    html += f"""
            </ul>

            <hr style="margin: 30px 30px;">

            <h3>🤡 This Week’s Satirical Spin</h3>
            <blockquote style="font-style: italic; font-size: 15px; color: #555; border-left: 4px solid #ccc; padding-left: 10px; margin: 10px 0;">
                {satirical_spin}
            </blockquote>

            <div style="text-align: center; margin-top: 30px;">
                <a href="https://facebook.com/liefeed" target="_blank" style="margin: 0 10px;">
                    <img src="https://cdn-icons-png.flaticon.com/512/733/733547.png" alt="Facebook" style="width: 24px; height: 24px;">
                </a>
                <a href="https://x.com/liefeed" target="_blank" style="margin: 0 10px;">
                    <img src="https://cdn-icons-png.flaticon.com/512/5968/5968958.png" alt="Twitter" style="width: 24px; height: 24px;">
                </a>
            </div>

            <p style="font-size: 12px; color: #888; text-align: center; margin-top: 40px;">
                You're receiving this because you subscribed to LieFeed.<br>
                <a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a> if satire makes you uncomfortable.
            </p>

        </div>
    </body>
    </html>
    """
    return html
