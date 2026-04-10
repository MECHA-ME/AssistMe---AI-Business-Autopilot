import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from .models import Message, Lead, Booking, MissedCall, Product, LoyaltyAccount, Feedback
from .ai_chatbot import send_whatsapp_message, generate_ai_response
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, time

@login_required
def web_chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        phone = request.user.username if request.user.is_authenticated else data.get('phone', 'anonymous')
        if not message:
            return JsonResponse({'error': 'Message is required.'}, status=400)

        Message.objects.create(
            phone_number=phone,
            user_message=message
        )

        ai_reply = generate_ai_response(message, phone)
        if not ai_reply:
            ai_reply = "Sorry, I'm having trouble responding right now. Please try again later."

        Message.objects.create(
            phone_number=phone,
            ai_response=ai_reply
        )

        return JsonResponse({'reply': ai_reply})

    return JsonResponse({'error': 'Invalid request'}, status=400)


def landing_page(request):
    return render(request, 'landing_page.html')

def custom_logout(request):
    """Safely log out using GET requests since Django 5 restricts it to POST"""
    logout(request)
    return redirect('login')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('customer_chat')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def customer_chat(request):
    """Customer-facing generic chat portal with dummy phone capability."""
    if request.user.is_staff:
        # Redirect staff to their secure portal
        return redirect('admin_dashboard')
    return render(request, 'customer_chat.html')

