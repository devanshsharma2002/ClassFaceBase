from django import forms
from .models import AttendanceSession


class SessionCreationForm(forms.ModelForm):
    photo = forms.ImageField(required=False)

    class Meta:
        model = AttendanceSession
        fields = ['subject', 'class_section', 'session_date']
        widgets = {
            'session_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        professor = kwargs.pop('professor', None)
        super().__init__(*args, **kwargs)

        if professor:
            assignments = professor.professorprofile.professorsubjectassignment_set.select_related('subject').all()
            subject_ids = [a.subject_id for a in assignments]
            self.fields['subject'].queryset = self.fields['subject'].queryset.filter(id__in=subject_ids)

            section_ids = list(
                self.fields['subject'].queryset.values_list('section_id', flat=True).distinct()
            )
            self.fields['class_section'].queryset = self.fields['class_section'].queryset.filter(id__in=section_ids)