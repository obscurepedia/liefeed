def generate_newsletter_html(posts):
    # posts = list of dicts with "title" and "slug"
    html = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>📰 Your LieFeed Digest</h2>
        <p>Here's your latest dose of satire and strange-but-true headlines:</p>
        <ul>
    """
    for post in posts:
        url = f"https://liefeed.com/{post['slug']}"
        html += f'<li><a href="{url}">{post["title"]}</a></li>'

    html += """
        </ul>
        <hr>
        <p style="font-size: 12px; color: #666;">You received this because you subscribed to LieFeed. <a href='https://liefeed.com/unsubscribe'>Unsubscribe</a></p>
    </body>
    </html>
    """
    return html
