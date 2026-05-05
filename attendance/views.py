import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import (
    ProfessorProfile,
    ProfessorSubjectAssignment,
    StudentProfile,
)
from accounts.models import CustomUser
from recognition.services import process_attendance_photos
from .forms import SessionCreationForm
from .models import AttendanceSession, AttendanceRecord, AttendanceDispute, AttendancePhoto
from .serializers import (
    AttendanceSessionSerializer,
    AttendanceRecordSerializer,
    AttendanceDisputeSerializer,
)
from .services import send_attendance_email


def get_students_for_session(session):
    enrolled_students = StudentProfile.objects.filter(
        subject_enrollments__subject=session.subject,
        subject_enrollments__is_active=True,
    ).select_related('user').distinct()

    if enrolled_students.exists():
        return list(enrolled_students)

    section_year_students = StudentProfile.objects.filter(
        section=session.class_section,
        academic_year=session.subject.academic_year,
    ).select_related('user').distinct()

    if section_year_students.exists():
        return list(section_year_students)

    section_students = StudentProfile.objects.filter(
        section=session.class_section,
    ).select_related('user').distinct()

    if section_students.exists():
        return list(section_students)

    return []






@login_required
def student_dispute_view(request, record_id):
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect('role-redirect')

    record = get_object_or_404(AttendanceRecord, id=record_id)
    profile = get_object_or_404(StudentProfile, user=request.user)

    if record.student != profile:
        messages.error(request, 'You can only dispute your own attendance records.')
        return redirect('student-dashboard')

    if record.attendance_session.status != AttendanceSession.Status.COMPLETED:
        messages.error(request, 'You can only dispute finalized sessions.')
        return redirect('student-dashboard')

    existing_dispute = AttendanceDispute.objects.filter(
        attendance_record=record,
        student=profile,
        status=AttendanceDispute.Status.PENDING
    ).exists()

    if existing_dispute:
        messages.warning(request, 'A pending dispute already exists for this record.')
        return redirect('student-dashboard')

    if request.method == 'POST':
        description = request.POST.get('reason', '').strip()
        proof_file = request.FILES.get('proof')

        if not description:
            messages.error(request, 'Please enter a reason for the dispute.')
            return render(request, 'student_dispute.html', {'record': record})

        AttendanceDispute.objects.create(
            attendance_record=record,
            student=profile,
            description=description,
            proof_file=proof_file,
            status=AttendanceDispute.Status.PENDING
        )
        messages.success(request, 'Dispute submitted successfully.')
        return redirect('student-dashboard')

    return render(request, 'student_dispute.html', {
        'record': record,
    })


@login_required
def dispute_review_view(request):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return redirect('role-redirect')

    disputes = AttendanceDispute.objects.filter(
        attendance_record__attendance_session__professor=request.user
    ).select_related(
        'student__user',
        'attendance_record',
        'attendance_record__attendance_session__subject'
    ).order_by('-created_at')

    if request.method == 'POST':
        dispute_id = request.POST.get('dispute_id')
        resolution_note = request.POST.get('resolution_note', '').strip()

        dispute = get_object_or_404(
            AttendanceDispute,
            id=dispute_id,
            attendance_record__attendance_session__professor=request.user
        )

        record = dispute.attendance_record

        if 'approve' in request.POST:
            dispute.status = AttendanceDispute.Status.APPROVED
            dispute.resolution_note = resolution_note
            dispute.save()

            record.status = AttendanceRecord.Status.PRESENT
            record.reviewed_manually = True
            record.remarks = resolution_note or 'Updated after approved dispute'
            record.save()

            messages.success(request, 'Dispute approved and attendance updated to PRESENT.')
            return redirect('dispute-review')

        elif 'reject' in request.POST:
            dispute.status = AttendanceDispute.Status.REJECTED
            dispute.resolution_note = resolution_note
            dispute.save()

            if resolution_note:
                record.reviewed_manually = True
                record.remarks = resolution_note
                record.save()

            messages.success(request, 'Dispute rejected.')
            return redirect('dispute-review')

    return render(request, 'dispute_review.html', {'disputes': disputes})


