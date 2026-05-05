from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import login_view, logout_view, role_redirect_view, professor_dashboard_view, student_dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('route/', role_redirect_view, name='role-redirect'),
    path('professor/dashboard/', professor_dashboard_view, name='professor-dashboard'),
    path('student/dashboard/', student_dashboard_view, name='student-dashboard'),
    path('api/accounts/', include('accounts.urls')),
    path('api/attendance/', include('attendance.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)