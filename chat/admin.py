# Register your models here.
"""
Chat admin configuration
"""

from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message, MessageReadStatus, TypingIndicator


class ConversationParticipantInline(admin.TabularInline):
    """
    Inline for conversation participants
    """
    model = ConversationParticipant
    extra = 1
    readonly_fields = ['joined_at']


class MessageInline(admin.TabularInline):
    """
    Inline for messages
    """
    model = Message
    extra = 0
    readonly_fields = ['created_at', 'edited_at']
    fields = ['sender', 'content', 'type', 'is_edited', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Conversation admin interface
    """
    list_display = ['id', 'type', 'name', 'created_at', 'updated_at', 'participant_count']
    list_filter = ['type', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    inlines = [ConversationParticipantInline, MessageInline]
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    """
    Conversation Participant admin interface
    """
    list_display = ['id', 'conversation', 'user', 'is_admin', 'joined_at', 'unread_count']
    list_filter = ['is_admin', 'joined_at']
    search_fields = ['user__username', 'user__email', 'conversation__name']
    readonly_fields = ['joined_at']
    ordering = ['-joined_at']
    
    def unread_count(self, obj):
        return obj.get_unread_count()
    unread_count.short_description = 'Unread Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Message admin interface
    """
    list_display = ['id', 'conversation', 'sender', 'content_preview', 'type', 'is_edited', 'created_at']
    list_filter = ['type', 'is_edited', 'created_at']
    search_fields = ['content', 'sender__username', 'sender__email']
    readonly_fields = ['created_at', 'edited_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    """
    Message Read Status admin interface
    """
    list_display = ['id', 'message', 'user', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['read_at']
    ordering = ['-read_at']


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    """
    Typing Indicator admin interface
    """
    list_display = ['id', 'conversation', 'user', 'started_at', 'is_active']
    list_filter = ['started_at']
    search_fields = ['user__username', 'conversation__name']
    readonly_fields = ['started_at']
    ordering = ['-started_at']
    
    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = 'Active'