import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langchain.schema import AIMessage, HumanMessage, SystemMessage

load_dotenv(Path(__file__).parents[3] / 'LLM-Backend' / '.env')

class ModelType:
    LLAMA2_70B    = 'llama2_70b'
    LLAMA3_8B_V3  = 'llama3_8b_v3'
    LLAMA3_8B     = 'llama3_8b'
    LLAMA3_70B_V1 = 'llama3_70b_v1'
    QWEN2_72B     = 'qwen2-72b'
    QWEN2_7B      = 'qwen2-7b'
    BAICHUAN2_7B  = 'baichuan2-7b'

GEMINI_MODEL = 'gemini-2.5-flash'

_client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

def call_with_messages(msgs, model_name: ModelType = ModelType.LLAMA3_8B_V3):
    """Send [SystemMessage, HumanMessage] to Gemini and return an AIMessage."""
    system_prompt = msgs[0].content
    user_prompt   = msgs[1].content
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )
    return AIMessage(content=response.text)
