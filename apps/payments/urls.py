from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('<int:reservation_id>/', views.payment_page, name='payment_page'),
    path('success/', views.payment_success, name='payment_success'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),
]
