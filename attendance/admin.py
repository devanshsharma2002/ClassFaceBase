from django.contrib import admin
from .models import AttendanceSession, AttendancePhoto, AttendanceRecord, AttendanceDispute, EmailLog


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'class_section', 'session_date', 'status', 'professor')
    list_filter = ('status', 'session_date')
    search_fields = ('subject__name', 'class_section__name', 'professor__email')


@admin.register(AttendancePhoto)
class AttendancePhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'attendance_session', 'uploaded_at')
    search_fields = ('attendance_session__subject__name',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'attendance_session', 'student', 'status', 'confidence_score', 'reviewed_manually')
    list_filter = ('status', 'reviewed_manually')
    search_fields = ('student__roll_number', 'student__user__email', 'attendance_session__subject__name')


@admin.register(AttendanceDispute)
class AttendanceDisputeAdmin(admin.ModelAdmin):
    list_display = ('id', 'attendance_record', 'student', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__roll_number', 'student__user__email', 'attendance_record__attendance_session__subject__name')

    def save_model(self, request, obj, form, change):
        old_status = None

        if change and obj.pk:
            old_status = AttendanceDispute.objects.get(pk=obj.pk).status

        super().save_model(request, obj, form, change)

        record = obj.attendance_record

        if obj.status == AttendanceDispute.Status.APPROVED and old_status != AttendanceDispute.Status.APPROVED:
            record.status = AttendanceRecord.Status.PRESENT
            record.reviewed_manually = True
            record.remarks = obj.resolution_note or 'Updated after approved dispute from admin'
            record.save()

        elif obj.status == AttendanceDispute.Status.REJECTED and old_status != AttendanceDispute.Status.REJECTED:
            record.reviewed_manually = True
            if obj.resolution_note:
                record.remarks = obj.resolution_note
            record.save()


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'attendance_session', 'recipient_email', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('recipient_email', 'attendance_session__subject__name')