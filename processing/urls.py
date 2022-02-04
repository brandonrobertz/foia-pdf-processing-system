"""processing URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from documents import views as documents_views


urlpatterns = [
    path("api/fieldname_values/count", documents_views.fieldname_value_count),
    path("api/fieldname_values", documents_views.fieldname_values),
    path("api/segmentable_home",
         documents_views.GET_segmentable_home,
         name="segmentable_home"),
    path("api/agency/<int:id>",
         documents_views.GET_agency,
         name="agency"),
    # TODO: use query args lookups, default shows all ala DRF
    path("api/pdocs/<int:agency_id>",
         documents_views.GET_pdocs,
         name="pdocs"),
    path("api/pdoc/<int:pdoc_id>",
         documents_views.GET_pdoc,
         name="pdoc"),
    path("api/pdoc_image_segments/<int:pdoc_id>",
         documents_views.GET_pdoc_image_segments,
         name="pdoc_image_segments"),
    path("api/save-segments/<int:pdoc_id>",
         documents_views.POST_save_image_segments,
         name="save_segments"),


]


if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
