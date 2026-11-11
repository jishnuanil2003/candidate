from django.urls import path
from . import views
from . import media

urlpatterns = [
    # Candidate
    path('', views.index, name='index'),
    path('select-language/', views.select_language, name='select_language'),
    path('demo/', views.demo_interview, name='demo'),
    path('interview/', views.interview, name='interview'),
    path('media/interview/<str:lang>/<str:filename>', media.serve_interview_media, name='serve_interview_media'),
    path('api/question/', views.get_question, name='get_question'),
    path('api/answer/', views.submit_answer, name='submit_answer'),
    path('api/transcribe/', views.transcribe_audio, name='transcribe_audio'),
    path('api/tts/', views.text_to_speech, name='text_to_speech'),
    path('api/complete/', views.complete_application, name='complete_application'),
    path('success/', views.success, name='success'),
    path('api/csrf/', views.csrf_token_view, name='csrf_token'),
    # HR Auth
    path('hr/signup/', views.hr_signup, name='hr_signup'),
    path('hr/login/', views.hr_login, name='hr_login'),
    path('hr/logout/', views.hr_logout, name='hr_logout'),
    # HR Dashboard (protected)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    # Admin Panel (superuser only)
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/hr/<int:pk>/', views.hr_detail, name='hr_detail'),
    path('admin-panel/hr/<int:pk>/action/', views.hr_approval_action, name='hr_approval_action'),
]
