from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    name = models.CharField(max_length=50)
    year_order = models.PositiveIntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class ClassSection(models.Model):
    name = models.CharField(max_length=20)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.academic_year.name} - {self.name}"


class Subject(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('code', 'academic_year', 'section')

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProfessorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name() or self.user.email}"


class ProfessorSubjectAssignment(models.Model):
    professor = models.ForeignKey(ProfessorProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('professor', 'subject')

    def __str__(self):
        return f"{self.professor} -> {self.subject}"


class StudentSubjectEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='subject_enrollments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_enrollments')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'subject', 'academic_year', 'class_section')

    def __str__(self):
        return f"{self.student.roll_number} - {self.subject.code}"


class StudentFaceImage(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='face_images')
    image = models.ImageField(upload_to='student_faces/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)
    embedding_data = models.JSONField(blank=True, null=True)
    quality_score = models.FloatField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Face image {self.id} - {self.student.roll_number}"