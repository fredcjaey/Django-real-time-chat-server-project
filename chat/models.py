# Create your models here.
"""
Chat models for one-to-one and group conversations
Time Complexity noted for each operation
Space Complexity: O(1) per instance for all models
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class Conversation(models.Model):
    """
    Base conversation model (one-to-one or group)
    Time Complexity: O(1) for lookups (indexed)
    """
    
    CONVERSATION_TYPE_CHOICES = [
        ('private', 'Private'),
        ('group', 'Group'),
    ]
    
    type = models.CharField(max_length=10, choices=CONVERSATION_TYPE_CHOICES, default='private', db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)  # For group chats
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['type', '-updated_at']),
        ]
    
    def __str__(self):
        if self.type == 'group':
            return self.name or f"Group Chat {self.id}"
        return f"Private Chat {self.id}"
    
    def get_other_user(self, user):
        """
        Get the other participant in a private conversation
        Time Complexity: O(1)
        """
        if self.type == 'private':
            participants = self.participants.exclude(user=user)
            if participants.exists():
                return participants.first().user
        return None


class ConversationParticipant(models.Model):
    """
    Participants in a conversation
    Time Complexity: O(1) for lookups (indexed)
    """
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)  # For group chats
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'conversation_participants'
        verbose_name = 'Conversation Participant'
        verbose_name_plural = 'Conversation Participants'
        unique_together = ['conversation', 'user']
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['user', 'conversation']),
            models.Index(fields=['conversation', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"
    
    def get_unread_count(self):
        """
        Get unread message count
        Time Complexity: O(n) where n is unread messages
        """
        if self.last_read_at:
            return self.conversation.messages.filter(
                created_at__gt=self.last_read_at
            ).exclude(sender=self.user).count()
        return self.conversation.messages.exclude(sender=self.user).count()


class Message(models.Model):
    """
    Individual message in a conversation
    Time Complexity: O(1) for creation, O(1) for lookups (indexed)
    """
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text', db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"
    
    def mark_as_edited(self):
        """
        Mark message as edited
        Time Complexity: O(1)
        """
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['is_edited', 'edited_at'])


class MessageReadStatus(models.Model):
    """
    Track message read status per user
    Time Complexity: O(1) for lookups (indexed)
    """
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_status')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reads')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_read_status'
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'
        unique_together = ['message', 'user']
        ordering = ['read_at']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"


class TypingIndicator(models.Model):
    """
    Track who is typing in a conversation
    Time Complexity: O(1) for all operations
    Space Complexity: O(1) per indicator
    """
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='typing_indicators')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='typing_in')
    started_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'typing_indicators'
        verbose_name = 'Typing Indicator'
        verbose_name_plural = 'Typing Indicators'
        unique_together = ['conversation', 'user']
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['conversation', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} typing in {self.conversation}"
    
    def is_active(self):
        """
        Check if typing indicator is still active (within 5 seconds)
        Time Complexity: O(1)
        """
        return (timezone.now() - self.started_at).seconds < 5