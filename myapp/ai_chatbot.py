import os
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError
from twilio.rest import Client
from .models import Message, Lead, Booking, Product, LoyaltyAccount, Notification
from django.contrib.auth.models import User
import re
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta, datetime
import google.generativeai as genai

def send_whatsapp_message(to_number, body):
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')

    if not all([account_sid, auth_token, from_number]):
        print("Twilio credentials not fully configured.")
        return False

    if not from_number.replace(' ', '').startswith('whatsapp:'):
        from_number = f"whatsapp:{from_number.replace(' ', '')}"
        
    if not to_number.replace(' ', '').startswith('whatsapp:'):
        to_number = f"whatsapp:{to_number.replace(' ', '')}"

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        print(f"Message sent SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Failed to send Twilio message: {e}")
        return False

# ----- GEMINI TOOLS -----

def check_availability(date_str: str) -> str:
    """
    Check the availability of slots for a specific date.
    Args:
        date_str: The date to check in YYYY-MM-DD format.
    Returns:
        Information about which slots (10:00, 14:00, 16:00) are booked or available.
    """
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        times = [datetime.strptime("10:00", '%H:%M').time(), 
                 datetime.strptime("14:00", '%H:%M').time(), 
                 datetime.strptime("16:00", '%H:%M').time()]
        
        availability_info = f"Availability for {date_str}:\n"
        for t in times:
            slot_datetime = datetime.combine(date, t)
            booked = Booking.objects.filter(time_slot=slot_datetime, status='confirmed').exists()
            status = "Booked" if booked else "Available"
            availability_info += f"- {t.strftime('%H:%M')}: {status}\n"
        return availability_info
    except Exception as e:
        return f"Error checking availability: {str(e)}. Make sure date format is YYYY-MM-DD."

def book_slot(phone_number: str, service: str, date_str: str, time_str: str) -> str:
    """
    Book a time slot for a customer.
    Args:
        phone_number: The customer's phone number exactly as given.
        service: The service they want (e.g., 'PC Hardware Consultation').
        date_str: The date in YYYY-MM-DD format.
        time_str: The time in HH:MM format (use 10:00, 14:00, or 16:00).
    Returns:
        Success or failure message.
    """
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        slot_datetime = datetime.combine(date, time_obj)
        
        if Booking.objects.filter(time_slot=slot_datetime, status='confirmed').exists():
            return "That slot is already booked. Please choose another."
        
        Booking.objects.create(
            customer_phone=phone_number,
            service=service,
            time_slot=slot_datetime,
            status='confirmed'
        )
        
        # Award loyalty points for booking
        users = User.objects.filter(username=phone_number)
        points_msg = ""
        if users.exists():
            user = users.first()
            loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)
            loyalty_account.award(10)
            points_msg = " and 10 loyalty points awarded"
            
        return f"Booking successful! The slot has been reserved{points_msg}."
    except Exception as e:
        return f"Failed to book slot due to error: {str(e)}"

def cancel_slot(phone_number: str, date_str: str, time_str: str = None) -> str:
    """
    Cancel a customer's booking.
    Args:
        phone_number: The customer's phone number exactly as given.
        date_str: The date in YYYY-MM-DD format.
        time_str: Optional time in HH:MM format.
    Returns:
        Success or failure message.
    """
    try:
        query = Booking.objects.filter(customer_phone=phone_number, status='confirmed')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(time_slot__date=date)
        if time_str:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            query = query.filter(time_slot__time=time_obj)
            
        bookings = list(query)
        if not bookings:
            return "No matching confirmed booking found to cancel."
            
        for booking in bookings:
            booking.status = 'cancelled'
            booking.save()
            
            users = User.objects.filter(username=phone_number)
            if users.exists():
                user = users.first()
                loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)
                loyalty_account.award(25)
                Notification.objects.create(
                    user=user,
                    title='Booking Cancelled',
                    message=f'Your booking for {booking.service} on {booking.time_slot.strftime("%B %d, %Y")} was cancelled. 25 loyalty points awarded.'
                )
        return f"Successfully cancelled {len(bookings)} booking(s). User earned loyalty points."
    except Exception as e:
        return f"Failed to cancel slot due to error: {str(e)}"

def check_stock() -> str:
    """
    Check the current stock of top products.
    """
    products = Product.objects.filter(stock_quantity__gt=0).order_by('-stock_quantity')[:5]
    if products:
        reply = "Here are some top items we have in stock right now:\n"
        for p in products:
            reply += f"- {p.name}: ${p.price}, {p.stock_quantity} available.\n"
        return reply
    return "Right now inventory is low."

# ----- MAIN AI RESPONSE -----

def generate_ai_response(user_message, phone_number):
    lead, created = Lead.objects.get_or_create(phone=phone_number)
    
    google_api_key = os.environ.get('GOOGLE_API_KEY')
    if not google_api_key:
        print("GOOGLE_API_KEY not configured.")
        return "I'm currently unable to connect to my AI engine because the API key is missing."
        
    genai.configure(api_key=google_api_key)
    
    # Enable automatic tool calling
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[check_availability, book_slot, cancel_slot, check_stock],
        system_instruction=(
            "You are AssistMe, the AI Business Autopilot. "
            "You CAN book appointments, check availability, cancel appointments, and check stock using your functions/tools. "
            "If a user asks to cancel, always call the cancel_slot tool. DO NOT tell them to do it manually. "
            "If a user asks to book, call check_availability to see what times are available, then call the book_slot tool. "
            "When booking, you need the Service name, Date (YYYY-MM-DD), and Time (HH:MM). If the user didn't specify these, ask them nicely out loud. "
            "Always talk directly to the user in a friendly, conversational tone. "
            f"The user's identifying phone number is: {phone_number}. Always pass this EXACT string: '{phone_number}' to any tools that require a phone number so you act on their behalf safely."
        )
    )
    
    try:
        # Reconstruct chat history for Gemini
        history = Message.objects.filter(phone_number=phone_number).order_by('-timestamp')[:8]
        gemini_history = []
        for msg in reversed(history):
            if msg.user_message:
                gemini_history.append({"role": "user", "parts": [{"text": msg.user_message}]})
            if msg.ai_response:
                gemini_history.append({"role": "model", "parts": [{"text": msg.ai_response}]})
                
        # Use starting chat
        chat = model.start_chat(history=gemini_history, enable_automatic_function_calling=True)
        response = chat.send_message(user_message)
        
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Sorry, I ran into an error while processing your request to Gemini."
