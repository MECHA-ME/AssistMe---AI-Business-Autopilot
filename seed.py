import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from myapp.models import Product

# Clean old data if rerunning
Product.objects.all().delete()

# Dummy Data for Automobiles
tools_data = [
    {
        "name": "Carbon Fiber Rear Spoiler",
        "sku": "AERO-CF-001",
        "category": "Accessory",
        "price": 499.99,
        "stock_quantity": 4,
        "vendor_info": "AeroDynamics Inc.",
        "warranty": "1 Year Limited"
    },
    {
        "name": "Ceramic Performance Brake Pads",
        "sku": "BRK-CER-110",
        "category": "Spare Part",
        "price": 89.50,
        "stock_quantity": 25,
        "vendor_info": "StopTech",
        "warranty": "Lifetime Wear Warranty"
    },
    {
        "name": "Full LED Headlight Conversion Kit",
        "sku": "LGT-LED-H4",
        "category": "Gadget",
        "price": 129.99,
        "stock_quantity": 12,
        "vendor_info": "LumenGlow",
        "warranty": "2 Years"
    },
    {
        "name": "High Flow Intake Air Filter",
        "sku": "PERF-AF-K22",
        "category": "Spare Part",
        "price": 55.00,
        "stock_quantity": 0,
        "vendor_info": "K&N Engineering",
        "warranty": "1 Million Miles"
    },
    {
        "name": "OBD2 Bluetooth Diagnostic Scanner",
        "sku": "ELEC-OBD-BT",
        "category": "Gadget",
        "price": 24.99,
        "stock_quantity": 45,
        "vendor_info": "AutoDiagnostics",
        "warranty": "6 Months"
    }
]

for item in tools_data:
    Product.objects.create(**item)

print(f"Successfully seeded {Product.objects.count()} automobile products!")
