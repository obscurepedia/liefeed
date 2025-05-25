import os
from openai import OpenAI
from utils.database.db import get_connection

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_question():
    prompt = """
Create a satirical headline, and 4 multiple choice options answering the question:
"What makes this fake?"

Use this format:
Question: <headline>
Options:
A. <option>
B. <option>
C. <option>
D. <option>
Correct Answer: <letter>
Explanation: <short explanation why it's fake>
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None

def parse_and_insert(content):
    try:
        lines = content.strip().splitlines()

        if len(lines) < 8:
            print("❌ Incomplete response, skipping.")
            return

        question = lines[0].replace("Question: ", "").strip()
        options = {line[0]: line[3:].strip() for line in lines[2:6]}
        correct = lines[6].split(":")[1].strip()[0]  # Ensure only 'A', 'B', etc.
        explanation = lines[7].split(":", 1)[1].strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO article_quiz_questions (
                level, format_type, question,
                option_a, option_b, option_c, option_d,
                correct_option, explanation, reward_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (
            1, "F2", question,
            options["A"], options["B"], options["C"], options["D"],
            correct, explanation
        ))
        conn.commit()
        conn.close()

        print(f"✅ Inserted question: {question[:60]}...")
    except Exception as e:
        print("❌ Failed to parse/insert:", e)


if __name__ == "__main__":
    # Generate and insert N questions
    for _ in range(15):
        output = generate_question()
        if output:
            parse_and_insert(output)
