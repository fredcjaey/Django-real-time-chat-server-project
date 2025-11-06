"""
WebSocket consumers for real-time chat
Time Complexity noted for each operation
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import Conversation, Message, ConversationParticipant, TypingIndicator
from .serializers import MessageSerializer
from authentication.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat
    Handles: message sending, typing indicators, online status
    """
    
    async def connect(self):
        """
        Handle WebSocket connection
        Time Complexity: O(1)
        """
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Verify user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify user is participant in conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user online status
        await self.update_online_status(True)
        
        # Notify others user joined
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        Time Complexity: O(1)
        """
        # Update user online status
        await self.update_online_status(False)
        
        # Remove typing indicator
        await self.remove_typing_indicator()
        
        # Notify others user left
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'offline'
            }
        )
        
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        Time Complexity: O(1) for most operations
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            
            elif message_type == 'typing':
                await self.handle_typing(data)
            
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown message type'
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def handle_chat_message(self, data):
        """
        Handle chat message
        Time Complexity: O(1)
        """
        content = data.get('content', '').strip()
        
        if not content:
            return
        
        # Save message to database
        message = await self.save_message(content)
        
        if message:
            # Serialize message
            message_data = await self.serialize_message(message)
            
            # Send message to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message_handler',
                    'message': message_data
                }
            )
    
    async def handle_typing(self, data):
        """
        Handle typing indicator
        Time Complexity: O(1)
        """
        is_typing = data.get('is_typing', False)
        
        if is_typing:
            await self.add_typing_indicator()
        else:
            await self.remove_typing_indicator()
        
        # Broadcast typing status
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator_handler',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """
        Handle read receipt
        Time Complexity: O(1)
        """
        message_id = data.get('message_id')
        
        if message_id:
            await self.mark_message_read(message_id)
    
    async def chat_message_handler(self, event):
        """
        Handle chat message broadcast
        Time Complexity: O(1)
        """
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator_handler(self, event):
        """
        Handle typing indicator broadcast
        Time Complexity: O(1)
        """
        # Don't send typing indicator to the user who is typing
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_status(self, event):
        """
        Handle user status broadcast
        Time Complexity: O(1)
        """
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def check_participant(self):
        """
        Check if user is participant in conversation
        Time Complexity: O(1) - single database query
        """
        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content):
        """
        Save message to database
        Time Complexity: O(1)
        """
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                type='text'
            )
            
            # Update conversation timestamp
            conversation.save(update_fields=['updated_at'])
            
            return message
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """
        Serialize message for JSON
        Time Complexity: O(1)
        """
        serializer = MessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def update_online_status(self, is_online):
        """
        Update user online status
        Time Complexity: O(1)
        """
        User.objects.filter(id=self.user.id).update(is_online=is_online)
    
    @database_sync_to_async
    def add_typing_indicator(self):
        """
        Add typing indicator
        Time Complexity: O(1)
        """
        TypingIndicator.objects.update_or_create(
            conversation_id=self.conversation_id,
            user=self.user
        )
    
    @database_sync_to_async
    def remove_typing_indicator(self):
        """
        Remove typing indicator
        Time Complexity: O(1)
        """
        TypingIndicator.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).delete()
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """
        Mark message as read
        Time Complexity: O(1)
        """
        from .models import MessageReadStatus
        
        try:
            message = Message.objects.get(id=message_id)
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=self.user
            )
        except Message.DoesNotExist:
            pass