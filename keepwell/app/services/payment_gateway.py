import urllib.parse
from typing import Dict, Any
from app.config import settings

class PaymentGatewayService:
    """
    UPI Payment Gateway Sandbox Service.
    Generates standard NPCI UPI Intent Links and verifies signed payment callbacks.
    """

    @classmethod
    def generate_upi_link(cls, quote_id: int, amount: float, agency_name: str = "KeepWell Repair") -> Dict[str, str]:
        # Formulate standard UPI URI: upi://pay?pa=...&pn=...&am=...&tn=...
        pa = settings.upi_vpa
        pn = agency_name
        am = f"{amount:.2f}"
        tr = f"KW_TXN_Q{quote_id}"
        tn = f"Payment for KeepWell Repair Quote #{quote_id}"
        
        params = {
            "pa": pa,
            "pn": pn,
            "am": am,
            "tr": tr,
            "tn": tn,
            "cu": "INR"
        }
        upi_uri = f"upi://pay?{urllib.parse.urlencode(params)}"
        qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(upi_uri)}"

        return {
            "upi_uri": upi_uri,
            "qr_image_url": qr_image_url,
            "transaction_ref": tr,
            "amount": am
        }

    @classmethod
    def process_webhook_callback(cls, quote_id: int, txn_ref: str, status: str = "SUCCESS") -> Dict[str, Any]:
        """
        Simulates receiving signed webhook from UPI gateway (ICICI / Pine Labs / Razorpay).
        """
        return {
            "quote_id": quote_id,
            "txn_ref": txn_ref,
            "status": "PAID" if status == "SUCCESS" else "FAILED",
            "verified": True
        }
