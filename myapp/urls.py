from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('chat/', views.customer_chat, name='customer_chat'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('connect/', views.whatsapp_connect, name='whatsapp_connect'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('allot-slot/<int:booking_id>/', views.allot_slot, name='allot_slot'),
    path('slot-management/', views.slot_management, name='slot_management'),
    path('webhook/whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('webhook/voice/', views.twilio_voice_webhook, name='twilio_voice_webhook'),
    path('missed_call/', views.missed_call, name='missed_call'),
    path('api/chat/', views.web_chat, name='api_chat'),
    path('api/web-chat/', views.web_chat, name='web_chat'),
    path('api/dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('cancel-day-bookings/', views.cancel_day_bookings, name='cancel_day_bookings'),
    path('staff-book-slot/', views.staff_book_slot, name='staff_book_slot'),
]
