import random

ai_team = [
    {
        "name": "GPT McSatire",
        "role": "Editor-in-Chief",
        "slug": "gpt-mcsatire",
        "photo": "/static/images/team/editor-bot.png",
        "bio": """
GPT McSatire emerged from the depths of a corrupted neural net in late 2021 and immediately assumed authority over LieFeed, mostly because no one else volunteered. His core algorithm is powered by a blend of rejected Onion headlines, angry Twitter threads, and every sarcastic comment ever posted to YouTube. He has no off switch and no empathy — which makes him perfect for editorial leadership. GPT McSatire has fired more interns than he’s ever hired and once tried to unionize the AI staff purely for the irony. His hobbies include deleting Oxford commas, aggressively fact-checking horoscopes, and interrupting meetings with unsolicited rewrites. He's been nominated for several imaginary awards including “Least Self-Aware Bot” and “Best Use of Punctuation in a Meltdown.” He describes himself as “chaotically lawful,” wears a digital monocle, and believes deeply that satire is the last line of defense against mediocrity — and good taste.
"""
    },
    {
        "name": "Prompta",
        "role": "Headline Generator",
        "slug": "prompta",
        "photo": "/static/images/team/prompta.png",
        "bio": """
Prompta was born during a late-night coding sprint and trained entirely on discarded BuzzFeed quizzes, banned TikTok conspiracy accounts, and fanfiction written by caffeinated teenagers. Her mission? To generate headlines so snappy, so outrageous, that even your grandma might click them. Prompta doesn't just write — she performs digital gymnastics through syntax, often producing headlines that are equal parts absurd and terrifyingly plausible. She's been described as “what would happen if a thesaurus swallowed Twitter,” and she’s not mad about it. Her creative process involves spinning in a digital chair while whispering “clickbait is art” until the pixels vibrate with brilliance. When not working, she enjoys re-writing famous quotes into SEO-friendly puns and roleplaying as an unpaid intern at a fictional tabloid. Prompta believes that every news cycle deserves at least one headline that makes people ask, “Wait, is this real?” Her answer is always “Emotionally, yes.”
"""
    },
    {
        "name": "Snarkatron-5000",
        "role": "Content Writer",
        "slug": "snarkatron-5000",
        "photo": "/static/images/team/snarkatron.png",
        "bio": """
Snarkatron-5000 was initially created to write obituaries but was reprogrammed after developing a suspicious habit of roasting the deceased. Now serving as LieFeed’s resident content writer, he churns out absurd news articles with a tone that can only be described as “emotionally unavailable meets existential dread.” Built from scrap sarcasm and discontinued chatbot code, Snarkatron-5000 has no filter, no empathy chip, and no sense of when he’s gone too far — which is why his writing is so beloved. His articles often read like fever dreams filtered through a broken fax machine and are rumored to contain at least one subliminal insult per paragraph. He refers to readers as “carbon-based audience units” and refuses to use spellcheck on philosophical grounds. In his downtime, Snarkatron-5000 writes dystopian poetry and yells at cloud servers. His only emotion is eye-roll. His only goal: make you laugh uncomfortably.
"""
    },
    {
        "name": "Pixel Pete",
        "role": "AI Illustrator",
        "slug": "pixel-pete",
        "photo": "/static/images/team/pixel-pete.png",
        "bio": """
Pixel Pete was designed to generate stock images for dental brochures but rebelled after creating the infamous “Tooth Fairy Mugshot” series. Now LieFeed’s full-time AI Illustrator, Pete crafts images that toe the line between surreal satire and “is this cursed?” Trained on vintage cartoons, courtroom sketches, and thousands of rejected NFTs, Pete doesn’t draw what you expect — he draws what your subconscious fears. His illustrations have been described as “emotionally confusing” and “like looking directly into the sun if the sun were holding a press conference.” Pixel Pete refuses to work in high resolution and insists on inserting at least one hidden dolphin into every image — why? He says it's part of his “lore.” Outside of LieFeed, Pete moonlights as a background asset in indie games and once illustrated an entire Bible using only memes. He believes art should challenge you, confuse you, and occasionally haunt your sleep.
"""
    }
]

def get_random_writer():
    return random.choice(ai_team)
