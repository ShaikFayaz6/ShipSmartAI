import json
import httpx
from datetime import date
from typing import Optional
from config.settings import settings
from models.schemas import ShippingQuote


class FedExTool:
    """
    Real FedEx API integration.
    Uses OAuth2 client credentials flow → then calls Rate API.
    Docs: https://developer.fedex.com/api/en-us/catalog/rate/v1/docs.html
    """

    BASE_URL = settings.FEDEX_BASE_URL
    _token: Optional[str] = None
    MAX_LENGTH_IN = 119.0
    MAX_WIDTH_IN = 80.0
    MAX_HEIGHT_IN = 70.0

    # FedEx service codes → human readable names
    SERVICE_MAP = {
        "FEDEX_GROUND": "FedEx Ground",
        "GROUND_HOME_DELIVERY": "FedEx Home Delivery",
        "FEDEX_EXPRESS_SAVER": "FedEx Express Saver",
        "FEDEX_2_DAY": "FedEx 2Day",
        "FEDEX_2_DAY_AM": "FedEx 2Day AM",
        "STANDARD_OVERNIGHT": "FedEx Standard Overnight",
        "PRIORITY_OVERNIGHT": "FedEx Priority Overnight",
        "FIRST_OVERNIGHT": "FedEx First Overnight",
    }

    # Approximate transit days per service (sandbox may not always return this)
    SERVICE_DAYS = {
        "FEDEX_GROUND": 5,
        "GROUND_HOME_DELIVERY": 5,
        "FEDEX_EXPRESS_SAVER": 3,
        "FEDEX_2_DAY": 2,
        "FEDEX_2_DAY_AM": 2,
        "STANDARD_OVERNIGHT": 1,
        "PRIORITY_OVERNIGHT": 1,
        "FIRST_OVERNIGHT": 1,
    }

    async def _get_token(self) -> str:
        """OAuth2 client credentials token fetch."""
        if self._token:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.FEDEX_CLIENT_ID,
                    "client_secret": settings.FEDEX_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    async def _request_rates(self, token: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/rate/v1/rates/quotes",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-locale": "en_US",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

    def _calc_dim_weight(self, length: float, width: float, height: float) -> float:
        """FedEx DIM weight formula: (L x W x H) / 139"""
        return round((length * width * height) / 139, 2)

    def _billable_weight(self, actual: float, dim: float) -> float:
        """FedEx bills whichever is greater."""
        return max(actual, dim)

    def _validate_package_size(self, length: float, width: float, height: float) -> None:
        longest, middle, shortest = sorted([length, width, height], reverse=True)
        if (
            longest > self.MAX_LENGTH_IN
            or middle > self.MAX_WIDTH_IN
            or shortest > self.MAX_HEIGHT_IN
        ):
            raise ValueError(
                f"FedEx max dimensions are {int(self.MAX_LENGTH_IN)} x {int(self.MAX_WIDTH_IN)} x {int(self.MAX_HEIGHT_IN)} in."
            )

    def _extract_cost(self, rated_details: list) -> Optional[float]:
        """
        FedEx can return net charge in a few nested shapes.
        Return first valid numeric amount found.
        """
        for detail in rated_details:
            if not isinstance(detail, dict):
                continue

            # Common FedEx fields at ratedShipmentDetails item level
            for top_level_key in [
                "totalNetCharge",
                "totalNetFedExCharge",
                "totalNetChargeWithDutiesAndTaxes",
                "totalBaseCharge",
            ]:
                top_val = detail.get(top_level_key)
                if isinstance(top_val, dict) and top_val.get("amount") is not None:
                    return float(top_val["amount"])
                if top_val is not None and not isinstance(top_val, dict):
                    return float(top_val)

            shipment_rate = detail.get("shipmentRateDetail", {})
            total_net_charge = shipment_rate.get("totalNetCharge")

            if isinstance(total_net_charge, dict):
                amount = total_net_charge.get("amount")
                if amount is not None:
                    return float(amount)
            elif total_net_charge is not None:
                return float(total_net_charge)

            # FedEx may return alternate charge fields depending on rate type
            for alt_key in [
                "totalNetFedExCharge",
                "totalNetChargeWithDutiesAndTaxes",
                "totalBaseCharge",
            ]:
                alt_val = shipment_rate.get(alt_key)
                if isinstance(alt_val, dict) and alt_val.get("amount") is not None:
                    return float(alt_val["amount"])
                if alt_val is not None and not isinstance(alt_val, dict):
                    return float(alt_val)

        return None

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
        """
        Calls FedEx Rate API and returns matching quotes.
        Uses live FedEx API only (no mock fallback).
        """
        if not settings.FEDEX_CLIENT_ID or not settings.FEDEX_CLIENT_SECRET or not settings.FEDEX_ACCOUNT_NUMBER:
            raise ValueError(
                "FedEx credentials are missing. Set FEDEX_CLIENT_ID, FEDEX_CLIENT_SECRET, and FEDEX_ACCOUNT_NUMBER."
            )
        if settings.RATE_MODE == "live" and "sandbox" in self.BASE_URL:
            raise ValueError(
                "RATE_MODE is live but FEDEX_BASE_URL points to sandbox. "
                "Set FEDEX_BASE_URL=https://apis.fedex.com or remove override."
            )

        try:
            self._validate_package_size(length_in, width_in, height_in)
            token = await self._get_token()
            dim_weight = self._calc_dim_weight(length_in, width_in, height_in)
            billable = self._billable_weight(weight_lbs, dim_weight)

            payload = {
                "accountNumber": {"value": settings.FEDEX_ACCOUNT_NUMBER},
                "rateRequestControlParameters": {
                    "returnTransitTimes": True,
                    "servicesNeededOnRateFailure": True,
                    "rateSortOrder": "SERVICENAMETRADITIONAL",
                },
                "requestedShipment": {
                    "shipper": {"address": {"postalCode": origin_zip, "countryCode": "US"}},
                    "recipient": {"address": {"postalCode": destination_zip, "countryCode": "US", "residential": True}},
                    "preferredCurrency": "USD",
                    "shipDateStamp": date.today().isoformat(),
                    "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                    "rateRequestType": ["LIST"],
                    "packagingType": "YOUR_PACKAGING",
                    "totalPackageCount": 1,
                    "requestedPackageLineItems": [
                        {
                            "groupPackageCount": 1,
                            "weight": {"units": "LB", "value": weight_lbs},
                            "dimensions": {
                                "length": int(length_in),
                                "width": int(width_in),
                                "height": int(height_in),
                                "units": "IN",
                            },
                        }
                    ],
                },
                "processingOptions": ["INCLUDE_PICKUPRATES"],
                "carrierCodes": ["FDXE", "FDXG"],
                "version": {"major": 1, "minor": 1, "patch": 1},
            }

            try:
                data = await self._request_rates(token, payload)
            except httpx.HTTPStatusError as exc:
                # Retry once with a fresh token if prior token became invalid/expired.
                if exc.response.status_code == 401:
                    self._token = None
                    fresh_token = await self._get_token()
                    data = await self._request_rates(fresh_token, payload)
                else:
                    fedex_error = exc.response.text
                    try:
                        fedex_error = json.dumps(exc.response.json())
                    except Exception:
                        pass
                    raise RuntimeError(
                        f"FedEx API returned {exc.response.status_code}: {fedex_error}"
                    ) from exc

            quotes = []
            rate_replies = data.get("output", {}).get("rateReplyDetails", [])

            for rate in rate_replies:
                service_code = rate.get("serviceType", "")
                service_name = self.SERVICE_MAP.get(service_code, service_code)
                est_days = self.SERVICE_DAYS.get(service_code, delivery_days)

                if est_days > delivery_days:
                    continue  # Filter out services that don't meet deadline

                rated = rate.get("ratedShipmentDetails", [])
                if not rated:
                    continue

                cost = self._extract_cost(rated)
                if cost is None:
                    continue

                quotes.append(
                    ShippingQuote(
                        carrier="FedEx",
                        service_name=service_name,
                        estimated_cost=float(cost),
                        estimated_days=est_days,
                        billable_weight=billable,
                        dim_weight=dim_weight,
                        guaranteed=est_days <= 2,
                        notes=f"Real FedEx {settings.RATE_MODE} rate",
                    )
                )

            if not quotes:
                raise RuntimeError("FedEx API returned no valid quotes for this shipment.")

            return sorted(quotes, key=lambda q: q.estimated_cost)

        except Exception as e:
            raise RuntimeError(f"FedEx live pricing failed: {e}") from e

