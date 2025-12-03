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
    # PDF history
    path('report/history/', views.pdf_history_view, name='pdf_history'),
    path('report/history/<int:election_id>/', views.pdf_history_view, name='pdf_history_by_election'),
    path('report/view/<int:report_id>/', views.view_pdf_report, name='view_pdf_report'),
]
