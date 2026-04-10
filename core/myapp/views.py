import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q
from .models import CustomUser, Property, Slot, Booking, Message
from .forms import CustomUserCreationForm, PropertyForm, SlotForm, MessageForm

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'myapp/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'myapp/register.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_owner():
        properties = request.user.properties.all()
        bookings = Booking.objects.filter(slot__property__owner=request.user)
        return render(request, 'myapp/owner_dashboard.html', {'properties': properties, 'bookings': bookings})
    else:
        properties = Property.objects.all()
        user_bookings = request.user.bookings.all()
        return render(request, 'myapp/buyer_dashboard.html', {'properties': properties, 'bookings': user_bookings})

@login_required
def add_property(request):
    if not request.user.is_owner():
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            property = form.save(commit=False)
            property.owner = request.user
            property.save()
            messages.success(request, "Property added successfully.")
            return redirect('dashboard')
    else:
        form = PropertyForm()
    return render(request, 'myapp/add_property.html', {'form': form})

@login_required
def property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    slots = property.slots.all()
    return render(request, 'myapp/property_detail.html', {'property': property, 'slots': slots})

@login_required
def add_slot(request, pk):
    property = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = SlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.property = property
            slot.save()
            messages.success(request, "Slot added successfully.")
            return redirect('property_detail', pk=property.pk)
    else:
        form = SlotForm()
    return render(request, 'myapp/add_slot.html', {'form': form, 'property': property})

@login_required
def book_slot(request, pk):
    if request.user.is_owner():
        return redirect('dashboard')
        
    slot = get_object_or_404(Slot, pk=pk, is_available=True)
    if request.method == 'POST':
        Booking.objects.create(slot=slot, buyer=request.user)
        slot.is_available = False
        slot.save()
        messages.success(request, "Slot booked! Awaiting approval.")
        return redirect('dashboard')
    return render(request, 'myapp/confirm_booking.html', {'slot': slot})

@login_required
def approve_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, slot__property__owner=request.user)
    booking.status = 'APPROVED'
    booking.save()
    messages.success(request, "Booking approved.")
    return redirect('dashboard')

@login_required
def reject_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, slot__property__owner=request.user)
    booking.status = 'REJECTED'
    booking.save()
    booking.slot.is_available = True
    booking.slot.save()
    messages.success(request, "Booking rejected.")
    return redirect('dashboard')

def get_assistant_user():
    assistant, created = CustomUser.objects.get_or_create(
        username='Gemini',
        defaults={'email': 'gemini@local', 'role': 'OWNER'}
    )
    if created:
        assistant.set_unusable_password()
        assistant.save()
    return assistant

def generate_gemini_reply(user_text, state, context):
    normalized = user_text.strip().lower()
    service_keywords = {
        'pc hardware': 'PC Hardware Consultation',
        'hardware': 'PC Hardware Consultation',
        'consultation': 'PC Hardware Consultation',
        'saloon': 'Saloon Appointment',
        'food': 'Food Delivery',
        'automobile': 'Automobile Service',
        'car': 'Automobile Service',
    }

    def detect_service(text):
        for key, label in service_keywords.items():
            if key in text:
                return label
        return None

    def is_yes(text):
        return bool(re.search(r"\b(yes|sure|yep|yeah|okay|ok|please|definitely)\b", text))

    def is_no(text):
        return bool(re.search(r"\b(no|not now|later|don't|do not|cancel)\b", text))

    if state == 'awaiting_service':
        service = detect_service(normalized)
        if service:
            context['service'] = service
            return f"Great choice. What date would you like for {service}? (e.g. 04/15/2026)", 'awaiting_date', context
        return "Sure — which service are you interested in? I can help with PC Hardware Consultation, Saloon Appointment, Food Delivery, or Automobile Service.", 'awaiting_service', context

    if state == 'awaiting_date':
        context['date'] = user_text.strip()
        return "Perfect. What time works best for you?", 'awaiting_time', context

    if state == 'awaiting_time':
        context['time'] = user_text.strip()
        service = context.get('service', 'your service')
        date = context.get('date', 'your chosen date')
        return f"I’ve got {service} scheduled for {date} at {context['time']}. Should I go ahead and create the booking request?", 'awaiting_confirmation', context

    if state == 'awaiting_confirmation':
        if is_yes(normalized):
            service = context.get('service', 'the service')
            date = context.get('date', 'the date')
            time = context.get('time', 'the time')
            reply = f"All set — I’ve drafted a booking request for {service} on {date} at {time}. You can track it in your dashboard and I’ll follow up if the owner confirms it. Anything else I can help with?"
            return reply, 'default', {}
        if is_no(normalized):
            return "No problem. If you want to book a different service or check availability, just let me know.", 'default', {}
        return "Got it. Should I confirm that slot booking for you now?", 'awaiting_confirmation', context

    if any(key in normalized for key in ['book', 'slot', 'appointment', 'schedule', 'reserve']):
        return "I can help you book a slot. Which service would you like to schedule?", 'awaiting_service', context

    if any(key in normalized for key in ['available', 'availability', 'slots', 'open', 'free']):
        return "I can check available services and slots for you. Which service are you interested in?", 'awaiting_service', context

    if detect_service(normalized):
        service = detect_service(normalized)
        context['service'] = service
        return f"Perfect. For {service}, which date would you like to book?", 'awaiting_date', context

    if any(key in normalized for key in ['hi', 'hello', 'hey']):
        return "Hi there! I’m Gemini AssistMe. Ask me about bookings, availability, or PC hardware recommendations and I’ll follow up with the next question.", 'default', context

    return "I’m here to help with bookings, service availability, and hardware recommendations. What would you like to do next?", 'default', context

@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(CustomUser, pk=user_id)
    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) | 
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = other_user
            msg.save()
            return redirect('chat', user_id=other_user.pk)
    else:
        form = MessageForm()
        
    return render(request, 'myapp/chat.html', {
        'messages_list': messages_list,
        'other_user': other_user,
        'form': form
    })

@login_required
def assistant_chat(request):
    assistant = get_assistant_user()
    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=assistant) | Q(sender=assistant, receiver=request.user)
    ).order_by('timestamp')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = assistant
            msg.save()

            state = request.session.get('gemini_state', 'default')
            context = request.session.get('gemini_context', {})
            bot_text, next_state, next_context = generate_gemini_reply(msg.content, state, context)

            Message.objects.create(
                sender=assistant,
                receiver=request.user,
                content=bot_text
            )

            request.session['gemini_state'] = next_state
            request.session['gemini_context'] = next_context
            return redirect('assistant_chat')
    else:
        form = MessageForm()

        if not messages_list.exists():
            greeting = "Hi there! I’m AssistMe. Ask me about PC builds, availability, or bookings and I’ll follow up with the next question."
            Message.objects.create(sender=assistant, receiver=request.user, content=greeting)
            messages_list = Message.objects.filter(
                Q(sender=request.user, receiver=assistant) | Q(sender=assistant, receiver=request.user)
            ).order_by('timestamp')
            request.session['gemini_state'] = 'default'
            request.session['gemini_context'] = {}

    return render(request, 'myapp/assistme_chat.html', {
        'messages_list': messages_list,
        'form': form
    })
