from django.urls import path
from .views import (
    professor_sessions,
    create_demo_session,
    professor_stats,
    student_records,
    create_dispute,
    download_csv,
    create_session_view,
    session_review_view,
    student_dispute_view,
    dispute_review_view,
)

urlpatterns = [
    path('professor/sessions/', professor_sessions, name='professor-sessions'),
    path('professor/sessions/create-demo/', create_demo_session, name='create-demo-session'),
    path('professor/sessions/create/', create_session_view, name='create-session'),
    path('professor/stats/', professor_stats, name='professor-stats'),
    path('professor/disputes/', dispute_review_view, name='dispute-review'),
    path('student/records/', student_records, name='student-records'),
    path('student/disputes/', create_dispute, name='create-dispute'),
    path('records/<int:record_id>/dispute/', student_dispute_view, name='student-dispute'),
    path('sessions/<int:session_id>/review/', session_review_view, name='session-review'),
    path('sessions/<int:session_id>/download-csv/', download_csv, name='download-csv'),
    
]