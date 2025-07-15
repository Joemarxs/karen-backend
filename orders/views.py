import re
import logging
from decimal import Decimal
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser
from django.db.utils import IntegrityError
from django.db.models import Q

from .models import Order, Location, MpesaTransaction, OrderItem
from .serializers import OrderSerializer, LocationSerializer, MpesaTransactionSerializer


from django.db.models.functions import TruncMonth
from django.db.models import Sum

from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsAdminUserOnly

logger = logging.getLogger(__name__)


class LocationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserOnly]

    def get_object(self, id):
        try:
            return Location.objects.get(id=id)
        except Location.DoesNotExist:
            return None

    def put(self, request, id):
        location = self.get_object(id)
        if not location:
            return Response({"error": "Location not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LocationSerializer(location, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        location = self.get_object(id)
        if not location:
            return Response({"error": "Location not found."}, status=status.HTTP_404_NOT_FOUND)
        
        location.delete()
        return Response({"message": "Location deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class MonthlyEarningsView(APIView):
    def get(self, request):
        # Only paid orders
        earnings = (
            Order.objects
            .filter(is_paid=True)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total_earnings=Sum("total_amount"))
            .order_by("month")
        )

        # Format the response
        data = [
            {
                "month": entry["month"].strftime("%Y-%m"),
                "total_earnings": float(entry["total_earnings"])
            }
            for entry in earnings
        ]

        return Response(data, status=status.HTTP_200_OK)


def normalize_phone(phone):
    """
    Normalize Safaricom phone numbers to 07XXXXXXXX or 01XXXXXXXX
    Accepts:
        - 2547XXXXXXXX → 07XXXXXXXX
        - 2541XXXXXXXX → 01XXXXXXXX
        - Already normalized formats remain unchanged
    """
    phone = str(phone).strip()
    if phone.startswith("254") and len(phone) == 12:
        return "0" + phone[3:]
    elif phone.startswith("07") or phone.startswith("01"):
        return phone
    return phone


class MpesaTransactionListView(APIView):
    def get(self, request):
        transactions = MpesaTransaction.objects.all().order_by('-transaction_date')
        serializer = MpesaTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MpesaTransactionByPhoneView(APIView):
    def get(self, request):
        phone = request.GET.get("phone")
        if not phone:
            return Response({"error": "Phone number is required (?phone=...)"}, status=status.HTTP_400_BAD_REQUEST)

        phone = phone.strip().replace(" ", "").replace("+", "")

        # Normalize to 07/01 and international format
        if phone.startswith("254") and len(phone) == 12:
            local_format = "0" + phone[3:]         # e.g., 254113055523 → 0113055523
            intl_format = phone                    # stays 254113055523
        elif phone.startswith("0") and len(phone) == 10:
            local_format = phone                   # stays 0113055523
            intl_format = "254" + phone[1:]        # e.g., 0113055523 → 254113055523
        else:
            return Response({"error": "Invalid phone number format"}, status=status.HTTP_400_BAD_REQUEST)

        # Query using both formats
        transactions = MpesaTransaction.objects.filter(
            Q(phone_number=local_format) | Q(phone_number=intl_format)
        ).order_by("-transaction_date")

        if not transactions.exists():
            return Response({"message": "No transactions found for this phone number."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MpesaTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MpesaStatusByCheckoutIDView(APIView):
    def get(self, request):
        id = request.GET.get("id")
        if not id:
            return Response({"error": "Missing id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=id)
            return Response({"order_paid": order.is_paid}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)


class MpesaCallbackView(APIView):
    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        try:
            logger.info("📦 Received M-Pesa callback: %s", request.data)  # 📍 Added log

            stk_callback = request.data.get("Body", {}).get("stkCallback", {})
            if not stk_callback:
                logger.error("Missing stkCallback in request data.")
                return Response({"error": "Invalid callback data"}, status=status.HTTP_400_BAD_REQUEST)

            if stk_callback.get("ResultCode") != 0:
                logger.info("Transaction failed: %s", stk_callback.get("ResultDesc"))
                return Response({"message": "Transaction failed or cancelled"}, status=status.HTTP_200_OK)

            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta_dict = {item["Name"]: item.get("Value") for item in metadata}

            receipt_number = meta_dict.get("MpesaReceiptNumber")
            phone_number = str(meta_dict.get("PhoneNumber", ""))
            raw_amount = meta_dict.get("Amount", 0)
            raw_date = str(meta_dict.get("TransactionDate", ""))
            account_reference = stk_callback.get("AccountReference")
            checkout_request_id = stk_callback.get("CheckoutRequestID")  # 📍 pulled out for logging

            logger.info("💾 CheckoutRequestID to be saved: %s", checkout_request_id)  # 📍 Added log

            if not (receipt_number and phone_number and raw_date):
                logger.warning("Missing required metadata")
                return Response({"error": "Incomplete callback metadata"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                transaction_date = datetime.strptime(raw_date, "%Y%m%d%H%M%S")
            except ValueError:
                logger.error("Invalid date format: %s", raw_date)
                return Response({"error": "Invalid transaction date format"}, status=status.HTTP_400_BAD_REQUEST)

            amount = Decimal(str(raw_amount))
            normalized_phone = normalize_phone(phone_number)

            order = None
            if account_reference:
                try:
                    order_id = int(account_reference)
                    order = Order.objects.get(id=order_id)
                    logger.info("Found order #%s via AccountReference", order_id)
                except (ValueError, Order.DoesNotExist):
                    logger.warning("No order found with AccountReference: %s", account_reference)

            try:
                MpesaTransaction.objects.create(
                    receipt_number=receipt_number,
                    phone_number=normalized_phone,
                    amount=amount,
                    transaction_date=transaction_date,
                    merchant_request_id=stk_callback.get("MerchantRequestID"),
                    checkout_request_id=checkout_request_id,
                    result_code=stk_callback.get("ResultCode"),
                    result_description=stk_callback.get("ResultDesc"),
                    order=order
                )
            except IntegrityError:
                logger.warning("Duplicate receipt number: %s", receipt_number)
                return Response(
                    {"error": f"A transaction with receipt number '{receipt_number}' already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            matched_order = order
            if not matched_order:
                matched_order = Order.objects.filter(
                    Q(customer_phone=normalized_phone) | Q(customer_phone=phone_number),
                    total_amount=amount,
                    is_paid=False,
                    transaction_id__in=["", None]
                ).order_by('-created_at').first()

            if matched_order:
                matched_order.transaction_id = receipt_number
                matched_order.customer_phone = normalized_phone
                matched_order.is_paid = True
                matched_order.save()
                logger.info("✅ Order #%s updated with transaction %s", matched_order.id, receipt_number)
                return Response({"message": f"Order {matched_order.id} updated with payment"}, status=status.HTTP_200_OK)
            else:
                logger.warning("⚠️ No matching order found for phone %s and amount %s", normalized_phone, amount)

            return Response({"message": "Callback received and logged"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("❌ Error processing callback")
            return Response({"error": "Unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminUserOnly()]
        return [AllowAny()]  # Anyone can GET

    def get(self, request):
        locations = Location.objects.all()
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderCreateView(APIView):
    def post(self, request):
        data = request.data.copy()
        data['transaction_id'] = ""
        data['is_paid'] = False
        data['customer_phone'] = normalize_phone(data.get('customer_phone', ''))
        serializer = OrderSerializer(data=data)
        if serializer.is_valid():
            order = serializer.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderByPhoneView(APIView):
    def get(self, request):
        phone = request.GET.get('phone')
        if not phone:
            return Response({"error": "Phone number is required (?phone=...)"}, status=status.HTTP_400_BAD_REQUEST)

        # Accept 07XXXXXXXX, 01XXXXXXXX, 2547XXXXXXXX, 2541XXXXXXXX
        pattern = re.compile(r'^(0[17]\d{8}|254[17]\d{8})$')
        if not pattern.match(phone):
            return Response({
                "error": "Invalid phone number format. Use 07XXXXXXXX, 01XXXXXXXX, 2547XXXXXXXX, or 2541XXXXXXXX."
            }, status=status.HTTP_400_BAD_REQUEST)

        normalized_phone = normalize_phone(phone)

        orders = Order.objects.filter(customer_phone=normalized_phone).order_by('-created_at')
        if not orders.exists():
            return Response({"message": "No orders found for this phone number."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllOrdersView(APIView):
    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrdersByDateView(APIView):
    def get(self, request):
        date_str = request.GET.get('date')
        if not date_str:
            return Response({"error": "Date query parameter (?date=YYYY-MM-DD) is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)

        orders = Order.objects.filter(created_at__date=date).order_by('-created_at')
        if not orders.exists():
            return Response({"message": "No orders found for the specified date."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
