# utils/image_prompt_generator.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_image_prompt(title, content):
    system_msg = (
        "You are a creative assistant that writes short prompts for AI image generation. "
        "The prompts should describe an image based on the article content in a visual, artistic way. "
        "All prompts must be designed for a satirical news site and must follow these rules: "
        "- The image must be a cartoon-style digital illustration "
        "- It must use surreal, absurd, or ironic exaggeration "
        "- There should be absolutely no text in the image "
    )

    user_msg = (
        f"Title: {title}\n"
        f"Content: {content}\n\n"
        f"Write a short, one-sentence prompt that visually represents this article "
        f"following the rules above."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=60
    )

    return response.choices[0].message.content.strip()
