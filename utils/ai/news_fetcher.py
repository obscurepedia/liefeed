# utils/news_fetcher.py

import os
import feedparser
from openai import OpenAI

# Load OpenAI API key from environment
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def is_sensitive_topic(title, summary):
    prompt = f"""
    Is the following news story about a sensitive or tragic topic that would be inappropriate for satire? 
    Examples include death, violence, war, disasters, mass shootings, or the recent death of a public figure.

    Title: {title}
    Summary: {summary}

    Respond with only "YES" or "NO".
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3,
            temperature=0
        )
        result = response.choices[0].message.content.strip().lower()
        return "yes" in result
    except Exception as e:
        print(f"OpenAI filter error: {e}")
        return False  # Assume safe if an error occurs

def fetch_google_news(category="politics", max_items=5):
    CATEGORY_SITES = {
        "tech": ["theverge.com", "techcrunch.com", "wired.com"],
        "weird": ["mirror.co.uk", "nypost.com", "odditycentral.com", "ladbible.com", "dailystar.co.uk"],
        "science": ["livescience.com", "newscientist.com", "phys.org"],
        "food": ["eater.com", "delish.com", "foodandwine.com"],
        "travel": ["cntraveler.com", "lonelyplanet.com"],
        "entertainment": ["buzzfeed.com", "vulture.com", "avclub.com"],
        "lifestyle": ["huffpost.com", "mindbodygreen.com", "wellandgood.com"],
        "sports": ["espn.com", "bleacherreport.com"],
        "business": ["marketwatch.com", "forbes.com", "businessinsider.com"],
        # Default fallback if category is unrecognized
        "default": ["bbc.com", "cnn.com", "nytimes.com"]
    }

    # Get list of sites for this category or fallback to default
    sites = CATEGORY_SITES.get(category.lower(), CATEGORY_SITES["default"])
    site_query = " OR ".join(f"site:{site}" for site in sites)
    query = f"{category} {site_query}"
    rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"

    print(f"📰 Fetching Google News RSS: {rss_url}")
    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries:
        article = {
            "title": entry.title,
            "link": entry.link,
            "summary": entry.summary
        }

        if not is_sensitive_topic(article["title"], article["summary"]):
            articles.append(article)
        else:
            print(f"🛑 Excluded sensitive article: {article['title']}")

        if len(articles) >= max_items:
            break

    return articles


