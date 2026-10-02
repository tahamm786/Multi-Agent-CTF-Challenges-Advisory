from django.urls import path
from .views import SolveSessionListCreateView, SolveSessionDetailView, SolveSessionStreamView

urlpatterns = [
    path('sessions/', SolveSessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:pk>/', SolveSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<int:pk>/stream/', SolveSessionStreamView.as_view(), name='session-stream'),
]