# Add `core.llm` to `projects/dyxn`

## 1. Create `core/llm.py`

```python
from langchain.chat_models import init_chat_model

from core.config import config


def get_llm():
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required to initialize the OpenAI chat model.")

    return init_chat_model(
        model="gpt-4.1-mini",
        model_provider="openai"
    )
```

## 2. In every file that uses the LLM

Replace this:
```python
from langchain.chat_models import init_chat_model

llm = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai"
)
```

With this:
```python
from core.llm import get_llm

llm = get_llm()
```

### Files to update
- `agents/planner.py`
- `agents/synthesizer.py`
- `agents/evaluator.py`
- `agents/latex_agent.py`
- `api/memory.py`

That's it. Everything else stays the same.
