"""
General contract every payment gateway integration must implement.

This exists so the pipelines depend on a gateway CONCEPT, not on Razorpay
specifically. Razorpay is the only implementation today (RazorpayTestClient
in razorpay_client.py, wrapped via get_gateway() in gateway_factory.py) —
adding another provider means writing one new class that implements this
interface, not changing any pipeline code.
"""

from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    @abstractmethod
    def create_recovery_link(self, txn: dict, cause: str) -> dict:
        """
        Attempt a recovery action (retry / recovery link / reminder) for a
        transaction. Must return a dict containing at minimum:
          - "mode": str describing how the result was produced
                    (e.g. "live_test_api", "simulated_test_mode", "live_test_api_error")
          - "succeeded": bool, when the outcome is known synchronously
        Implementations may return provider-specific extra fields
        (link_id, short_url, etc.) — callers should not assume every
        gateway returns the same extra fields, only the two above.
        """
        raise NotImplementedError