@login_required
def create_session_view(request):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return redirect('role-redirect')

    if request.method == 'POST':
        form = SessionCreationForm(request.POST, request.FILES, professor=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.professor = request.user
            session.status = AttendanceSession.Status.COMPLETED
            session.save()

            uploaded_photo = form.cleaned_data.get('photo')
            if uploaded_photo:
                AttendancePhoto.objects.create(
                    attendance_session=session,
                    image=uploaded_photo,
                    notes='Uploaded from professor session form'
                )

            students = get_students_for_session(session)

            for student in students:
                AttendanceRecord.objects.get_or_create(
                    attendance_session=session,
                    student=student,
                    defaults={
                        'status': AttendanceRecord.Status.ABSENT,
                        'confidence_score': 0.0,
                        'recognized_in_photo_count': 0,
                        'reviewed_manually': False,
                        'remarks': 'Waiting for face recognition processing',
                    }
                )

            success, result_message = process_attendance_photos(session)

            if students:
                if success:
                    messages.success(request, f'Attendance session created and processed. {result_message}')
                else:
                    messages.warning(request, f'Session created, but processing issue: {result_message}')
            else:
                messages.warning(request, 'Session created, but no matching students were found for this subject/section/year.')

            return redirect('session-review', session_id=session.id)
    else:
        form = SessionCreationForm(professor=request.user)

    return render(request, 'create_session.html', {'form': form})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def professor_sessions(request):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return Response({'detail': 'Forbidden'}, status=403)

    sessions = AttendanceSession.objects.filter(
        professor=request.user
    ).order_by('-created_at')

    return Response(AttendanceSessionSerializer(sessions, many=True).data)


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def create_demo_session(request):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return Response({'detail': 'Forbidden'}, status=403)

    profile = get_object_or_404(ProfessorProfile, user=request.user)

    assignment_id = request.data.get('assignment_id') or request.query_params.get('assignment_id')

    assignments = ProfessorSubjectAssignment.objects.filter(
        professor=profile,
        is_active=True
    ).select_related('subject__section', 'subject__academic_year')

    if not assignment_id:
        return Response({
            'detail': 'assignment_id is required when professor has multiple subjects',
            'assignments': [
                {
                    'id': assignment.id,
                    'subject': assignment.subject.name,
                    'code': assignment.subject.code,
                    'academic_year': str(assignment.subject.academic_year),
                    'section': str(assignment.subject.section),
                }
                for assignment in assignments
            ]
        }, status=400)

    assignment = get_object_or_404(
        ProfessorSubjectAssignment.objects.select_related('subject__section', 'subject__academic_year'),
        id=assignment_id,
        professor=profile,
        is_active=True
    )

    session = AttendanceSession.objects.create(
        professor=request.user,
        subject=assignment.subject,
        class_section=assignment.subject.section,
        session_date=date.today(),
        status=AttendanceSession.Status.COMPLETED,
    )

    students = get_students_for_session(session)

    for student in students:
        AttendanceRecord.objects.get_or_create(
            attendance_session=session,
            student=student,
            defaults={
                'status': AttendanceRecord.Status.ABSENT,
                'confidence_score': 0.0,
                'recognized_in_photo_count': 0,
                'reviewed_manually': False,
                'remarks': 'Waiting for face recognition processing',
            }
        )

    success, result_message = process_attendance_photos(session)

    return Response({
        'message': result_message if students else 'No matching students were found for this subject/section/year.',
        'success': success if students else False,
        'session_id': session.id,
        'student_count': len(students),
        'subject': assignment.subject.name,
        'section': str(assignment.subject.section),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def professor_stats(request):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return Response({'detail': 'Forbidden'}, status=403)

    records = AttendanceRecord.objects.filter(attendance_session__professor=request.user)
    total = records.count()
    present = records.filter(status=AttendanceRecord.Status.PRESENT).count()
    absent = records.filter(status=AttendanceRecord.Status.ABSENT).count()

    return Response({
        'total_records': total,
        'present_records': present,
        'absent_records': absent,
        'attendance_percentage': round((present / total) * 100, 2) if total else 0,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_records(request):
    if request.user.role != CustomUser.Role.STUDENT:
        return Response({'detail': 'Forbidden'}, status=403)

    profile = get_object_or_404(StudentProfile, user=request.user)
    records = AttendanceRecord.objects.filter(
        student=profile
    ).order_by('-attendance_session__session_date')

    return Response(AttendanceRecordSerializer(records, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_dispute(request):
    if request.user.role != CustomUser.Role.STUDENT:
        return Response({'detail': 'Forbidden'}, status=403)

    profile = get_object_or_404(StudentProfile, user=request.user)
    serializer = AttendanceDisputeSerializer(data=request.data)

    if serializer.is_valid():
        record = serializer.validated_data['attendance_record']

        if record.student_id != profile.id:
            return Response({'detail': 'You can dispute only your own record'}, status=403)

        if record.attendance_session.status != AttendanceSession.Status.COMPLETED:
            return Response({'detail': 'You can dispute only finalized sessions'}, status=400)

        serializer.save(student=profile)
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


@login_required
def session_review_view(request, session_id):
    if request.user.role != CustomUser.Role.PROFESSOR:
        return redirect('role-redirect')

    session = get_object_or_404(AttendanceSession, id=session_id, professor=request.user)

    students = get_students_for_session(session)

    for student in students:
        AttendanceRecord.objects.get_or_create(
            attendance_session=session,
            student=student,
            defaults={
                'status': AttendanceRecord.Status.ABSENT,
                'confidence_score': 0.0,
                'recognized_in_photo_count': 0,
                'reviewed_manually': False,
                'remarks': '',
            }
        )

    if request.method == 'POST':
        if 'process_ai' in request.POST:
            success, result_message = process_attendance_photos(session)
            if success:
                messages.success(request, result_message)
            else:
                messages.warning(request, result_message)
            return redirect('session-review', session_id=session.id)

        records = session.records.select_related('student__user').all()

        for record in records:
            record.status = request.POST.get(f'status_{record.id}', AttendanceRecord.Status.ABSENT)
            record.remarks = request.POST.get(f'remarks_{record.id}', '')
            record.reviewed_manually = True
            record.save()

        if 'finalize' in request.POST:
            session.status = AttendanceSession.Status.COMPLETED
            session.save()

            success, error = send_attendance_email(session)

            if success:
                messages.success(request, 'Session finalized and email sent successfully.')
            else:
                messages.warning(request, f'Session finalized, but email failed: {error}')

            return redirect('professor-dashboard')

        messages.success(request, 'Attendance updated successfully.')
        return redirect('session-review', session_id=session.id)

    records = session.records.select_related('student__user').all()

    return render(request, 'session_review.html', {
        'session': session,
        'records': records,
        'enrollments': len(students),
    })


@login_required
def download_csv(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id, professor=request.user)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_session_{session_id}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'session_id',
        'date',
        'subject',
        'roll_number',
        'student_name',
        'status',
        'confidence_score',
        'recognized_in_photo_count',
        'reviewed_manually',
        'remarks',
    ])

    for record in session.records.select_related('student__user').all():
        writer.writerow([
            session.id,
            session.session_date,
            session.subject.name,
            record.student.roll_number,
            record.student.user.get_full_name() or record.student.user.email,
            record.status,
            record.confidence_score,
            record.recognized_in_photo_count,
            record.reviewed_manually,
            record.remarks,
        ])

    return response