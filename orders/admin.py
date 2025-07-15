from django.contrib import admin
from .models import Order, MpesaTransaction, OrderItem, Location    

admin.site.register(Order)
admin.site.register(MpesaTransaction)
admin.site.register(OrderItem)
admin.site.register(Location)
