from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Property, Slot, Booking, Message

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Property)
admin.site.register(Slot)
admin.site.register(Booking)
admin.site.register(Message)
