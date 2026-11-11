from django.contrib import admin
from django.utils.html import format_html
from .models import CandidateApplication, HRProfile

@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display  = ['get_name', 'get_email', 'company', 'designation', 'approval_status', 'created_at', 'action_btn']
    list_filter   = ['approval_status']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'company']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_selected', 'reject_selected']

    def get_name(self, obj): return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'

    def get_email(self, obj): return obj.user.email
    get_email.short_description = 'Email'

    def action_btn(self, obj):
        if obj.approval_status == 'pending':
            return format_html(
                '<a class="button" href="/admin/screening/hrprofile/{}/change/" '
                'style="background:#1D9E75;color:#fff;padding:4px 12px;border-radius:5px;'
                'text-decoration:none;font-size:12px">Review</a>', obj.pk)
        color = '#1D9E75' if obj.approval_status == 'approved' else '#c0392b'
        return format_html('<span style="color:{}">{}</span>', color, obj.get_approval_status_display())
    action_btn.short_description = 'Action'

    def approve_selected(self, request, queryset):
        queryset.update(approval_status='approved', approved_by=request.user)
        self.message_user(request, f'{queryset.count()} HR account(s) approved.')
    approve_selected.short_description = '✅ Approve selected'

    def reject_selected(self, request, queryset):
        queryset.update(approval_status='rejected')
        self.message_user(request, f'{queryset.count()} HR account(s) rejected.')
    reject_selected.short_description = '❌ Reject selected'

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('HR Details', {'fields': ('company', 'department', 'designation', 'phone', 'employee_id')}),
        ('Approval', {'fields': ('approval_status', 'rejection_reason', 'approved_by', 'approved_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(CandidateApplication)
class CandidateApplicationAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'email', 'applied_role', 'qualification', 'status', 'created_at']
    list_filter   = ['status', 'applied_role', 'has_experience', 'qualification']
    search_fields = ['full_name', 'email', 'applied_role', 'skills']
    readonly_fields = ['created_at', 'updated_at', 'session_key']
    list_editable = ['status']
    ordering      = ['-created_at']
    fieldsets = (
        ('Personal',    {'fields': ('full_name', 'email', 'phone', 'linkedin')}),
        ('Education',   {'fields': ('qualification', 'field_of_study', 'institution', 'graduation_year', 'cgpa')}),
        ('Application', {'fields': ('applied_role', 'has_experience', 'company', 'previous_role', 'work_duration', 'skills')}),
        ('Offer',       {'fields': ('notice_period', 'expected_salary', 'cover_note')}),
        ('Meta',        {'fields': ('status', 'session_key', 'current_question', 'created_at', 'updated_at')}),
    )
