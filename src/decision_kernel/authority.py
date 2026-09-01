from __future__ import annotations

from typing import Literal, TypeAlias

from .primitives import KernelModel


InvestmentAuthority: TypeAlias = Literal["NONE"]
NO_INVESTMENT_AUTHORITY: InvestmentAuthority = "NONE"


class SystemAuthorityBoundary(KernelModel):
    """Constitutional boundary: the kernel creates research, never capital authority."""

    recommendation: Literal["NONE"] = "NONE"
    position_size: Literal["NONE"] = "NONE"
    portfolio: Literal["NONE"] = "NONE"
    human_decision: Literal["NONE"] = "NONE"
    execution: Literal["NONE"] = "NONE"
    capital_deployment: Literal["NONE"] = "NONE"


NO_SYSTEM_AUTHORITY = SystemAuthorityBoundary()
