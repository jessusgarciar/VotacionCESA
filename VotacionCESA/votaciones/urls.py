from django.urls import path
from . import views

app_name = 'votaciones'

urlpatterns = [
    path('create-user/', views.create_user_view, name='create_user'),
    path('create-voter/', views.create_voter_view, name='create_voter'),
    path('create-candidate/', views.create_candidate_view, name='create_candidate'),
]
