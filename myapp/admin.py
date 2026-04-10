from django.contrib import admin
from .models import Message, Lead, Booking, MissedCall, Product

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'channel', 'timestamp')

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('phone', 'name', 'interest', 'status')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'customer_phone', 'service', 'time_slot', 'status')

@admin.register(MissedCall)
class MissedCallAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'handled', 'timestamp')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'stock_quantity', 'category')
    search_fields = ('name', 'sku', 'category')

