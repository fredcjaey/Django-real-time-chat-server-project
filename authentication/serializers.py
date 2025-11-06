"""
Authentication serializers for user operations
Time Complexity: O(1) for most operations, O(n) for validation where n is input size
Space Complexity: O(1) for serialization
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
import secrets

from .models import User, PasswordResetToken


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 
                  'full_name', 'is_online', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        """
        Time Complexity: O(1)
        """
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    Time Complexity: O(n) where n is password length for validation
    Space Complexity: O(1)
    """
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 
                  'first_name', 'last_name']
    
    def validate(self, attrs):
        """
        Validate password match
        Time Complexity: O(1)
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        """
        Create user instance
        Time Complexity: O(1)
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    Time Complexity: O(1) for authentication
    Space Complexity: O(1)
    """
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """
        Validate user credentials
        Time Complexity: O(1)
        """
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              username=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """
        Validate email exists
        Time Complexity: O(1) - database lookup with index
        """
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value
    
    def save(self):
        """
        Create password reset token
        Time Complexity: O(1)
        """
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        
        # Create reset token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        return reset_token


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation
    Time Complexity: O(n) where n is password length for validation
    Space Complexity: O(1)
    """
    
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """
        Validate token and password match
        Time Complexity: O(1)
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        try:
            token_obj = PasswordResetToken.objects.get(token=attrs['token'])
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid token."})
        
        if not token_obj.is_valid():
            raise serializers.ValidationError({"token": "Token has expired or already been used."})
        
        attrs['token_obj'] = token_obj
        return attrs
    
    def save(self):
        """
        Reset user password
        Time Complexity: O(1)
        """
        token_obj = self.validated_data['token_obj']
        password = self.validated_data['password']
        
        user = token_obj.user
        user.set_password(password)
        user.save()
        
        token_obj.is_used = True
        token_obj.save()
        
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change (logged in user)
    Time Complexity: O(n) where n is password length for validation
    Space Complexity: O(1)
    """
    
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """
        Validate old password and new password match
        Time Complexity: O(1)
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs
    
    def validate_old_password(self, value):
        """
        Validate old password is correct
        Time Complexity: O(1)
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def save(self):
        """
        Change user password
        Time Complexity: O(1)
        """
        user = self.context['request'].user
        password = self.validated_data['new_password']
        user.set_password(password)
        user.save()
        return user