import asyncio
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.fedex_tool import FedExTool
from agents.ups_tool import UPSTool
from agents.usps_tool import USPSTool
from models.schemas import ShippingRequest, ShippingQuote, ShippingResponse, CarrierWarning
from config.settings import settings


SYSTEM_PROMPT = """You are a shipping rate advisor AI. You receive a list of shipping quotes 
from FedEx, UPS, and USPS and the user's delivery deadline requirement.

Your job is to:
1. Identify the best value option (lowest cost that meets deadline).
2. Write a clear 2-3 sentence summary explaining:
   - Which carrier/service you recommend and why
   - Any notable cost differences between options
   - Whether dimensional weight affected the pricing

Keep the tone professional but friendly. Be specific with numbers.
Respond ONLY with the summary text — no headers, no bullet points."""


class ShippingOrchestrator:
    """
    LangChain-based orchestrator that:
    1. Spawns FedEx, UPS, USPS sub-agents in parallel (asyncio.gather)
    2. Aggregates and sorts results
    3. Uses an LLM to write a human-readable recommendation summary
    """

    def __init__(self):
        self.fedex = FedExTool()
        self.ups = UPSTool()
        self.usps = USPSTool()

        # LLM for summary generation — falls back gracefully if no API key
        self.llm: Optional[ChatOpenAI] = None
        if settings.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=settings.OPENAI_API_KEY,
            )

    async def get_quotes(self, request: ShippingRequest) -> ShippingResponse:
        """
        Main orchestration method.
        Calls all 3 carrier agents in parallel, aggregates results, generates AI summary.
        """

        # ── Step 1: Spawn all 3 agents concurrently ──────────────────────────
        fedex_task = self.fedex.get_rates(
            request.origin_zip, request.destination_zip,
            request.weight_lbs, request.length_in, request.width_in,
            request.height_in, request.delivery_days,
        )
        ups_task = self.ups.get_rates(
            request.origin_zip, request.destination_zip,
            request.weight_lbs, request.length_in, request.width_in,
            request.height_in, request.delivery_days,
        )
        usps_task = self.usps.get_rates(
            request.origin_zip, request.destination_zip,
            request.weight_lbs, request.length_in, request.width_in,
            request.height_in, request.delivery_days,
        )

        fedex_quotes, ups_quotes, usps_quotes = await asyncio.gather(
            fedex_task, ups_task, usps_task, return_exceptions=True
        )

        # ── Step 2: Aggregate quotes + collect carrier warnings ───────────────
        all_quotes: list[ShippingQuote] = []
        carrier_warnings: list[CarrierWarning] = []

        if isinstance(fedex_quotes, list):
            all_quotes.extend(fedex_quotes)
        else:
            msg = str(fedex_quotes)
            print(f"[Orchestrator] FedEx agent error: {msg}")
            carrier_warnings.append(CarrierWarning(carrier="FedEx", message=msg))

        if isinstance(ups_quotes, list):
            all_quotes.extend(ups_quotes)
        else:
            msg = str(ups_quotes)
            print(f"[Orchestrator] UPS agent error: {msg}")
            carrier_warnings.append(CarrierWarning(carrier="UPS", message=msg))

        if isinstance(usps_quotes, list):
            all_quotes.extend(usps_quotes)
        else:
            msg = str(usps_quotes)
            print(f"[Orchestrator] USPS agent error: {msg}")
            carrier_warnings.append(CarrierWarning(carrier="USPS", message=msg))

        # Sort by cost
        all_quotes.sort(key=lambda q: q.estimated_cost)

        # ── Step 3: Pick best recommendation ─────────────────────────────────
        recommended = all_quotes[0] if all_quotes else None

        # ── Step 4: Generate AI summary ───────────────────────────────────────
        summary = await self._generate_summary(all_quotes, recommended, request)

        return ShippingResponse(
            quotes=all_quotes,
            recommended=recommended,
            ai_summary=summary,
            origin_zip=request.origin_zip,
            destination_zip=request.destination_zip,
            actual_weight=request.weight_lbs,
            carrier_warnings=carrier_warnings,
        )

    async def _generate_summary(
        self,
        quotes: list[ShippingQuote],
        recommended: Optional[ShippingQuote],
        request: ShippingRequest,
    ) -> str:
        """Uses LLM to produce a human-readable summary. Falls back to rule-based if no LLM."""

        if not self.llm or not quotes:
            return self._fallback_summary(quotes, recommended, request)

        quotes_text = "\n".join(
            [f"- {q.carrier} {q.service_name}: ${q.estimated_cost} | {q.estimated_days} day(s) | Billable weight: {q.billable_weight}lbs"
             for q in quotes[:8]]
        )

        user_msg = f"""
User needs a package shipped from ZIP {request.origin_zip} to {request.destination_zip}.
Package: {request.weight_lbs}lbs actual, {request.length_in}x{request.width_in}x{request.height_in} inches.
Must arrive within: {request.delivery_days} day(s).

Available quotes:
{quotes_text}

Recommended: {recommended.carrier} {recommended.service_name} at ${recommended.estimated_cost}
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_msg),
            ])
            return response.content.strip()
        except Exception as e:
            print(f"[LLM] Summary error: {e}")
            return self._fallback_summary(quotes, recommended, request)

    def _fallback_summary(self, quotes, recommended, request) -> str:
        if not quotes:
            return "No carriers found matching your delivery deadline. Try extending your delivery window."

        cheapest = quotes[0]
        fastest = min(quotes, key=lambda q: q.estimated_days)
        dim_note = ""
        if cheapest.dim_weight > cheapest.billable_weight * 0.8:
            dim_note = f" Note: dimensional weight ({cheapest.dim_weight}lbs) is close to actual weight — consider a smaller box."

        return (
            f"Best value: {cheapest.carrier} {cheapest.service_name} at ${cheapest.estimated_cost:.2f} "
            f"arriving in {cheapest.estimated_days} day(s). "
            f"Fastest option is {fastest.carrier} {fastest.service_name} at ${fastest.estimated_cost:.2f} "
            f"with {fastest.estimated_days} day(s) delivery.{dim_note}"
        )
