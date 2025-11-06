"""
Chat serializers for conversations and messages
Time Complexity noted for each serializer
"""

from rest_framework import serializers
from django.db.models import Q, Max
from authentication.serializers import UserSerializer
from .models import Conversation, ConversationParticipant, Message, MessageReadStatus


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model
    Time Complexity: O(1)
    """
    
    sender = UserSerializer(read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'type', 'content', 
                  'created_at', 'edited_at', 'is_edited', 'is_read']
        read_only_fields = ['id', 'created_at', 'edited_at', 'is_edited']
    
    def get_is_read(self, obj):
        """
        Check if message is read by current user
        Time Complexity: O(1) - single database lookup
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MessageReadStatus.objects.filter(
                message=obj, 
                user=request.user
            ).exists()
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating messages
    Time Complexity: O(1)
    """
    
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'type']
    
    def validate_conversation(self, value):
        """
        Validate user is participant in conversation
        Time Complexity: O(1) - single database lookup
        """
        user = self.context['request'].user
        if not ConversationParticipant.objects.filter(
            conversation=value, 
            user=user
        ).exists():
            raise serializers.ValidationError("You are not a participant in this conversation.")
        return value
    
    def create(self, validated_data):
        """
        Create message with sender
        Time Complexity: O(1)
        """
        validated_data['sender'] = self.context['request'].user
        message = Message.objects.create(**validated_data)
        
        # Update conversation timestamp
        conversation = validated_data['conversation']
        conversation.save(update_fields=['updated_at'])
        
        return message


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for ConversationParticipant model
    Time Complexity: O(1)
    """
    
    user = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user', 'joined_at', 'is_admin', 'unread_count']
    
    def get_unread_count(self, obj):
        """
        Get unread message count
        Time Complexity: O(n) where n is unread messages
        """
        return obj.get_unread_count()


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model
    Time Complexity: O(n) where n is number of participants
    """
    
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'type', 'name', 'participants', 'last_message', 
                  'unread_count', 'other_user', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        """
        Get last message in conversation
        Time Complexity: O(1) - single database query with ordering
        """
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        """
        Get unread message count for current user
        Time Complexity: O(n) where n is unread messages
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.participants.filter(user=request.user).first()
            if participant:
                return participant.get_unread_count()
        return 0
    
    def get_other_user(self, obj):
        """
        Get other user in private conversation
        Time Complexity: O(1)
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.type == 'private':
            other_user = obj.get_other_user(request.user)
            if other_user:
                return UserSerializer(other_user).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating conversations
    Time Complexity: O(n) where n is number of participants
    """
    
    type = serializers.ChoiceField(choices=['private', 'group'])
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    
    def validate(self, attrs):
        """
        Validate conversation creation
        Time Complexity: O(n) where n is number of participants
        """
        from authentication.models import User
        
        conv_type = attrs.get('type')
        participant_ids = attrs.get('participant_ids', [])
        
        # Validate private chat has exactly one other user
        if conv_type == 'private' and len(participant_ids) != 1:
            raise serializers.ValidationError({
                'participant_ids': 'Private conversation must have exactly one other participant.'
            })
        
        # Validate group chat has name and at least 2 participants
        if conv_type == 'group':
            if len(participant_ids) < 1:
                raise serializers.ValidationError({
                    'participant_ids': 'Group conversation must have at least one other participant.'
                })
            if not attrs.get('name'):
                raise serializers.ValidationError({
                    'name': 'Group conversation must have a name.'
                })
        
        # Validate all participants exist
        existing_users = User.objects.filter(id__in=participant_ids).count()
        if existing_users != len(participant_ids):
            raise serializers.ValidationError({
                'participant_ids': 'One or more participant IDs are invalid.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create conversation with participants
        Time Complexity: O(n) where n is number of participants
        """
        from authentication.models import User
        
        current_user = self.context['request'].user
        conv_type = validated_data['type']
        participant_ids = validated_data['participant_ids']
        
        # Check if private conversation already exists
        if conv_type == 'private':
            other_user_id = participant_ids[0]
            existing_conv = Conversation.objects.filter(
                type='private',
                participants__user=current_user
            ).filter(
                participants__user_id=other_user_id
            ).distinct().first()
            
            if existing_conv:
                return existing_conv
        
        # Create new conversation
        conversation = Conversation.objects.create(
            type=conv_type,
            name=validated_data.get('name', '')
        )
        
        # Add current user as participant
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=current_user,
            is_admin=(conv_type == 'group')
        )
        
        # Add other participants
        participants = User.objects.filter(id__in=participant_ids)
        for participant in participants:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=participant,
                is_admin=False
            )
        
        return conversation