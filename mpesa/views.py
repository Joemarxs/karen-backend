# views.py
import base64
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import datetime

def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("+", "")
    
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("254") and len(phone) == 12:
        return phone
    elif phone.startswith("7") or phone.startswith("1"):
        return "254" + phone
    else:
        raise ValueError("Invalid phone number format")



class MpesaTokenView(APIView):
    def get(self, request):
        consumer_key = settings.MPESA_CONSUMER_KEY
        consumer_secret = settings.MPESA_CONSUMER_SECRET
        auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

        credentials = f"{consumer_key}:{consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}"
        }

        response = requests.get(auth_url, headers=headers)
        if response.status_code == 200:
            return Response(response.json())
        return Response({"error": "Failed to get token"}, status=status.HTTP_400_BAD_REQUEST)


class MpesaSTKPushView(APIView):
    def post(self, request):
        amount = request.data.get("amount")
        order_id = request.data.get("order_id")  # <-- ✅ Expect order ID from frontend
        try:
            phone = normalize_phone(request.data.get("phone"))
        except (ValueError, AttributeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

        if not phone or not amount or not order_id:
            return Response({"error": "Phone, amount, and order_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get token
        token = self.get_token()
        if not token:
            return Response({"error": "Unable to retrieve access token"}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare credentials
        shortcode = settings.MPESA_SHORTCODE
        passkey = settings.MPESA_PASSKEY
        callback_url = settings.MPESA_CALLBACK_URL
        print(callback_url)
        print(passkey)
        print(order_id)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": shortcode,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,# Replace this before production
            "AccountReference": str(order_id),  # <-- ✅ This links transaction to specific order
            "TransactionDesc": f"Payment for Order {order_id}"
        }

        stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        response = requests.post(stk_url, json=payload, headers=headers)
        return Response(response.json(), status=response.status_code)
        

    def get_token(self):
        consumer_key = settings.MPESA_CONSUMER_KEY
        consumer_secret = settings.MPESA_CONSUMER_SECRET
        auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        encoded = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        response = requests.get(auth_url, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
