from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django import forms
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, UserLoginForm, AddCourseForm, AddCourseContentForm, ChangePasswordForm, QuizForm, QuestionForm, OptionForm, get_option_formset
from .models import User, Course, SubscribedCourse, CourseContent, RatingCourse, Quiz, UserResponse, ResponseAnswer, Option, Question
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from .decorators import teacher_required, student_required, admin_required
from django.conf import settings
from .tasks import send_email_task
import random
import razorpay
from dotenv import load_dotenv
from django.core.mail import send_mail
import os
load_dotenv()

# create your views here
@login_required
@admin_required
def register_view(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            role = form.cleaned_data.get("role")  # Store the role in the session
            # request.session["username"] = username
            # request.session["role"] = role
            user = form.save()
            return redirect("register")
            # generate_otp(user) #generate otp for the current user
            # url = reverse('verify_otp', args=["register"])
            # return redirect(url)
        else:
            errors = form.errors
    else:
        form = UserRegistrationForm()
    errors = None
    return render(request, "course/register.html", {"form": form, "errors": errors})

def login_view(request):
    errors = {}
    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            role = form.cleaned_data.get("role")
            try:
                user = User.objects.get(email = email, role=role) # get the username if email and role exists in db
            except:
                try:
                    user = User.objects.get(email = email) # get the email if the try block fails
                    errors[
                        "invalid_role"
                    ] = "Selected role not associated with this email"
                    return render(
                        request,
                        "course/login.html",
                        {"form": form, "errors": errors},
                    )
                except User.DoesNotExist:
                    errors[
                        "bad_credentials"
                    ] = "Invalid Email / Password"
                    return render(
                        request,
                        "course/login.html",
                        {"form": form, "errors": errors},
                    )
            user = authenticate(request, email=email, password=password) #authenticate user with username and password
            if user is not None:
                if user.role == role: #check for the user role
                    login(request, user)
                    # redirect based on role
                    if role == "student": 
                        return redirect("student_dashboard")
                    elif role == 'teacher':
                        return redirect("teacher_dashboard")
                    else:
                        return redirect("admin_dashboard")
                    # request.session["username"] = username
                    # request.session["role"] = role
                    # generate_otp(user)
                    # url = reverse('verify_otp', args=["login"])
                    # return redirect(url)
                else: #raise an error if invalid role is selected
                    errors[
                        "invalid_role"
                    ] = "Selected role not associated with this email"
                    return render(
                        request,
                        "course/login.html",
                        {"form": form, "errors": errors},
                    )
            else: # raise the error if either username or password is incorrect
                errors["bad_credentials"] = "Invalid Email / Password"
                return render(
                    request,
                    "course/login.html",
                    {"form": form, "errors": errors},
                )
        else:
            errors["invalid_data"] = "Invalid form data. Please try again."
            return render(
                request,
                "course/login.html",
                {"form": form, "errors": errors},
        )
    else:
        form = UserLoginForm()
        errors = {}
    return render(request, "course/login.html", {"form": form, "errors": errors})

def resend_otp(request):
    username = request.session.get("username") #get the username from the session
    user = User.objects.get(username = username) # get the user with the username
    generate_otp(user) #generate otp for that user
    url = reverse('verify_otp', args=["login"])
    return redirect(url) 

def generate_otp(user):
    otp = str(random.randint(100000, 999999)) #generate 6 digit otp
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.save() #save the otp and otp created time in user model
    email = user.email
    subject = "Your OTP for Two-Factor Authentication"
    message = f"Your OTP for login is: {otp} \n valid till 5 minutes"
    print("OTP: ", otp)
    # try:
    #     send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    # except Exception as e:
    #     print(str(e))
    # send_email_task.delay(subject, message, settings.DEFAULT_FROM_EMAIL, email) # send otp to user's email

def set_password(request):
    username = request.session.get("username")
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        try:
            form.clean()
            password = form.data.get("password")
            password = make_password(password, hasher='default')
            user = User.objects.get(username=username)
            user.password = password
            user.save()
            return redirect("/")
        except forms.ValidationError as e:
            form = ChangePasswordForm()
            errors = " "
            errors = errors.join(e)
            return render(request, "course/reset_password.html", {"form": form, "errors": errors})

def verify_otp_view(request, path):
    username = request.session.get("username")
    role = request.session.get("role")
    if request.method == "POST":
        post_data = request.POST
        otp = request.POST.get("otp")
        try:
            user = User.objects.get(username=username)
            if (
                user.otp == otp
                and user.otp_created_at + timezone.timedelta(minutes=5)
                >= timezone.now()
            ):
                user.otp = None
                user.otp_created_at = None
                user.save()
                if path == 'login':
                # Perform login or redirect to the dashboard if path is login or register
                    login(request, user)
                    # redirect based on role
                    if role == "student": 
                        return redirect("student_dashboard")
                    else:
                        return redirect("teacher_dashboard")
                elif path == 'register':
                    return redirect("/")
                else:
                    form = ChangePasswordForm()
                    return render(request, "course/reset_password.html", {"form":form})
            else:
                # Handle invalid OTP
                error_message = "Invalid OTP"
                return render(
                    request,
                    "course/verify_otp.html",
                    {"username": username, "error_message": error_message},
                )
        except User.DoesNotExist:
            # Handle user not found
            error_message = "User Not found"
            pass
    error_message = None
    return render(
        request,
        "course/verify_otp.html",
        {"error_message": error_message},
    )


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
@student_required
def student_dashboard(request):
    query = request.GET.get("query")
    if query is None:
        courses_set = Course.objects.all()
    elif query == 'low-to-high':
        courses_set = Course.objects.all().order_by('price')
    elif query == 'high-to-low':
        courses_set = Course.objects.all().order_by('-price')
    elif query == 'newest':
        courses_set = Course.objects.all().order_by('created_at')
    else:
        coursesTitle = Course.objects.filter(title__icontains=query)
        coursesAuthor = Course.objects.filter(created_by__username__icontains=query)
        coursesDescription = Course.objects.filter(description__icontains=query)
        courses_set = coursesTitle | coursesAuthor | coursesDescription
    paginator = Paginator(courses_set, 3)  # Show 10 courses per page.
    page_number = request.GET.get("page", 1)
    try:
        courses = paginator.get_page(page_number)  # returns the desired page object
    except PageNotAnInteger:
        # if page_number is not an integer then assign the first page
        courses = paginator.page(1)
    except EmptyPage:
        # if page is empty then return last page
        courses = paginator.page(paginator.num_pages)
    return render(
            request,
            "course/student_dashboard.html",
            {"courses": courses},
    )



@login_required
@teacher_required
def teacher_dashboard(request):
    courses = Course.objects.filter(created_by_id=request.user.id)
    # form = AddCourseForm()
    # if request.method == "POST":
    #     form = AddCourseForm(request.POST)
    #     if form.is_valid():
    #         course_instance = Course(
    #             title=form.cleaned_data["title"],
    #             description=form.cleaned_data["description"],
    #             price=form.cleaned_data["price"],
    #             # Add other fields from the form as needed
    #             created_by=request.user,
    #         )
    #         course_instance.save()
    return render(
        request,
        "course/teacher_dashboard.html",
        {"courses": courses, "user": request.user},
    )

@login_required
@admin_required
def admin_dashboard(request):
    courses = Course.objects.all()
    return render(
        request,
        "course/admin_dashboard.html",
        {"courses": courses, "user": request.user},
    )

@login_required
@teacher_required
def add_course(request, course_id=None):
    if course_id:
        instance = Course.objects.get(pk=course_id)
        form = AddCourseForm(initial={
            "title": instance.title,
            "description": instance.description,
            "price": instance.price,
        })
        type = "update"
    else:
        instance = None
        form = AddCourseForm()
        type = "create"
    context = {"form": form, "type":type}
    if request.method == "POST":
        form = AddCourseForm(request.POST)
        if form.is_valid():
            if instance:
                instance.title = form.cleaned_data["title"]
                instance.description = form.cleaned_data["description"]
                instance.price = form.cleaned_data["price"]
                instance.save()
            else:
                course_instance = Course(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    price=form.cleaned_data["price"],
                    # Add other fields from the form as needed
                    created_by=request.user,
                )
                course_instance.save()
                students = SubscribedCourse.objects.filter(courseId__created_by__id = request.user.id, is_paid = True)
                subject = "New Course Alert: Explore Exciting Knowledge!"
                for student in students:
                    message = f"Hi {student.userId.username}, We are excited to bring some fantastic news your way. One of our esteemed authors, {request.user.username}, has just launched a brand new course, titled '{form.cleaned_data['title']}'. As a student who has demonstrated a strong passion for learning, we wanted to personally inform you about this valuable addition to our course catalog.\n\nBest Regards,\n\nThe Course Academy Team."
                    email = student.userId.email
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                    # send_email_task.delay(subject, message, settings.DEFAULT_FROM_EMAIL, email)           
        return redirect("teacher_dashboard")
    return render(request, "course/add_course.html", context)

@login_required
@teacher_required
def delete_course(request):
    course_id = request.GET.get('course_id')
    print("COURSE ID", course_id)
    try:
        course = Course.objects.get(pk = course_id)
        course.delete()
    except:
        return redirect("teacher_dashboard")
    return redirect("teacher_dashboard")

@login_required
@teacher_required
def add_content(request, course_id=None, content_id=None):
    if course_id:
        try:
            course_name = Course.objects.get(pk=course_id)
            form = AddCourseContentForm()
            form.fields['course_id'].initial = course_name
        except:
            return redirect("teacher_dashboard")
    elif content_id:
        try:
            instance = CourseContent.objects.get(pk=content_id)
            form = AddCourseContentForm(initial={
                "course_id": instance.course_id.title,
                "content_title": instance.content_title,
                "content": instance.content,
                "content_link": instance.content_link,
            })
        except:
            return redirect("teacher_dashboard")
    if request.method == "POST":
        form = AddCourseContentForm(request.POST)
        try:
            instance = CourseContent.objects.get(pk=content_id)
        except:
            instance = None
        if instance:
            instance.content_title = request.POST['content_title']
            instance.content = request.POST['content']
            instance.content_link = request.POST['content_link']
            instance.save()
        else:
            print("UPDATE STARTED")
            course_content_instance = CourseContent(
                course_id = course_name,
                content_title = request.POST['content_title'],
                content = request.POST['content'],
                content_link = request.POST['content_link']
            )
            course_content_instance.save()
            form = AddCourseContentForm()
        SubscribedStudents = SubscribedCourse.objects.filter(courseId_id = course_id)
        for student in SubscribedStudents:
            subject = f'New Topic Alert: Expand Your Knowledge in {course_name}'
            message = f'Hi {student.userId.username},\nWe are thrilled to inform you that there\'s a new addition to your purchased course, "{course_name}". Our dedicated instructors have just introduced a fascinating new topic titled "{request.POST["content_title"]}". As a valued student who has invested in your education with us, we believe this latest topic will be an exciting and valuable expansion to your existing knowledge.\n\nBest Regards,\nThe Course Academy Team.'
            email = student.userId.email
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            # send_email_task.delay(subject, message, settings.DEFAULT_FROM_EMAIL, email)
        return redirect("teacher_dashboard")
    return render(request, "course/add_content.html", {"form":form})

@login_required
@teacher_required
def delete_content(request):
    content_id = request.GET.get('content_id')
    print(content_id)
    try:
        content = CourseContent.objects.get(pk = content_id)
        content.delete()
    except:
        return redirect("teacher_dashboard")
    return redirect("teacher_dashboard")

@login_required
@student_required
def success(request):
    order_id = request.GET.get('order_id')
    subscribed = SubscribedCourse.objects.get(razor_pay_order_id = order_id)
    subscribed.is_paid = True
    subscribed.razor_pay_payment_id = request.GET.get('payment_id')
    subscribed.razor_pay_payment_signature = request.GET.get('razorpay_signature')
    subscribed.save()

    student_email = request.user.email
    subject_student = "Thank You for Your Purchase"
    message_student = f"Congratulations on your successful purchase! Your payment has been processed. \n Please find below the details to access your purchase: \n Order ID: {order_id} \n Purchased Date: {subscribed.subscribed_at}. \n\n Best regards, \n Course Academy"

    course_title = subscribed.courseId.title
    teacher_username = subscribed.courseId.created_by.username
    teacher_email = subscribed.courseId.created_by.email
    subject_teacher = "Course Purchase Notification"
    message_teacher = f'Dear {teacher_username},\n\nYour course "{course_title}" has been purchased by a user on our website. Congratulations!\n\nBest regards,\nCourse Academy'
    send_mail(subject_student, message_student, settings.DEFAULT_FROM_EMAIL, [student_email])
    send_mail(subject_teacher, message_teacher, settings.DEFAULT_FROM_EMAIL, [teacher_email])
    # send_email_task.delay(subject_student, message_student, settings.DEFAULT_FROM_EMAIL, student_email)
    # send_email_task.delay(subject_teacher, message_teacher, settings.DEFAULT_FROM_EMAIL, teacher_email)

    return render(request, "course/success.html")


@login_required
@teacher_required
def view_subscribed_student(request):
    courses = Course.objects.filter(created_by=request.user.id)
    if request.method == "GET" and request.GET.get("course"):
        course_id = request.GET.get("course")
        subscribed_students = SubscribedCourse.objects.filter(courseId__created_by__id = request.user.id, courseId_id =  course_id, is_paid = True)
        print(courses)
        return render(request, "course/view_students.html", {"subscribed_students":subscribed_students, "courses": courses, "data": True})
    return render(request, "course/view_students.html", {"courses": courses, "data":False})

@login_required
def view_content(request, course_id):
    print(course_id)
    course = Course.objects.get(pk=course_id)
    course_contents = CourseContent.objects.filter(course_id_id = course_id)
    user_rating = RatingCourse.objects.filter(course_id = course_id, user_id = request.user.id).first()
    if user_rating:
        user_rating = user_rating.userRating
    else:
        user_rating = 0
    try:
        purchased = SubscribedCourse.objects.get(courseId_id = course_id, userId_id = request.user.id, is_paid = True)
        purchased = True
    except:
        purchased = False
    if (len(course_contents) > 0  and not purchased and request.user.role == "student"):
        print('student purchasing')
        print("KEY ID: ", settings.RAZORPAYKEY)
        print("KEY SECRET: ", settings.RAZORPAYSECRET)
        client = razorpay.Client(auth = (settings.RAZORPAYKEY, settings.RAZORPAYSECRET))  
        data = {'amount': course.price * 100, 'currency': 'INR', 'payment_capture': 1}
        print("DATA: ", data)
        payment = client.order.create(data=data)
        subscribed_course_instance = SubscribedCourse(
            courseId = course,
            userId = request.user,
            razor_pay_order_id = payment['id']
        )
        subscribed_course_instance.save()
        return render(request, "course/viewContent.html", {"course_contents":course_contents, "course":course, "payment":payment, "purchased": purchased, "key":os.environ.get("RAZOR_PAY_KEY_ID")})
    elif len(course_contents) > 0 and request.user.role == "teacher":
        print("teacher viewing")
        return render(request, "course/viewContent.html", {"course_contents":course_contents, "course":course, "purchased": purchased})
    else:
        print("student purchased")
        return render(request, "course/viewContent.html", {"course_contents":course_contents, "course":course, "purchased": purchased, "user_rating":user_rating})

@login_required
@student_required
def purchasedCourse(request):
    print("user: ",request.user.id)
    subscribed_courses = SubscribedCourse.objects.filter(userId_id = request.user.id, is_paid = True)
    return render(request, "course/purchased_courses.html", {"subscribed_courses":subscribed_courses})

def reset_password(request):
    form = UserRegistrationForm()
    if request.method == "POST":
        email = request.POST["email"]
        role = request.POST["role"]
        try:
            user = User.objects.get(email=email, role=role)
            request.session["username"] = user.username
            request.session["role"] = role
        except:
            errors = {}
            user = None
        print(user)
        if user is not None:
            generate_otp(user)
            url = reverse("verify_otp", args=["forgot_password"])
            return redirect(url)
        else:
            errors = "The email and role are not associated, please check your email and role"
            return render(request, "course/send_password_reset.html", {"form": form, "invalid_data": errors})
    return render(request, "course/send_password_reset.html", {"form": form})

@login_required
@student_required
def course_ratings(request, rating, course_id):
    course = Course.objects.get(pk = course_id)
    RatingCourse.objects.filter(course = course, user = request.user).delete()
    # course.rating_set.create(user=request.user, rating=rating)
    RatingCourse.objects.create(userRating = rating, user = request.user, course = course)
    print(course_id)
    print(rating)
    print(RatingCourse.objects.all())
    print(course.average_rating())
    url = reverse("view_content", args=[course_id])
    return redirect(url)

@login_required
@teacher_required
def add_quiz(request, course_id=None, quiz_id=None):

    course = get_object_or_404(Course, pk=course_id)

    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.course = course
            try:
                quiz.save()
            except Exception as e:
                print(str(e))
            return redirect('quiz_detail', quiz_id=quiz.id)  # Redirect to quiz detail page
    else:
        form = QuizForm()
    return render(request, 'course/add_quiz.html', {'form': form})

@login_required
@teacher_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    OptionFormSet = get_option_formset()
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        option_formset = OptionFormSet(request.POST)
        if question_form.is_valid() and option_formset.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()
            option_formset.instance = question
            option_formset.save()
            return redirect('quiz_detail', quiz_id=quiz.id)
    else:
        question_form = QuestionForm()
        option_formset = OptionFormSet()
    return render(request, 'course/quiz_detail.html', {'quiz': quiz, 'question_form': question_form, 'option_formset': option_formset})

def course_quizzes(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    quizzes = course.quiz_set.all()  # Retrieve all quizzes associated with the course
    return render(request, 'course/course_quizzes.html', {'course': course, 'quizzes': quizzes})

def take_quiz(request, quiz_id):
    submitted_quiz = UserResponse.objects.filter(user=request.user,quiz=quiz_id).first()
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    total_questions = questions.count()

    if submitted_quiz:
        return render(request, 'course/quiz_result.html',  {'quiz': quiz, 'score': int(submitted_quiz.score), 'total_questions': total_questions})


    if request.method == 'POST':
        correct_answers = 0

        user_response = UserResponse.objects.create(user=request.user, quiz=quiz)
        
        for question in questions:
            selected_option_id = request.POST.get(f'question_{question.id}', None)
            if selected_option_id:
                selected_option = get_object_or_404(Option, id=selected_option_id)
                if selected_option.is_correct:
                    correct_answers += 1
                response_answer = ResponseAnswer.objects.create(user_response=user_response, question=question, selected_option=selected_option)
        user_response.score = correct_answers
        user_response.save()

        return render(request, 'course/quiz_result.html', {'quiz': quiz, 'score': correct_answers})  # Redirect to a view that shows quiz results
    
    return render(request, 'course/take_quiz.html', {'quiz': quiz, 'questions': questions})