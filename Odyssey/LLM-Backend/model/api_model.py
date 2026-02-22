import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set — add it to Odyssey/LLM-Backend/.env")
client = genai.Client(api_key=GEMINI_API_KEY)

class GeminiModel:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def __call__(self, user_prompt, system_prompt):
        response = client.models.generate_content(
            model=self.model_name,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                temperature=0.6,
                top_p=0.9,
                max_output_tokens=1024,
            )
        )
        return response.text

class ModelFactory:
    _gemini = None

    @classmethod
    def get_gemini(cls):
        if cls._gemini is None:
            cls._gemini = GeminiModel()
        return cls._gemini

    @classmethod
    def call(cls, model_name, messages):
        system_prompt = next((m['content'] for m in messages if m['role'] == 'system'), '')
        user_prompt = next((m['content'] for m in messages if m['role'] == 'user'), '')
        return cls.get_gemini()(user_prompt=user_prompt, system_prompt=system_prompt)
