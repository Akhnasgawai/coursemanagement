from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("", views.login_view, name="login"),
    # path(
    #     "verify_otp/<str:username>/<str:role>/",
    #     views.verify_otp_view,
    #     name="verify_otp",
    # ),
    path(
        "<str:path>/verify_otp/",
        views.verify_otp_view,
        name="verify_otp",
    ),
    path(
        "verify_otp/",
        views.verify_otp_view,
        name="verify_otp",
    ),
    path("resend_otp/", views.resend_otp, name="resend_otp"),
    path("logout/", views.logout_view, name="logout"),
    path("student_dashboard/", views.student_dashboard, name="student_dashboard"),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("search/", views.student_dashboard, name="search"),
    path("all-courses/", views.teacher_dashboard, name="teacher_dashboard"),
    path("add-course/", views.add_course, name="add_course"),
    path("update-course/<uuid:course_id>/", views.add_course, name="add_course"),
    path("delete-course/", views.delete_course, name="delete_course"),
    path("add-content/<uuid:course_id>/", views.add_content, name="add_content"),
    path("update-content/<uuid:content_id>/", views.add_content, name="update_content"),
    path("delete-content/", views.delete_content, name="delete_content"),
    path("view-students/", views.view_subscribed_student, name="view_subscribed_student"),
    path("view-content/<uuid:course_id>/", views.view_content, name="view_content"),
    path("subscribed-course/", views.purchasedCourse, name="purchased_course"),
    path("success/", views.success, name="success"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("set-password/", views.set_password, name="set_password"),
    path("rating/<int:rating>/<uuid:course_id>/", views.course_ratings, name="course_rating"),
    path('add_quiz/<uuid:course_id>/', views.add_quiz, name='add_quiz'),
    path('update_quiz/<uuid:quiz_id>/', views.add_quiz, name='update_quiz'),
    path('quiz_detail/<uuid:quiz_id>/', views.add_question, name='quiz_detail'),
    path('course_quizzes/<uuid:course_id>/', views.course_quizzes, name='course_quizzes'),
    path('take_quiz/<uuid:quiz_id>/', views.take_quiz, name='take_quiz'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)