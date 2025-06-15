import os
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def generate_voiceover(text: str, output_path: str, voice_id="TX3LPaxmHKxFdv7VOQHJ"):
    try:
        stream = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_monolingual_v1",
            text=text,
            output_format="mp3_44100_128"
        )

        with open(output_path, "wb") as f:
            for chunk in stream:
                f.write(chunk)

        print(f"🎤 Voiceover saved: {output_path}")
    except Exception as e:
        print(f"❌ Voiceover generation failed: {e}")
