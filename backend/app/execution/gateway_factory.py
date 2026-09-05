"""
Single place pipelines get a payment gateway from. Today "razorpay" is the
only registered implementation — adding a new provider means writing a
class that implements PaymentGateway (see gateway_interface.py) and
registering it in _GATEWAYS below. No pipeline code needs to change.
"""

from app.execution.razorpay_client import razorpay_client
from app.execution.gateway_interface import PaymentGateway

_GATEWAYS = {
    "razorpay": razorpay_client,
    # "cashfree": CashfreeGateway(),   # not implemented — example of how a
    # second provider would be added without touching any pipeline.
}


def get_gateway(name: str = "razorpay") -> PaymentGateway:
    try:
        return _GATEWAYS[name]
    except KeyError:
        raise ValueError(
            f"Unsupported gateway: '{name}'. Registered: {list(_GATEWAYS.keys())}"
        )
