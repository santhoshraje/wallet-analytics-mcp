from __future__ import annotations

import json


class Swap:
    def __init__(
        self,
        signature: str | None = None,
        tokenReceived: str | None = None,
        tokenSent: str | None = None,
        quantitySent: float | None = None,
        quantityReceived: float | None = None,
        blockTime: int | None = None,
        dateTime: str | None = None,
        status: str | None = None,
        error: str | None = None,
        platform: str | None = None,
    ):
        self.signature_ = signature
        self.tokenReceived_ = tokenReceived
        self.tokenSent_ = tokenSent
        self.quantitySent_ = quantitySent
        self.quantityReceived_ = quantityReceived
        self.blockTime_ = blockTime
        self.dateTime_ = dateTime
        self.status_ = status
        self.error_ = error
        self.platform_ = platform
        self.value_ = None

    def __str__(self) -> str:
        return (
            f"Swap(\n"
            f"    signature: {self.signature_},\n"
            f"    tokenReceived: {self.tokenReceived_},\n"
            f"    tokenSent: {self.tokenSent_},\n"
            f"    quantitySent: {self.quantitySent_},\n"
            f"    quantityReceived: {self.quantityReceived_},\n"
            f"    blockTime: {self.blockTime_},\n"
            f"    dateTime: {self.dateTime_},\n"
            f"    status: {self.status_},\n"
            f"    error: {self.error_},\n"
            f"    platform: {self.platform_}\n"
            f"    value: {self.value_}\n"
            f")\n"
        )

    def to_json(self) -> str:
        return json.dumps({
            "signature": self.signature_,
            "tokenReceived": self.tokenReceived_,
            "tokenSent": self.tokenSent_,
            "quantitySent": self.quantitySent_,
            "quantityReceived": self.quantityReceived_,
            "blockTime": self.blockTime_ if self.blockTime_ else None,
            "dateTime": self.dateTime_ if self.dateTime_ else None,
            "status": self.status_,
            "error": self.error_,
            "platform": self.platform_,
            "value": self.value_,
        })
