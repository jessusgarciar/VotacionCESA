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
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Redirige la raíz a la página de login (evita el 404 en /)
    path('', RedirectView.as_view(url='login/', permanent=False)),

    # 2. Define la URL de login
    path('login/', auth_views.LoginView.as_view(
        # 3. Dile qué plantilla HTML usar
        template_name='registration/login.html' 
    ), name='login'),
    # 4. (Opcional pero recomendado) Añade la URL de logout
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
