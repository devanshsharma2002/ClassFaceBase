from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CustomUser
from .serializers import UserSerializer
from academics.models import ProfessorProfile, StudentProfile, ProfessorSubjectAssignment
from attendance.models import AttendanceSession, AttendanceRecord

def login_view(request):
    if request.user.is_authenticated:
        return redirect('role-redirect')
    error = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            return redirect('role-redirect')
        error = 'Invalid credentials'
    return render(request, 'login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def role_redirect_view(request):
    if request.user.role == CustomUser.Role.PROFESSOR:
        return redirect('professor-dashboard')
    if request.user.role == CustomUser.Role.STUDENT:
        return redirect('student-dashboard')
    return redirect('/admin/')
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from attendance.models import AttendanceSession, AttendanceRecord

@login_required
def professor_dashboard_view(request):
    if request.user.role != 'PROFESSOR':
        return redirect('role-redirect')

    sessions = (
        AttendanceSession.objects
        .filter(professor=request.user)
        .select_related('subject', 'class_section')
        .order_by('-session_date', '-created_at')
    )

    sessions = list(sessions)

    total_sessions = len(sessions)
    total_records = 0
    total_present = 0

    for session in sessions:
        records_qs = AttendanceRecord.objects.filter(attendance_session=session)

        session.total_records = records_qs.count()
        session.present_records = records_qs.filter(
            status=AttendanceRecord.Status.PRESENT
        ).count()
        session.absent_records = records_qs.filter(
            status=AttendanceRecord.Status.ABSENT
        ).count()

        session.attendance_percentage = round(
            (session.present_records / session.total_records) * 100, 2
        ) if session.total_records else 0

        total_records += session.total_records
        total_present += session.present_records

    overall_percentage = round(
        (total_present / total_records) * 100, 2
    ) if total_records else 0

    return render(request, 'professor_dashboard.html', {
        'sessions': sessions,
        'total_sessions': total_sessions,
        'total_records': total_records,
        'total_present': total_present,
        'overall_percentage': overall_percentage,
    })

@login_required
def student_dashboard_view(request):
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect('role-redirect')
    profile = StudentProfile.objects.get(user=request.user)
    records = AttendanceRecord.objects.filter(student=profile).select_related('attendance_session__subject').order_by('-attendance_session__session_date')
    total = records.count()
    present = records.filter(status='PRESENT').count()
    percentage = round((present / total) * 100, 2) if total else 0
    return render(request, 'student_dashboard.html', {
        'records': records[:20],
        'percentage': percentage,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    return Response(UserSerializer(request.user).data)