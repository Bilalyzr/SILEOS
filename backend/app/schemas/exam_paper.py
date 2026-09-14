from typing import Literal
from pydantic import BaseModel, Field, model_validator


class SlabIn(BaseModel):
    exam: Literal['JEE', 'NEET']
    title: str = Field(min_length=1, max_length=100)
    min_questions: int = Field(ge=5, le=180)
    max_questions: int = Field(ge=5, le=180)
    price_paise: int = Field(ge=100, le=10000000)
    active: bool = True

    @model_validator(mode='after')
    def valid_range(self):
        if self.max_questions < self.min_questions:
            raise ValueError('Maximum question count must not be below minimum.')
        return self


class PaperIn(BaseModel):
    exam: Literal['JEE', 'NEET']
    topic: str = Field(default='', max_length=500)
    count: int = Field(default=10, ge=5, le=180)
    source_text: str = Field(default='', max_length=80000)


class PaperVerification(BaseModel):
    razorpay_order_id: str = Field(min_length=1, max_length=100)
    razorpay_payment_id: str = Field(min_length=1, max_length=100)
    razorpay_signature: str = Field(min_length=1, max_length=200)
