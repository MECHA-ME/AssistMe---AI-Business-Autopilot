from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Message(models.Model):
    user_message = models.TextField()
    ai_response = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    channel = models.CharField(max_length=20, default="WhatsApp")
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.phone_number}: {self.user_message[:50]}"

class Lead(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    interest = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default="New")

    def __str__(self):
        return self.phone

class Booking(models.Model):
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    service = models.CharField(max_length=100)
    time_slot = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, default="confirmed")

    def __str__(self):
        return f"{self.customer_name or self.customer_phone} - {self.service}"

class LoyaltyAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty_account')
    points = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=50, default='Bronze')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.points} pts ({self.tier})"

    def award(self, amount):
        self.points += amount
        if self.points >= 100:
            self.tier = 'Gold'
        elif self.points >= 50:
            self.tier = 'Silver'
        else:
            self.tier = 'Bronze'
        self.save()

class Feedback(models.Model):
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    rating = models.PositiveSmallIntegerField(default=0)
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{username} - {self.rating} stars"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']

class MissedCall(models.Model):
    phone_number = models.CharField(max_length=20)
    handled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Missed call from {self.phone_number}"

class Product(models.Model):
    business_id = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    category = models.CharField(max_length=100, default="Accessory")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_quantity = models.IntegerField(default=0)
    vendor_info = models.TextField(blank=True, null=True)
    warranty = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"