def user_login(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('user_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/user_login.html', {'form': form})

def staff_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            form.add_error(None, 'Only staff members may access this portal.')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/staff_login.html', {'form': form})


def whatsapp_connect(request):
    default_phone = request.GET.get('phone', '')
    return render(request, 'connect.html', {'default_phone': default_phone})

@login_required
def user_dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    
    phone = request.user.username
    user_name = request.user.get_full_name() or request.user.username
    user_email = request.user.email
    all_bookings = Booking.objects.filter(customer_phone=phone).order_by('-time_slot')
    upcoming_bookings = all_bookings.filter(status='confirmed', time_slot__gte=timezone.now())
    cancelled_bookings = all_bookings.filter(status='cancelled')
    deleted_bookings = all_bookings.filter(status='deleted')
    chat_history = Message.objects.filter(phone_number=phone).order_by('timestamp')[:50]

    loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    product_list = Product.objects.order_by('-stock_quantity')[:12]
    demand_by_service = Booking.objects.values('service').annotate(count=Count('id')).order_by('-count')
    stock_labels = [product.name for product in product_list]
    stock_values = [product.stock_quantity for product in product_list]
    demand_labels = [item['service'] for item in demand_by_service]
    demand_values = [item['count'] for item in demand_by_service]
    
    sales_by_service = Booking.objects.filter(status='confirmed').values('service').annotate(count=Count('id')).order_by('-count')
    sales_labels = [item['service'] for item in sales_by_service]
    sales_values = [item['count'] for item in sales_by_service]
    
    recent_feedback = Feedback.objects.filter(user=request.user).order_by('-submitted_at')[:5]
    average_feedback = Feedback.objects.filter(user=request.user).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    if request.method == 'POST':
        if 'book_slot' in request.POST:
            service = request.POST.get('service')
            date_str = request.POST.get('date')
            time_str = request.POST.get('time')
            if service and date_str and time_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    time = datetime.strptime(time_str, '%H:%M').time()
                    slot_datetime = datetime.combine(date, time)
                    if not Booking.objects.filter(time_slot=slot_datetime, status='confirmed').exists():
                        Booking.objects.create(
                            customer_phone=phone,
                            service=service,
                            time_slot=slot_datetime,
                            status='confirmed'
                        )
                        loyalty_account.award(10)
                        messages.success(request, f'Booking confirmed! You earned 10 loyalty points and now have {loyalty_account.points} points.')
                    else:
                        messages.error(request, 'Slot not available.')
                except ValueError:
                    messages.error(request, 'Invalid date or time.')
            return redirect('user_dashboard')

        if 'delete_booking' in request.POST:
            booking_id = request.POST.get('booking_id')
            booking = get_object_or_404(Booking, id=booking_id, customer_phone=phone)
            booking.status = 'deleted'
            booking.save()
            messages.success(request, 'Booking deleted successfully.')
            return redirect('user_dashboard')

        if 'submit_feedback' in request.POST:
            rating = int(request.POST.get('rating', 0))
            comment = request.POST.get('comment', '').strip()
            if rating <= 0 or rating > 5:
                messages.error(request, 'Please select a valid rating between 1 and 5.')
            else:
                Feedback.objects.create(user=request.user, rating=rating, comment=comment)
                loyalty_account.award(5)
                messages.success(request, f'Thank you for your feedback! You earned 5 loyalty points and now have {loyalty_account.points} points.')
            return redirect('user_dashboard')

    context = {
        'user_name': user_name,
        'user_email': user_email,
        'upcoming_bookings': upcoming_bookings,
        'cancelled_bookings': cancelled_bookings,
        'deleted_bookings': deleted_bookings,
        'chat_history': chat_history,
        'phone': phone,
        'loyalty_points': loyalty_account.points,
        'loyalty_tier': loyalty_account.tier,
        'products': product_list,
        'stock_labels': stock_labels,
        'stock_values': stock_values,
        'demand_labels': demand_labels,
        'demand_values': demand_values,
        'sales_labels': sales_labels,
        'sales_values': sales_values,
        'recent_feedback': recent_feedback,
        'average_feedback': round(average_feedback, 1),
    }
    return render(request, 'user_dashboard.html', context)

@login_required
def dashboard_data(request):
    if request.user.is_staff:
        return JsonResponse({'error': 'Not available for staff dashboard'}, status=403)

    product_list = Product.objects.order_by('-stock_quantity')[:12]
    demand_by_service = Booking.objects.values('service').annotate(count=Count('id')).order_by('-count')
    sales_by_service = Booking.objects.filter(status='confirmed').values('service').annotate(count=Count('id')).order_by('-count')
    stock_labels = [product.name for product in product_list]
    stock_values = [product.stock_quantity for product in product_list]
    demand_labels = [item['service'] for item in demand_by_service]
    demand_values = [item['count'] for item in demand_by_service]
    sales_labels = [item['service'] for item in sales_by_service]
    sales_values = [item['count'] for item in sales_by_service]
    return JsonResponse({
        'stock_labels': stock_labels,
        'stock_values': stock_values,
        'demand_labels': demand_labels,
        'demand_values': demand_values,
        'sales_labels': sales_labels,
        'sales_values': sales_values,
    })

@login_required
def staff_book_slot(request):
    """Staff can book slots on behalf of customers"""
    if not request.user.is_staff:
        return redirect('landing_page')
    
    if request.method == 'POST':
        customer_phone = request.POST.get('customer_phone', '').strip()
        service = request.POST.get('service')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        
        if customer_phone and service and date_str and time_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time = datetime.strptime(time_str, '%H:%M').time()
                slot_datetime = datetime.combine(date, time)
                
                if not Booking.objects.filter(time_slot=slot_datetime, status='confirmed').exists():
                    Booking.objects.create(
                        customer_phone=customer_phone,
                        service=service,
                        time_slot=slot_datetime,
                        status='confirmed'
                    )
                    messages.success(request, f'Booking created for {customer_phone}.')
                else:
                    messages.error(request, 'Slot not available.')
            except ValueError:
                messages.error(request, 'Invalid date or time.')
        else:
            messages.error(request, 'All fields are required.')
        return redirect('admin_dashboard')
    
    return render(request, 'staff_book_slot.html')

@login_required
def admin_dashboard(request):
    """Only admins see the internal metrics and full lead histories"""
    if not request.user.is_staff:
        return redirect('landing_page')
    
    messages_count = Message.objects.count()
    leads_count = Lead.objects.count()
    bookings_count = Booking.objects.count()
    missed_calls_count = MissedCall.objects.count()
    
    recent_leads = Lead.objects.order_by('-id')[:5]
    recent_messages = Message.objects.order_by('-timestamp')[:10]
    
    active_lead = request.GET.get('lead_phone')
    active_history = []
    if active_lead:
        active_history = Message.objects.filter(phone_number=active_lead).order_by('timestamp')

    all_bookings = Booking.objects.all().order_by('-time_slot')
    
    product_list = Product.objects.order_by('-stock_quantity')[:8]
    demand_by_service = Booking.objects.values('service').annotate(count=Count('id')).order_by('-count')
    stock_labels = [product.name for product in product_list]
    stock_values = [product.stock_quantity for product in product_list]
    demand_labels = [item['service'] for item in demand_by_service]
    demand_values = [item['count'] for item in demand_by_service]

    bookings_confirmed = Booking.objects.filter(status='confirmed').count()
    bookings_cancelled = Booking.objects.filter(status='cancelled').count()
    bookings_deleted = Booking.objects.filter(status='deleted').count()

    context = {
        'messages_count': messages_count,
        'leads_count': leads_count,
        'bookings_count': bookings_count,
        'missed_calls_count': missed_calls_count,
        'bookings_confirmed': bookings_confirmed,
        'bookings_cancelled': bookings_cancelled,
        'bookings_deleted': bookings_deleted,
        'recent_leads': recent_leads,
        'recent_messages': recent_messages,
        'active_lead': active_lead,
        'active_history': active_history,
        'bookings': all_bookings,
        'stock_labels': stock_labels,
        'stock_values': stock_values,
        'demand_labels': demand_labels,
        'demand_values': demand_values,
    }
    return render(request, 'dashboard.html', context)

@login_required
def cancel_day_bookings(request):
    """Staff can cancel all bookings for a specific day"""
    if not request.user.is_staff:
        return redirect('landing_page')
    
    if request.method == 'POST':
        cancel_date_str = request.POST.get('cancel_date')
        if cancel_date_str:
            try:
                cancel_date = datetime.strptime(cancel_date_str, '%Y-%m-%d').date()
                bookings_to_cancel = Booking.objects.filter(
                    time_slot__date=cancel_date,
                    status='confirmed'
                )
                
                from .models import Notification
                cancelled_count = 0
                notified_count = 0
                points_awarded = 0
                
                for booking in bookings_to_cancel:
                    booking.status = 'cancelled'
                    booking.save()
                    cancelled_count += 1
                    
                    if booking.customer_phone:
                        from django.contrib.auth.models import User
                        users = User.objects.filter(username=booking.customer_phone)
                        if users.exists():
                            for user in users:
                                loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)
                                loyalty_account.award(25)
                                points_awarded += 25
                                notified_count += 1
                                
                                Notification.objects.create(
                                    user=user,
                                    title='Appointment Cancelled - We Apologize',
                                    message=f'Your {booking.service} appointment on {booking.time_slot.strftime("%B %d, %Y at %I:%M %p")} has been cancelled due to an unforeseen operational issue. We sincerely apologize for the inconvenience. As compensation, we\'ve added 25 loyalty points to your account. Please feel free to rebook at your convenience.'
                                )
                
                if cancelled_count > 0:
                    messages.success(request, f'✓ Cancelled {cancelled_count} bookings for {cancel_date_str}. Notified {notified_count} users with +25 loyalty points each (Total: +{points_awarded} points awarded).')
                else:
                    messages.info(request, f'No confirmed bookings found for {cancel_date_str}.')
            except ValueError:
                messages.error(request, 'Invalid date format.')
        else:
            messages.error(request, 'Please select a date.')
        return redirect('admin_dashboard')
    
    return render(request, 'cancel_day_bookings.html')

