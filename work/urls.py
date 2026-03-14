from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Help Requests
    path('request/new/', views.create_help_request, name='create_help_request'),
    path('request/<int:pk>/', views.help_request_detail, name='help_request_detail'),
    path('browse/', views.browse_requests, name='browse_requests'),
    path('my-requests/', views.my_requests, name='my_requests'),

    # Applications
    path('request/<int:pk>/apply/', views.apply_to_help, name='apply_to_help'),
    path('application/<int:pk>/accept/', views.accept_application, name='accept_application'),
    path('application/<int:pk>/reject/', views.reject_application, name='reject_application'),
    path('application/<int:pk>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('application/<int:pk>/complete/', views.complete_application, name='complete_application'),
    path('my-applications/', views.my_applications, name='my_applications'),

    # Request Management
    path('request/<int:pk>/resolve/', views.resolve_request, name='resolve_request'),
    path('request/<int:pk>/close/', views.close_request, name='close_request'),
    path('request/<int:pk>/completed/', views.mark_completed, name='mark_completed'),

    # Payment
    path('request/<int:pk>/payment/', views.payment_page, name='payment_page'),
    path('request/<int:pk>/payment/create-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('request/<int:pk>/payment/confirm/', views.confirm_payment, name='confirm_payment'),
    path('request/<int:pk>/payment/receipt/', views.payment_receipt, name='payment_receipt'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
]

