from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('profile/', views.profile, name='profile'),

        # Admin endpoints
    path('users/', views.get_all_users, name='get_all_users'),
    path('users/<uuid:user_id>/', views.get_user_by_id, name='get_user_by_id'),
]
