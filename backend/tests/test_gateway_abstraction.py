import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.execution.gateway_factory import get_gateway
from app.execution.gateway_interface import PaymentGateway
from app.execution.razorpay_client import RazorpayTestClient


def test_razorpay_client_implements_the_interface():
    assert issubclass(RazorpayTestClient, PaymentGateway)


def test_factory_returns_razorpay_by_default():
    gateway = get_gateway()
    assert isinstance(gateway, PaymentGateway)
    assert isinstance(gateway, RazorpayTestClient)


def test_factory_rejects_unregistered_gateway():
    try:
        get_gateway("stripe")
        assert False, "expected ValueError for an unregistered gateway"
    except ValueError as e:
        assert "stripe" in str(e)
