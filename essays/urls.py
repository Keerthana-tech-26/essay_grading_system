from django.urls import path
from . import views

app_name = 'essays'

urlpatterns = [
    path('', views.index, name='index'),
    path('submit/', views.submit_essay, name='submit'),
    path('essay/<int:pk>/', views.essay_detail, name='detail'),
    path('essay/<int:pk>/delete/', views.delete_essay, name='delete'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
