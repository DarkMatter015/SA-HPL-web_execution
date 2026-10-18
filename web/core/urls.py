"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.execution_form_view, name="home"),
    path("historico/", views.history_view, name="history"),
    path("historico/excluir/", views.execution_delete_view, name="execution_delete"),
    path(
        "execucoes/<slug:execution_id>/",
        views.execution_detail_view,
        name="execution_detail",
    ),
    path(
        "execucoes/<slug:execution_id>/pdf/",
        views.execution_pdf_view,
        name="execution_pdf",
    ),
    path("comparativo/", views.execution_compare_view, name="execution_compare"),
    path("comparativo/pdf/", views.comparison_pdf_view, name="comparison_pdf"),
    path("historico/pdf/", views.history_pdf_view, name="history_pdf"),
    path("api/executions/", views.executions_api_view, name="executions_api"),
]
