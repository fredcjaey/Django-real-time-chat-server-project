"""
Chat URL patterns
"""

from django.urls import path
from .views import (
    ConversationListView, ConversationCreateView, ConversationDetailView,
    ConversationDeleteView, MessageListView, MessageCreateView,
    MessageMarkReadView, MessageUpdateView, MessageDeleteView
)

app_name = 'chat'

urlpatterns = [
    # Conversation endpoints
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/delete/', ConversationDeleteView.as_view(), name='conversation-delete'),
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<int:conversation_id>/mark-read/', MessageMarkReadView.as_view(), name='message-mark-read'),
    
    # Message endpoints
    path('messages/create/', MessageCreateView.as_view(), name='message-create'),
    path('messages/<int:message_id>/', MessageUpdateView.as_view(), name='message-update'),
    path('messages/<int:message_id>/delete/', MessageDeleteView.as_view(), name='message-delete'),
]