@login_required
def allot_slot(request, booking_id):
    if not request.user.is_staff:
        return redirect('landing_page')
    
    booking = get_object_or_404(Booking, id=booking_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # If the status is being changed to 'Cancelled'
        if new_status.lower() == 'cancelled' and booking.status.lower() != 'cancelled':
            from django.contrib.auth.models import User
            from .models import Notification
            from .ai_chatbot import send_whatsapp_message
            
            if booking.customer_phone:
                users = User.objects.filter(username=booking.customer_phone)
                if users.exists():
                    for user in users:
                        loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)
                        loyalty_account.award(25)
                        
                        Notification.objects.create(
                            user=user,
                            title='Appointment Cancelled - Action Required',
                            message=f'Your {booking.service} appointment on {booking.time_slot.strftime("%B %d, %Y at %I:%M %p") if booking.time_slot else "Unknown Date"} has been cancelled by our support team. We apologize for the inconvenience. As compensation, 25 loyalty points have been added to your account.'
                        )
                
                # Send WhatsApp text
                whatsapp_msg = f"Hi from AI Business Autopilot. We had to cancel your {booking.service} appointment on {booking.time_slot.strftime('%b %d at %I:%M %p') if booking.time_slot else 'the requested date'}. We've added 25 Loyalty Points to your account as an apology. Reply here to reschedule!"
                send_whatsapp_message(booking.customer_phone, whatsapp_msg)
                
            messages.success(request, f'Booking cancelled! Customer {booking.customer_phone} has been notified and awarded 25 points.')
        else:
            messages.success(request, f'Booking status updated to {new_status}.')
            
        booking.status = new_status
        booking.save()
        return redirect('admin_dashboard')
    
    return render(request, 'allot_slot.html', {'booking': booking})

