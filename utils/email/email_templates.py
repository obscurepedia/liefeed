from utils.database.token_utils import generate_unsubscribe_token

def generate_newsletter_html(posts, subscriber_id, recipient_email, satirical_spin, email_id, current_freq=None):
    token = generate_unsubscribe_token(recipient_email)
    unsubscribe_url = f"https://liefeed.com/unsubscribe/{token}"

    featured_post = posts[0]
    more_posts = posts[1:5]

    # Create the table-based rows for the additional posts
    more_posts_rows = ""
    for post in more_posts:
        if post.get("image"):
            image_html = f"<td width='60' valign='top'><img src='{post['image']}' alt='Thumbnail' width='60' height='60' style='display:block; border-radius:4px;'></td>"
        else:
            image_html = ""

        more_posts_rows += f"""
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 15px;">
          <tr>
            {image_html}
            <td valign="middle" style="padding-left: 10px;">
              <a href="https://liefeed.com/post/{post['slug']}" style="font-size: 16px; color: #0077cc; text-decoration: none;">{post['title']}</a>
            </td>
          </tr>
        </table>
        """

    html = f"""\
<html>
  <body style="margin: 0; padding: 0; background-color: #f9f9f9;">
    <center>

      <!-- Preheader -->
      <span style="display: none; font-size: 1px; color: #fff;">
        Here’s your next dose of truth-adjacent absurdity.
      </span>

      <table width="600" border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background: #ffffff; margin: 30px auto; font-family: Arial, sans-serif; color: #333;">
        <tr>
          <td align="center" style="padding: 30px;">
            <img src="https://liefeed.com/static/logo.png" alt="LieFeed Logo" width="180" style="display: block; border: 0; margin-bottom: 20px;">
            <p style="font-size: 20px; color: #555; font-weight: 500; margin: 0 0 20px 0;">Today’s Made-Up Headlines, Delivered Fresh.</p>

            <h2 style="color: #d32f2f; font-size: 22px; margin: 0 0 10px 0;">{featured_post['title']}</h2>
    """

    if featured_post.get('image'):
        html += f"""
            <img src="{featured_post['image']}" alt="{featured_post['title']}" width="540" height="300" style="display: block; border-radius: 5px; margin: 15px 0;">
        """

    html += f"""
            <div style="font-size: 15px; line-height: 1.6;">
              {featured_post['content']}
            </div>

            <p style="margin-top: 20px;">
              👉 <a href="https://liefeed.com/post/{featured_post['slug']}" style="color: #0077cc;">Read it on LieFeed</a>
            </p>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

            <h3 style="margin-bottom: 10px;">🗞️ More News You May Have Missed</h3>

            {more_posts_rows}

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

            <h3 style="margin-bottom: 10px;">🤡 This Week’s Satirical Spin</h3>
            <blockquote style="font-style: italic; font-size: 15px; color: #555; border-left: 4px solid #ccc; padding-left: 10px; margin: 10px 0;">
              {satirical_spin}
            </blockquote>
    """

    # 🆙 Add upgrade prompt for weekly users
    if current_freq == "weekly":
        html += f"""
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

            <div style="background: #f0f8ff; padding: 20px; border-radius: 8px; text-align: center;">
              <h3 style="margin-bottom: 10px;">💥 Upgrade Your Dose of Nonsense</h3>
              <p style="font-size: 15px; color: #444;">
                You're on the <strong>Weekly Plan</strong> — but you could be getting 3x the satire, scandal, and surrealism.
              </p>
              <a href="https://liefeed.com/newsletter/upgrade-to-3x?email={recipient_email}"
                 style="display: inline-block; background: #0077cc; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; margin-top: 10px;">
                🔁 Switch to 3x/week Lies
              </a>
            </div>
        """

    html += f"""
            <div style="text-align: center; margin-top: 30px;">
              <a href="https://facebook.com/liefeed" target="_blank" style="margin: 0 10px;">
                <img src="https://cdn-icons-png.flaticon.com/512/733/733547.png" alt="Facebook" width="24" height="24" style="display: inline-block;">
              </a>
              <a href="https://x.com/liefeed" target="_blank" style="margin: 0 10px;">
                <img src="https://cdn-icons-png.flaticon.com/512/5968/5968958.png" alt="Twitter" width="24" height="24" style="display: inline-block;">
              </a>
            </div>

            <p style="font-size: 12px; color: #888; text-align: center; margin-top: 40px;">
              You're receiving this because you subscribed to LieFeed.<br>
              <a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a> if satire makes you uncomfortable.
            </p>
          </td>
        </tr>
      </table>
    </center>
  </body>
</html>
"""
    return html
