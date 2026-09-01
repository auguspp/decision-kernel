from __future__ import annotations

from datetime import date, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field

from .primitives import AwareDateTime, CurrencyCode, KernelModel


def _validate_money_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("money Decimal must be finite")
    _, digits, exponent = value.as_tuple()
    fractional_digits = max(-exponent, 0)
    integer_digits = 0 if value.is_zero() else max(len(digits) + exponent, 0)
    if fractional_digits > 18:
        raise ValueError("money Decimal scale exceeds 18")
    if integer_digits > 20:
        raise ValueError("money Decimal integer precision exceeds 20")
    return value


MoneyDecimal = Annotated[Decimal, AfterValidator(_validate_money_decimal)]


class ObservedMarket(KernelModel):
    """One frozen market-price observation; transport/provider logic lives elsewhere."""

    market_price: MoneyDecimal = Field(gt=Decimal("0"))
    market_timestamp: AwareDateTime
    market_utc_offset_minutes: int = Field(ge=-840, le=840)
    market_data_source: str = Field(min_length=1, max_length=128)
    price_convention: str = Field(min_length=1, max_length=128)
    currency: CurrencyCode

    @property
    def market_date(self) -> date:
        offset = timezone(timedelta(minutes=self.market_utc_offset_minutes))
        return self.market_timestamp.astimezone(offset).date()
