from pydantic import BaseModel, Field
from typing import Optional, List


class ShippingRequest(BaseModel):
    origin_zip: str = Field(..., example="76201", description="Origin ZIP code")
    destination_zip: str = Field(..., example="45152", description="Destination ZIP code")
    weight_lbs: float = Field(..., gt=0, example=2.0, description="Package weight in lbs")
    length_in: float = Field(..., gt=0, example=12.0, description="Package length in inches")
    width_in: float = Field(..., gt=0, example=8.0, description="Package width in inches")
    height_in: float = Field(..., gt=0, example=6.0, description="Package height in inches")
    delivery_days: int = Field(..., ge=1, le=10, example=3, description="Max days for delivery")


class ShippingQuote(BaseModel):
    carrier: str
    service_name: str
    estimated_cost: float
    estimated_days: int
    billable_weight: float
    dim_weight: float
    guaranteed: bool
    notes: Optional[str] = None


class CarrierWarning(BaseModel):
    carrier: str
    message: str


class ShippingResponse(BaseModel):
    quotes: List[ShippingQuote]
    recommended: Optional[ShippingQuote] = None
    ai_summary: str
    origin_zip: str
    destination_zip: str
    actual_weight: float
    carrier_warnings: List[CarrierWarning] = []
