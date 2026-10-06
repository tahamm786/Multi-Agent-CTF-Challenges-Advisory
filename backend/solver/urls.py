from django.urls import path
from .views import (
    SolveSessionListCreateView, SolveSessionDetailView, SolveSessionStreamView,
    RegisterView, LoginView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('sessions/', SolveSessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:pk>/', SolveSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<int:pk>/stream/', SolveSessionStreamView.as_view(), name='session-stream'),
]