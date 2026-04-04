# -*- coding: utf-8 -*-
from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    service: str
    generated_at: str
