"""
URL configuration for VotacionCESA project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from votaciones import views as vot_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Servir homepage en la raíz usando una TemplateView
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Página de resultados
    path('resultados/', TemplateView.as_view(template_name='resultados.html'), name='resultados'),
    # Página del explorador de blockchain
    path('blockchain/', TemplateView.as_view(template_name='blockchain.html'), name='blockchain'),

    # Página de login
    # Página de login (usar vista estándar de Django)
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    # Logout (redirige al login una vez cerrado sesión)
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # API endpoints (candidates + vote)
    path('api/candidates/', vot_views.api_candidates, name='api_candidates'),
    path('api/vote/', vot_views.api_vote, name='api_vote'),
    # Elections listing
    path('api/elections/', vot_views.api_elections, name='api_elections'),
    path('api/stats/', vot_views.api_stats, name='api_stats'),
    # Blockchain records (used by blockchain explorer)
    path('api/blockchain/records/', vot_views.api_blockchain_records, name='api_blockchain_records'),
]
