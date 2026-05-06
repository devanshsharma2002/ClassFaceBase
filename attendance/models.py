from django.conf import settings
from django.db import models
from academics.models import Subject, ClassSection, StudentProfile


class AttendanceSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'

    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)
    session_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.class_section} - {self.session_date}"


class AttendancePhoto(models.Model):
    attendance_session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='attendance_photos/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Photo {self.id} for session {self.attendance_session_id}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review Required'

    marked_by_system = models.BooleanField(default=False)
    attendance_session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABSENT)
    confidence_score = models.FloatField(default=0)
    recognized_in_photo_count = models.PositiveIntegerField(default=0)
    reviewed_manually = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student} - {self.attendance_session} - {self.status}"


class AttendanceDispute(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='disputes')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    description = models.TextField()
    proof_file = models.FileField(upload_to='disputes/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispute {self.id} - {self.status}"


class EmailLog(models.Model):
    attendance_session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.recipient_email} - {self.status}"