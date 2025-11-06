# Create your views here.
"""
Authentication views for user management
Time Complexity noted for each view
Space Complexity: O(1) for all views
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import login

from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    PasswordChangeSerializer
)


class UserRegistrationView(APIView):
    """
    User registration endpoint
    Time Complexity: O(1) - single database insert
    """
    
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def post(self, request):
        """
        Register a new user
        POST /api/auth/register/
        """
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    User login endpoint
    Time Complexity: O(1) - single database lookup with index
    """
    
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        """
        Login user and return tokens
        POST /api/auth/login/
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update user login status
            login(request, user)
            user.is_online = True
            user.save(update_fields=['is_online', 'last_login'])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """
    User logout endpoint
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Logout user and blacklist refresh token
        POST /api/auth/logout/
        """
        try:
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Update user online status
            user = request.user
            user.is_online = False
            user.save(update_fields=['is_online'])
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    User profile endpoint
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get current user profile
        GET /api/auth/profile/
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        """
        Update current user profile
        PUT /api/auth/profile/
        """
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckSessionView(APIView):
    """
    Check if user session is valid
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Verify user session
        GET /api/auth/check-session/
        """
        return Response({
            'valid': True,
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view
    Time Complexity: O(1)
    """
    
    def post(self, request, *args, **kwargs):
        """
        Refresh access token
        POST /api/auth/token/refresh/
        """
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            return Response({
                'message': 'Token refreshed successfully',
                'tokens': response.data
            }, status=status.HTTP_200_OK)
        
        return response


class PasswordResetRequestView(APIView):
    """
    Password reset request endpoint
    Time Complexity: O(1)
    """
    
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        """
        Request password reset
        POST /api/auth/password-reset/
        """
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            reset_token = serializer.save()
            
            # In production, send email with reset link
            # For now, return token in response (for testing only)
            return Response({
                'message': 'Password reset token generated',
                'token': reset_token.token,  # Remove this in production
                'note': 'In production, this would be sent via email'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    Password reset confirmation endpoint
    Time Complexity: O(1)
    """
    
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        """
        Confirm password reset with token
        POST /api/auth/password-reset-confirm/
        """
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'message': 'Password reset successful'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    Password change endpoint (for logged in users)
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    
    def post(self, request):
        """
        Change password for authenticated user
        POST /api/auth/password-change/
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(APIView):
    """
    List all users (for chat user selection)
    Time Complexity: O(n) where n is number of users
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get list of all users
        GET /api/auth/users/
        """
        users = User.objects.exclude(id=request.user.id)
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'users': serializer.data
        }, status=status.HTTP_200_OK)