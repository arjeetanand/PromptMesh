from pydantic import BaseModel

class SummaryOutput(BaseModel):
    text: str
