from rest_framework import serializers
from .models import Order, OrderItem, Location, MpesaTransaction
from products.models import Product

class MpesaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MpesaTransaction
        fields = [
            'id',
            'receipt_number',
            'phone_number',
            'amount',
            'transaction_date',
            'merchant_request_id',
            'checkout_request_id',
            'result_code',
            'result_description',
        ]

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'delivery_price']

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product')

    class Meta:
        model = OrderItem
        fields = ['product_id', 'quantity']

        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    is_paid = serializers.BooleanField(read_only=True)  # Include is_paid in API response, but not required during creation

    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'payment_method',
            'transaction_id',
            'total_amount',
            'is_paid',           # ✅ make sure this is included
            'items',
            'created_at',
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
