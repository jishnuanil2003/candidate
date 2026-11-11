from django.db import models
from django.contrib.auth.models import User

class HRProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hr_profile')
    phone            = models.CharField(max_length=20, blank=True)
    department       = models.CharField(max_length=100, blank=True)   # existing field
    designation      = models.CharField(max_length=100, blank=True)
    employee_id      = models.CharField(max_length=50, blank=True)    # existing field
    company          = models.CharField(max_length=200, blank=True, default='') # new
    approval_status  = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at      = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    approved_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_hrs')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.approval_status})"

    def is_approved(self):
        return self.approval_status == 'approved'

    @property
    def status(self):
        return self.approval_status

    class Meta:
        verbose_name = 'HR Profile'
        verbose_name_plural = 'HR Profiles'
        ordering = ['-created_at']


class CandidateApplication(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
    ]
    full_name        = models.CharField(max_length=200, blank=True)
    email            = models.EmailField(blank=True)
    phone            = models.CharField(max_length=30, blank=True)
    qualification    = models.CharField(max_length=100, blank=True)
    field_of_study   = models.CharField(max_length=150, blank=True)
    institution      = models.CharField(max_length=200, blank=True)
    graduation_year  = models.CharField(max_length=10, blank=True)
    cgpa             = models.CharField(max_length=20, blank=True)
    applied_role     = models.CharField(max_length=100, blank=True)
    has_experience   = models.BooleanField(null=True, blank=True)
    company          = models.CharField(max_length=200, blank=True)
    previous_role    = models.CharField(max_length=100, blank=True)
    work_duration    = models.CharField(max_length=100, blank=True)
    skills           = models.TextField(blank=True)
    notice_period    = models.CharField(max_length=50, blank=True)
    expected_salary  = models.CharField(max_length=50, blank=True)
    linkedin         = models.URLField(blank=True)
    cover_note       = models.TextField(blank=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    session_key      = models.CharField(max_length=100, blank=True)
    current_question = models.IntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name or 'Anonymous'} – {self.applied_role or 'N/A'} ({self.status})"

    def get_skills_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()] if self.skills else []

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Candidate Application'
        verbose_name_plural = 'Candidate Applications'
