from pydantic import BaseModel

class EvalInput(BaseModel):
    model_name: str
    dataset_name: str
    num_samples: int

class EvalOutput(BaseModel):
    score: float
    feedback: list[str]