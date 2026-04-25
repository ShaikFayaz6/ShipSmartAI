import math
import httpx
from models.schemas import ShippingQuote
from config.settings import settings


class UPSTool:
    """UPS rates via Shippo API."""

    SHIPPO_BASE_URL = "https://api.goshippo.com"
    MAX_LENGTH_PLUS_GIRTH_IN = 165.0

    def _calc_dim_weight(self, length: float, width: float, height: float) -> float:
        """UPS DIM divisor is 139 for domestic."""
        return round((length * width * height) / 139, 2)

    def _length_plus_girth(self, length: float, width: float, height: float) -> float:
        girth = 2 * width + 2 * height
        return length + girth

    def _billable_weight(self, actual: float, dim: float) -> float:
        return math.ceil(max(actual, dim))

    async def get_rates(
        self,
        origin_zip: str,
        destination_zip: str,
        weight_lbs: float,
        length_in: float,
        width_in: float,
        height_in: float,
        delivery_days: int,
    ) -> list[ShippingQuote]:
        if not settings.SHIPPO_API_KEY:
            raise RuntimeError("SHIPPO_API_KEY is missing for UPS live rates.")
        if settings.RATE_MODE == "live" and settings.SHIPPO_API_KEY.startswith("shippo_test_"):
            raise RuntimeError("RATE_MODE is live but SHIPPO_API_KEY is a test key.")
        if self._length_plus_girth(length_in, width_in, height_in) > self.MAX_LENGTH_PLUS_GIRTH_IN:
            raise RuntimeError(
                "Package exceeds UPS max size: length + girth must be <= 165 in."
            )

        dim_weight = self._calc_dim_weight(length_in, width_in, height_in)
        billable = float(self._billable_weight(weight_lbs, dim_weight))

        payload = {
            "address_from": {"zip": origin_zip, "country": "US"},
            "address_to": {"zip": destination_zip, "country": "US"},
            "parcels": [
                {
                    "length": str(length_in),
                    "width": str(width_in),
                    "height": str(height_in),
                    "distance_unit": "in",
                    "weight": str(weight_lbs),
                    "mass_unit": "lb",
                }
            ],
            "async": False,
        }

        headers = {
            "Authorization": f"ShippoToken {settings.SHIPPO_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.SHIPPO_BASE_URL}/shipments/",
                json=payload,
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            shipment = resp.json()

        quotes: list[ShippingQuote] = []
        for rate in shipment.get("rates", []):
            provider = (rate.get("provider") or "").upper()
            if provider != "UPS":
                continue

            service_name = rate.get("servicelevel", {}).get("name", "UPS")
            estimated_days = rate.get("estimated_days")
            if isinstance(estimated_days, int) and estimated_days > delivery_days:
                continue

            cost = rate.get("amount")
            if cost is None:
                continue

            days = int(estimated_days) if isinstance(estimated_days, int) else delivery_days
            quotes.append(
                ShippingQuote(
                    carrier="UPS",
                    service_name=service_name,
                    estimated_cost=float(cost),
                    estimated_days=days,
                    billable_weight=billable,
                    dim_weight=dim_weight,
                    guaranteed=days <= 2,
                    notes=f"Real UPS {settings.RATE_MODE} rate via Shippo API",
                )
            )

        return sorted(quotes, key=lambda q: q.estimated_cost)
