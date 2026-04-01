import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../backend/.env"))

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GROQ_MODEL        = "llama-3.3-70b-versatile"
# FIX: was used in call_llm_vision but never defined — caused NameError at runtime
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def call_llm(prompt: str, system: str | None = None) -> str:
    """
    Call the Groq chat model.

    Args:
        prompt: User message.
        system: Optional system prompt sent as the "system" role — gives the
                model clearer context than embedding instructions in the user
                message.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        messages=messages,
        model=GROQ_MODEL,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def call_llm_vision(prompt: str, image_path: str) -> str:
    """
    Send a text prompt + local image to the Groq vision model.
    The image is base64-encoded and sent inline.
    """
    ext_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    ext  = os.path.splitext(image_path)[1].lower()
    mime = ext_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        temperature=0.1,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content.strip()