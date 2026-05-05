import csv
from io import StringIO

from django.core.mail import EmailMessage
from django.utils import timezone

from .models import AttendanceRecord, EmailLog


def build_attendance_csv(session):
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'session_id',
        'date',
        'subject_code',
        'subject_name',
        'class_section',
        'roll_number',
        'student_name',
        'status',
        'confidence_score',
        'recognized_in_photo_count',
        'reviewed_manually',
        'timestamp',
    ])

    records = session.records.select_related('student__user').all()

    for record in records:
        writer.writerow([
            session.id,
            session.session_date,
            getattr(session.subject, 'code', ''),
            session.subject.name,
            str(session.class_section),
            record.student.roll_number,
            record.student.user.get_full_name() or record.student.user.email,
            record.status,
            record.confidence_score,
            record.recognized_in_photo_count,
            record.reviewed_manually,
            timezone.now().isoformat(),
        ])

    return output.getvalue()


def send_attendance_email(session):
    recipient = session.professor.email
    subject = f'Attendance Report - {session.subject.name} - {session.session_date}'
    csv_content = build_attendance_csv(session)

    email_log = EmailLog.objects.create(
        attendance_session=session,
        recipient_email=recipient,
        subject=subject,
        status='PENDING',
    )

    present_count = session.records.filter(status=AttendanceRecord.Status.PRESENT).count()
    total_count = session.records.count()

    body = (
        f'Attendance session {session.id} has been finalized.\n\n'
        f'Subject: {session.subject.name}\n'
        f'Date: {session.session_date}\n'
        f'Class Section: {session.class_section}\n'
        f'Present: {present_count}\n'
        f'Total Records: {total_count}\n\n'
        f'The CSV report is attached.'
    )

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            to=[recipient],
        )
        email.attach(
            f'attendance_session_{session.id}.csv',
            csv_content,
            'text/csv'
        )
        email.send()

        email_log.status = 'SENT'
        email_log.sent_at = timezone.now()
        email_log.save()

        return True, None
    except Exception as exc:
        email_log.status = 'FAILED'
        email_log.error_message = str(exc)
        email_log.save()

        return False, str(exc)