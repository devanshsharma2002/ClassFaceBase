from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Department,
    AcademicYear,
    ClassSection,
    Subject,
    ProfessorProfile,
    StudentProfile,
    ProfessorSubjectAssignment,
    StudentSubjectEnrollment,
    StudentFaceImage,
)


class ProfessorSubjectAssignmentInline(admin.TabularInline):
    model = ProfessorSubjectAssignment
    extra = 1
    autocomplete_fields = ('subject',)


class StudentFaceImageInline(admin.TabularInline):
    model = StudentFaceImage
    extra = 1
    fields = ('image_preview', 'image', 'is_primary', 'quality_score', 'is_active', 'uploaded_at')
    readonly_fields = ('image_preview', 'uploaded_at')

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="80" height="80" style="object-fit:cover;border-radius:6px;" /></a>',
                obj.image.url,
                obj.image.url,
            )
        return "No image"

    image_preview.short_description = 'Preview'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'year_order', 'department')
    list_filter = ('department',)
    search_fields = ('name', 'department__name')


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'academic_year')
    list_filter = ('academic_year',)
    search_fields = ('name', 'academic_year__name')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'academic_year', 'section')
    list_filter = ('academic_year', 'section')
    search_fields = ('name', 'code')


@admin.register(ProfessorProfile)
class ProfessorProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department', 'employee_id')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id')
    list_filter = ('department',)
    inlines = [ProfessorSubjectAssignmentInline]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'roll_number', 'user', 'department', 'academic_year', 'section', 'face_image_count')
    search_fields = ('roll_number', 'user__email', 'user__first_name', 'user__last_name')
    list_filter = ('department', 'academic_year', 'section')
    inlines = [StudentFaceImageInline]

    def face_image_count(self, obj):
        return obj.face_images.count()

    face_image_count.short_description = 'Face Images'


@admin.register(ProfessorSubjectAssignment)
class ProfessorSubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'professor',
        'subject',
        'subject_year',
        'subject_section',
        'is_active',
    )
    list_filter = ('is_active', 'subject__academic_year', 'subject__section')
    search_fields = (
        'professor__user__email',
        'professor__user__first_name',
        'professor__user__last_name',
        'subject__name',
        'subject__code',
    )
    autocomplete_fields = ('professor', 'subject')

    def subject_year(self, obj):
        return obj.subject.academic_year
    subject_year.short_description = 'Academic Year'

    def subject_section(self, obj):
        return obj.subject.section
    subject_section.short_description = 'Section'


@admin.register(StudentSubjectEnrollment)
class StudentSubjectEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'subject', 'academic_year', 'class_section', 'is_active', 'enrolled_at')
    list_filter = ('is_active', 'academic_year', 'class_section', 'subject')
    search_fields = ('student__roll_number', 'student__user__email', 'subject__name', 'subject__code')
    readonly_fields = ('enrolled_at',)


@admin.register(StudentFaceImage)
class StudentFaceImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'image_preview', 'is_primary', 'quality_score', 'is_active', 'uploaded_at')
    list_filter = ('is_primary', 'is_active')
    search_fields = ('student__roll_number', 'student__user__email')
    readonly_fields = ('image_preview', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.image and not obj.embedding_data:
            from recognition.services import store_embedding_for_image
            store_embedding_for_image(obj)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="80" height="80" style="object-fit:cover;border-radius:6px;" /></a>',
                obj.image.url,
                obj.image.url,
            )
        return "No image"

    image_preview.short_description = 'Preview'