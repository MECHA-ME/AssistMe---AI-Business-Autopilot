from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='myapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('property/add/', views.add_property, name='add_property'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/add_slot/', views.add_slot, name='add_slot'),
    path('slot/<int:pk>/book/', views.book_slot, name='book_slot'),
    path('booking/<int:pk>/approve/', views.approve_booking, name='approve_booking'),
    path('booking/<int:pk>/reject/', views.reject_booking, name='reject_booking'),
    path('chat/<int:user_id>/', views.chat_view, name='chat'),
    path('assistant/', views.assistant_chat, name='assistant_chat'),
]
