# Create your views here.
"""
Chat views for conversation and message management
Time Complexity noted for each view
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Max, Prefetch
from django.utils import timezone

from .models import Conversation, ConversationParticipant, Message, MessageReadStatus
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer
)


class ConversationListView(APIView):
    """
    List all conversations for current user
    Time Complexity: O(n) where n is number of conversations
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get all conversations for current user
        GET /api/chat/conversations/
        """
        # Optimize query with prefetch_related
        conversations = Conversation.objects.filter(
            participants__user=request.user
        ).prefetch_related(
            'participants__user',
            'messages'
        ).distinct().order_by('-updated_at')
        
        serializer = ConversationSerializer(
            conversations, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'conversations': serializer.data
        }, status=status.HTTP_200_OK)


class ConversationCreateView(APIView):
    """
    Create new conversation
    Time Complexity: O(n) where n is number of participants
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationCreateSerializer
    
    def post(self, request):
        """
        Create a new conversation
        POST /api/chat/conversations/create/
        """
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            conversation = serializer.save()
            
            return Response({
                'message': 'Conversation created successfully',
                'conversation': ConversationSerializer(
                    conversation, 
                    context={'request': request}
                ).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversationDetailView(APIView):
    """
    Get conversation details
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, conversation_id):
        """
        Get conversation details
        GET /api/chat/conversations/<id>/
        """
        try:
            conversation = Conversation.objects.prefetch_related(
                'participants__user'
            ).get(
                id=conversation_id,
                participants__user=request.user
            )
            
            serializer = ConversationSerializer(
                conversation,
                context={'request': request}
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MessageListView(APIView):
    """
    List messages in a conversation
    Time Complexity: O(n) where n is number of messages
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, conversation_id):
        """
        Get all messages in a conversation
        GET /api/chat/conversations/<id>/messages/
        Query params:
        - limit: number of messages to return (default: 50)
        - offset: pagination offset (default: 0)
        - before: get messages before this message_id
        """
        try:
            # Verify user is participant
            conversation = Conversation.objects.get(
                id=conversation_id,
                participants__user=request.user
            )
            
            # Get query parameters
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            before_id = request.query_params.get('before')
            
            # Build query
            messages = conversation.messages.select_related('sender')
            
            if before_id:
                messages = messages.filter(id__lt=before_id)
            
            messages = messages.order_by('-created_at')[offset:offset+limit]
            
            serializer = MessageSerializer(
                messages,
                many=True,
                context={'request': request}
            )
            
            return Response({
                'messages': serializer.data,
                'conversation_id': conversation_id
            }, status=status.HTTP_200_OK)
        
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found or you are not a participant'
            }, status=status.HTTP_404_NOT_FOUND)


class MessageCreateView(APIView):
    """
    Create a new message
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = MessageCreateSerializer
    
    def post(self, request):
        """
        Create a new message
        POST /api/chat/messages/create/
        """
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            message = serializer.save()
            
            return Response({
                'message': 'Message sent successfully',
                'data': MessageSerializer(message, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageMarkReadView(APIView):
    """
    Mark messages as read
    Time Complexity: O(n) where n is number of messages to mark
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, conversation_id):
        """
        Mark all messages in conversation as read
        POST /api/chat/conversations/<id>/mark-read/
        """
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                participants__user=request.user
            )
            
            # Get participant
            participant = conversation.participants.get(user=request.user)
            
            # Update last_read_at
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])
            
            # Mark all unread messages as read
            unread_messages = conversation.messages.exclude(
                sender=request.user
            ).exclude(
                read_status__user=request.user
            )
            
            for message in unread_messages:
                MessageReadStatus.objects.get_or_create(
                    message=message,
                    user=request.user
                )
            
            return Response({
                'message': 'Messages marked as read'
            }, status=status.HTTP_200_OK)
        
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ConversationDeleteView(APIView):
    """
    Delete/Leave a conversation
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, conversation_id):
        """
        Leave or delete a conversation
        DELETE /api/chat/conversations/<id>/
        """
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                participants__user=request.user
            )
            
            # Remove user from participants
            participant = conversation.participants.get(user=request.user)
            participant.delete()
            
            # Delete conversation if no participants left
            if conversation.participants.count() == 0:
                conversation.delete()
                return Response({
                    'message': 'Conversation deleted'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'message': 'Left conversation'
            }, status=status.HTTP_200_OK)
        
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MessageUpdateView(APIView):
    """
    Update a message
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def put(self, request, message_id):
        """
        Update a message
        PUT /api/chat/messages/<id>/
        """
        try:
            message = Message.objects.get(
                id=message_id,
                sender=request.user
            )
            
            content = request.data.get('content')
            if not content:
                return Response({
                    'error': 'Content is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            message.content = content
            message.mark_as_edited()
            
            return Response({
                'message': 'Message updated successfully',
                'data': MessageSerializer(message, context={'request': request}).data
            }, status=status.HTTP_200_OK)
        
        except Message.DoesNotExist:
            return Response({
                'error': 'Message not found or you are not the sender'
            }, status=status.HTTP_404_NOT_FOUND)


class MessageDeleteView(APIView):
    """
    Delete a message
    Time Complexity: O(1)
    """
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, message_id):
        """
        Delete a message
        DELETE /api/chat/messages/<id>/
        """
        try:
            message = Message.objects.get(
                id=message_id,
                sender=request.user
            )
            
            message.delete()
            
            return Response({
                'message': 'Message deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Message.DoesNotExist:
            return Response({
                'error': 'Message not found or you are not the sender'
            }, status=status.HTTP_404_NOT_FOUND)