import os
from huggingface_hub import InferenceClient
import dotenv
dotenv.load_dotenv()

import os
from huggingface_hub import InferenceClient

from prompts.system_prompt import SYSTEM_PROMPT
from tools.my_tools import get_weather

## You need a token from https://hf.co/settings/tokens, ensure that you select 'read' as the token type.
## If you run this on Google Colab, add it in the "Secrets" tab (key icon on the left sidebar) and call it "HF_TOKEN".
try:
    from google.colab import userdata
    HF_TOKEN = userdata.get("HF_TOKEN")
except ImportError:
    HF_TOKEN = os.environ.get("HF_TOKEN")

client = InferenceClient(model="moonshotai/Kimi-K2.5", token=HF_TOKEN)

output = client.chat.completions.create(
    messages=[
        {"role": "user", "content": "The capital of France is"},
    ],
    stream=False,
    max_tokens=1024,
    extra_body={'thinking': {'type': 'disabled'}},
)
print(output.choices[0].message.content)
messages=[
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "What's the weather in London ?"},
    {"role": "assistant", "content": output.choices[0].message.content + "Observation:\n" + get_weather('London')},
]

output = client.chat.completions.create(
    messages=messages,
    stream=False,
    max_tokens=200,
    extra_body={'thinking': {'type': 'disabled'}},
)

print(output.choices[0].message.content)

print("*************************************************")
print("*************************************************")

