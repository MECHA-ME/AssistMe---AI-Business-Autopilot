from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('OWNER', 'Owner'),
        ('BUYER', 'Buyer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='BUYER')

    def is_owner(self):
        return self.role == 'OWNER'

    def is_buyer(self):
        return self.role == 'BUYER'


class Property(models.Model):
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='properties')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to='property_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Slot(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'time']
        unique_together = ('property', 'date', 'time')

    def __str__(self):
        return f"{self.property.title} - {self.date} {self.time}"


class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='bookings')
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.buyer.username} for {self.slot}"


class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"from {self.sender.username} to {self.receiver.username} at {self.timestamp}"