@login_required
def slot_management(request):
    if not request.user.is_staff:
        return redirect('landing_page')
    
    days = int(request.GET.get('days', 7))
    # Generate time slots for the next days
    import datetime
    today = datetime.date.today()
    slots = []
    times = [datetime.time(10, 0), datetime.time(14, 0), datetime.time(16, 0)]  # 10 AM, 2 PM, 4 PM
    
    for i in range(days):
        date = today + datetime.timedelta(days=i)
        for t in times:
            slot_datetime = datetime.datetime.combine(date, t)
            # Check if booked
            booked = Booking.objects.filter(time_slot=slot_datetime, status='confirmed').exists()
            slots.append({
                'datetime': slot_datetime,
                'booked': booked,
                'available': not booked  # Assume available if not booked
            })
    
    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        action = request.POST.get('action')  # 'make_available' or 'make_unavailable'
        # For now, just toggle, but since no model, perhaps do nothing or use session
        # In real app, would have Slot model
        pass
    
    return render(request, 'slot_management.html', {'slots': slots, 'days': days})

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'POST':
        # Twilio sends data as form-urlencoded, but if test fallback sends JSON
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                sender_full = data.get('From', '')
                body = data.get('Body', '')
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
        else:
            sender_full = request.POST.get('From', '')
            body = request.POST.get('Body', '')

        if not sender_full or not body:
            return HttpResponse("No From or Body", status=400)
            
        print(f"Incoming message from {sender_full}: {body}")
        
        # Extract number (Twilio format: whatsapp:+1234567890)
        sender_number = sender_full.replace('whatsapp:', '')
        
        # Determine AI Response
        ai_reply = generate_ai_response(body, sender_number)
        
        # Save message to DB
        Message.objects.create(
            user_message=body,
            ai_response=ai_reply,
            phone_number=sender_number
        )
        
        # Send reply back via Twilio
        send_whatsapp_message(sender_number, ai_reply)
        
        # Twilio webhook optionally expects TwiML, but a 200 HTTP response is fine if we use the API to reply
        # Alternatively, we could return TwiML directly
        return HttpResponse("OK")
        
    return HttpResponse("GET not allowed", status=405)

@csrf_exempt
def missed_call(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
        except:
            phone_number = request.POST.get('phone_number')
            
        if not phone_number:
            return JsonResponse({'error': 'phone_number required'}, status=400)
            
        # Create missed call record
        MissedCall.objects.create(phone_number=phone_number)
        
        # Send automated WhatsApp followup
        follow_up_msg = f"Hi! We noticed we missed a call from this number ({phone_number}). How can we help you today? Reply here to chat with us."
        send_whatsapp_message(phone_number, follow_up_msg)
        
        return JsonResponse({'status': 'Missed call logged and follow-up sent.'})
    return JsonResponse({'error': 'POST only'}, status=405)

@csrf_exempt
def dummy_fallback_chat(request):
    """
    Since the prompt requires a fallback chat UI if API fails, this endpoint simulates the webhook behavior directly for the frontend JS.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')
        phone = data.get('phone', '+10000000000') # default test phone
        
        ai_reply = generate_ai_response(user_message, phone)
        
        Message.objects.create(
            user_message=user_message,
            ai_response=ai_reply,
            phone_number=phone,
            channel="Web Fallback"
        )
        return JsonResponse({'reply': ai_reply})
    return JsonResponse({'error': 'Invalid request'})


@csrf_exempt
def twilio_voice_webhook(request):
    """
    Twilio hits this via HTTP POST when someone dials the Twilio Phone Number.
    We drop the call using TwiML <Reject/> to save money, and autonomously
    send a personalized 'Missed Call' WhatsApp conversation starter via Groq!
    """
    if request.method == 'POST':
        caller_phone = request.POST.get('From')
        
        # Log it locally
        if caller_phone:
            MissedCall.objects.create(phone_number=caller_phone)
            
            # Send intro via WhatsApp using the new Groq AI API
            intro_msg = "Yo! This is the PC Hardware AI Bot. I saw you just tried ringing us. 📞 Need an i7 Core or looking to build a new rig today? How can I help?"
            send_whatsapp_message(caller_phone, intro_msg)
            
            # Log the message to the dashboard
            Message.objects.create(
                user_message="<Incoming Voice Call Detected>",
                ai_response=intro_msg,
                phone_number=caller_phone.replace('whatsapp:', ''),
                channel="Voice Webhook"
            )

        # Return empty/reject TwiML to Twilio
        return HttpResponse("<Response><Reject/></Response>", content_type="text/xml")
    
    return HttpResponse("GET not allowed.", status=405)
