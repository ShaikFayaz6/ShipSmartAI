import math
import httpx
from models.schemas import ShippingQuote
from config.settings import settings


class USPSTool:
    """USPS rates via Shippo API."""

    SHIPPO_BASE_URL = "https://api.goshippo.com"
    MAX_LENGTH_PLUS_GIRTH_IN = 130.0
    PRIORITY_MAX_LENGTH_PLUS_GIRTH_IN = 108.0
    MAX_WEIGHT_LBS = 70.0

    def _calc_dim_weight(self, length: float, width: float, height: float) -> float:
        """USPS uses 166 as DIM divisor for Priority, no DIM for Ground Advantage."""
        return round((length * width * height) / 166, 2)

    def _billable_weight(self, actual: float, dim: float, service_name: str) -> float:
        if "Ground Advantage" in service_name:
            return math.ceil(actual)  # No DIM weight for Ground Advantage
        return math.ceil(max(actual, dim))

    def _length_plus_girth(self, length: float, width: float, height: float) -> float:
        girth = 2 * width + 2 * height
        return length + girth

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
            raise RuntimeError("SHIPPO_API_KEY is missing for USPS live rates.")
        if settings.RATE_MODE == "live" and settings.SHIPPO_API_KEY.startswith("shippo_test_"):
            raise RuntimeError("RATE_MODE is live but SHIPPO_API_KEY is a test key.")
        if weight_lbs > self.MAX_WEIGHT_LBS:
            raise RuntimeError("USPS max weight is 70 lbs.")

        length_plus_girth = self._length_plus_girth(length_in, width_in, height_in)
        if length_plus_girth > self.MAX_LENGTH_PLUS_GIRTH_IN:
            raise RuntimeError("USPS max size is 130 in (length + girth).")

        dim_weight = self._calc_dim_weight(length_in, width_in, height_in)

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
            if provider != "USPS":
                continue

            service_name = rate.get("servicelevel", {}).get("name", "USPS")
            if (
                length_plus_girth > self.PRIORITY_MAX_LENGTH_PLUS_GIRTH_IN
                and "Ground Advantage" not in service_name
            ):
                # USPS priority products are generally limited to 108 inches
                continue
            billable = float(self._billable_weight(weight_lbs, dim_weight, service_name))
            estimated_days = rate.get("estimated_days")
            if isinstance(estimated_days, int) and estimated_days > delivery_days:
                continue

            cost = rate.get("amount")
            if cost is None:
                continue

            days = int(estimated_days) if isinstance(estimated_days, int) else delivery_days
            quotes.append(
                ShippingQuote(
                    carrier="USPS",
                    service_name=service_name,
                    estimated_cost=float(cost),
                    estimated_days=days,
                    billable_weight=billable,
                    dim_weight=dim_weight,
                    guaranteed=days <= 2 or "Express" in service_name,
                    notes=f"Real USPS {settings.RATE_MODE} rate via Shippo API",
                )
            )

        return sorted(quotes, key=lambda q: q.estimated_cost)
