import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from myapp.models import Product

# Clean old data if rerunning
Product.objects.all().delete()

# Dummy Data for Hardware Components
hardware_data = [
    {
        "name": "Intel Core i7-13700K 16-Core Processor",
        "sku": "CPU-INT-i7-137",
        "category": "CPU",
        "price": 389.99,
        "stock_quantity": 42,
        "vendor_info": "Intel",
        "warranty": "3 Year Limited"
    },
    {
        "name": "NVIDIA GeForce RTX 4070 Ti 12GB",
        "sku": "GPU-NV-4070TI",
        "category": "GPU",
        "price": 799.00,
        "stock_quantity": 5,
        "vendor_info": "NVIDIA",
        "warranty": "3 Years"
    },
    {
        "name": "Corsair Vengeance RGB 32GB (2x16GB) DDR5",
        "sku": "RAM-COR-32G-D5",
        "category": "Memory",
        "price": 114.99,
        "stock_quantity": 80,
        "vendor_info": "Corsair",
        "warranty": "Lifetime Limited"
    },
    {
        "name": "Samsung 990 PRO 2TB PCIe 4.0 NVMe SSD",
        "sku": "SSD-SAM-990-2T",
        "category": "Storage",
        "price": 169.99,
        "stock_quantity": 15,
        "vendor_info": "Samsung",
        "warranty": "5 Years or 1200 TBW"
    },
    {
        "name": "ASUS ROG Strix Z790-E Gaming Motherboard",
        "sku": "MB-ASUS-Z790E",
        "category": "Motherboard",
        "price": 439.50,
        "stock_quantity": 0,
        "vendor_info": "ASUS",
        "warranty": "3 Years"
    }
]

for item in hardware_data:
    Product.objects.create(**item)

print(f"Successfully seeded {Product.objects.count()} hardware products!")
