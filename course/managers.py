from django.contrib.auth.models import BaseUserManager
from django.db import IntegrityError


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("role") != 'admin':
            raise ValueError("Superuser must have role as admin.")

        while True:
            if username is None:
                username = input("Enter username: ")

            # Check if the username already exists
            if self.model.objects.filter(username=username).exists():
                print("Username already exists. Please choose a different username.")
                username = None
                continue
            else:
                break

        return self.create_user(email, username, password, **extra_fields)
