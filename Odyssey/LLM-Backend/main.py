from api.api import create_app
from model.api_model import GeminiModel
import uvicorn
from conf import config_manager

gemini = GeminiModel("gemini-2.5-flash")

# Register Gemini under every model name Odyssey may request
MODEL_NAMES = [
    'llama3_8b_v3',
    'llama3_8b',
    'llama3_70b_v1',
    'llama2_70b',
    'qwen2-7b',
    'qwen2-72b',
    'baichuan2-7b',
]

if __name__ == "__main__":
    models = {name: gemini for name in MODEL_NAMES}
    app = create_app(models)
    uvicorn.run(app, host="0.0.0.0", port=config_manager.get('port'))
