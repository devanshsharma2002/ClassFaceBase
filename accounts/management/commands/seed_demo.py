from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from academics.models import Department, AcademicYear, ClassSection, Subject, ProfessorProfile, StudentProfile, ProfessorSubjectAssignment, StudentSubjectEnrollment
from attendance.models import AttendanceSession, AttendanceRecord
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Seed demo data for ClassFace MVP'

    def handle(self, *args, **kwargs):
        AttendanceRecord.objects.all().delete()
        AttendanceSession.objects.all().delete()
        StudentSubjectEnrollment.objects.all().delete()
        ProfessorSubjectAssignment.objects.all().delete()
        StudentProfile.objects.all().delete()
        ProfessorProfile.objects.all().delete()
        Subject.objects.all().delete()
        ClassSection.objects.all().delete()
        AcademicYear.objects.all().delete()
        Department.objects.all().delete()
        CustomUser.objects.filter(email__in=['admin@classface.local', 'prof@classface.local', 'student@classface.local']).delete()

        dept = Department.objects.create(name='Computer Engineering', code='COMP')
        year = AcademicYear.objects.create(name='Second Year', year_order=2, department=dept)
        section = ClassSection.objects.create(name='A', academic_year=year)
        subject = Subject.objects.create(name='Data Structures', code='DS201', academic_year=year, section=section)

        CustomUser.objects.create_user(
            email='admin@classface.local',
            password='admin12345',
            role=CustomUser.Role.DEPARTMENT_ADMIN,
            first_name='Dept',
            last_name='Admin',
            is_staff=True,
        )
        prof_user = CustomUser.objects.create_user(
            email='prof@classface.local',
            password='prof12345',
            role=CustomUser.Role.PROFESSOR,
            first_name='Riya',
            last_name='Professor',
        )
        student_user = CustomUser.objects.create_user(
            email='student@classface.local',
            password='student12345',
            role=CustomUser.Role.STUDENT,
            first_name='Aman',
            last_name='Student',
        )

        prof_profile = ProfessorProfile.objects.create(user=prof_user, department=dept, employee_id='EMP001')
        student_profile = StudentProfile.objects.create(
            user=student_user,
            department=dept,
            academic_year=year,
            section=section,
            roll_number='CSE-23-001'
        )

        ProfessorSubjectAssignment.objects.create(professor=prof_profile, subject=subject)
        StudentSubjectEnrollment.objects.create(student=student_profile, subject=subject)

        for i in range(3):
            session = AttendanceSession.objects.create(
                professor=prof_user,
                subject=subject,
                class_section=section,
                session_date=date.today() - timedelta(days=i * 2),
                status='COMPLETED'
            )
            AttendanceRecord.objects.create(
                attendance_session=session,
                student=student_profile,
                status='PRESENT' if i != 1 else 'ABSENT',
                confidence_score=0.94 if i != 1 else 0.18,
                recognized_in_photo_count=2 if i != 1 else 0,
                reviewed_manually=False,
                remarks='' if i != 1 else 'Possible missed detection'
            )

        self.stdout.write(self.style.SUCCESS('Demo data created successfully.'))