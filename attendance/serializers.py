from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord, AttendanceDispute

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    roll_number = serializers.CharField(source='student.roll_number', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student_name', 'roll_number', 'status', 'confidence_score', 'recognized_in_photo_count', 'reviewed_manually', 'remarks']

class AttendanceSessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id', 'subject_name', 'session_date', 'status', 'created_at']

class AttendanceDisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceDispute
        fields = ['id', 'attendance_record', 'description', 'proof_file', 'status', 'resolution_note', 'created_at']
        read_only_fields = ['status', 'resolution_note', 'created_at']