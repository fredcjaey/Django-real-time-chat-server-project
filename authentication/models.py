# Create your models here.
"""
Authentication models - Custom User model with additional fields
Time Complexity: O(1) for all model operations (database indexed)
Space Complexity: O(1) per user instance
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication
    Time Complexity: O(1) for user creation operations
    """
    
    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a regular user
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a superuser
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with email as the unique identifier
    Time Complexity: O(1) for lookups (indexed fields)
    Space Complexity: O(1) per instance
    """
    
    email = models.EmailField(unique=True, max_length=255, db_index=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_online']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """
        Return full name
        Time Complexity: O(1)
        """
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_short_name(self):
        """
        Return short name
        Time Complexity: O(1)
        """
        return self.first_name or self.username


class PasswordResetToken(models.Model):
    """
    Model to handle password reset tokens
    Time Complexity: O(1) for token lookups (indexed)
    Space Complexity: O(1) per token
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Reset token for {self.user.email}"
    
    def is_valid(self):
        """
        Check if token is still valid
        Time Complexity: O(1)
        """
        return not self.is_used and timezone.now() < self.expires_at