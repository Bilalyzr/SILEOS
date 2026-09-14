"""Strict schemas for the manual instructor payout ledger."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class BankMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bank"]
    account_holder: str = Field(min_length=1, max_length=120)
    account_number: str = Field(pattern=r"^[0-9]{6,20}$")
    ifsc: str = Field(pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    bank_name: str = Field(default="", max_length=120)


class UpiMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["upi"]
    upi_id: str = Field(pattern=r"^[A-Za-z0-9._\-]{2,256}@[A-Za-z]{2,64}$")


MethodData = Annotated[Union[BankMethod, UpiMethod], Field(discriminator="type")]


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(max_digits=16, decimal_places=2)
    method_data: MethodData


class BalanceOut(BaseModel):
    earned: float
    withdrawn_or_pending: float
    available: float


class WithdrawalOut(BaseModel):
    id: int
    amount: float
    method_data: dict
    status: str
    reject_detail: str = ""
    paid_reference: str = ""
    created_at: datetime | None = None
    processed_at: datetime | None = None


class InstructorWithdrawalsOut(BaseModel):
    balance: BalanceOut
    min_withdrawal_inr: int
    items: list[WithdrawalOut]


class AdminWithdrawalOut(WithdrawalOut):
    user_id: int
    user_email: str
    display_name: str
    processed_by: int | None = None


class RejectRequest(BaseModel):
    reject_detail: str = Field(min_length=3, max_length=1000)


class MarkPaidRequest(BaseModel):
    paid_reference: str = Field(min_length=3, max_length=255)
