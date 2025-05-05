from utils.token import generate_unsubscribe_token

def generate_newsletter_html(posts, recipient_email):
    token = generate_unsubscribe_token(recipient_email)
    unsubscribe_url = f"https://liefeed.com/unsubscribe/{token}"

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

    html += f"""
        </ul>
        <hr>
        <p style="font-size: 12px; color: #666;">
            You received this because you subscribed to LieFeed.
            <a href="{unsubscribe_url}">Unsubscribe</a>
        </p>
    </body>
    </html>
    """
    return html
