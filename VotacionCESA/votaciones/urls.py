from django.urls import path
from . import views

app_name = 'votaciones'

urlpatterns = [
    path('create-user/', views.create_user_view, name='create_user'),
    path('create-voter/', views.create_voter_view, name='create_voter'),
    path('create-candidate/', views.create_candidate_view, name='create_candidate'),
    # PDF report generation
    path('report/pdf/', views.generate_election_pdf, name='election_pdf'),
    path('report/pdf/<int:election_id>/', views.generate_election_pdf, name='election_pdf_by_id'),
]
