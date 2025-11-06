# Django Realtime Chat Server

A full-featured realtime chat server built with Django Rest Framework, Django Channels, and WebSockets.

## Features

### Authentication
- ✅ User Registration
- ✅ User Login
- ✅ User Logout
- ✅ JWT Token Authentication
- ✅ Token Refresh
- ✅ Session Check
- ✅ Password Reset (with tokens)
- ✅ Password Change
- ✅ User Profile Management

### Chat Features
- ✅ One-to-One Private Chat
- ✅ Group Chat
- ✅ Realtime Messaging (WebSocket)
- ✅ Message Persistence (Database Storage)
- ✅ Message History
- ✅ Typing Indicators
- ✅ Online/Offline Status
- ✅ Read Receipts
- ✅ Unread Message Count
- ✅ Message Editing
- ✅ Message Deletion

## Installation

### Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd django_chat_server
```

2. **Create and activate virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
```

6. **Run the server**
```bash
# Development server (with WebSocket support)
python manage.py runserver

# Production server
daphne -b 0.0.0.0 -p 8000 chat_server.asgi:application
```

7. **Access the application**
- Frontend: http://localhost:8000/
- Admin Panel: http://localhost:8000/admin/
- API Documentation: http://localhost:8000/api/

## API Endpoints

### Authentication
```
POST   /api/auth/register/                 - Register new user
POST   /api/auth/login/                    - Login user
POST   /api/auth/logout/                   - Logout user
GET    /api/auth/profile/                  - Get user profile
PUT    /api/auth/profile/                  - Update user profile
GET    /api/auth/check-session/            - Check session validity
POST   /api/auth/token/refresh/            - Refresh access token
POST   /api/auth/password-reset/           - Request password reset
POST   /api/auth/password-reset-confirm/   - Confirm password reset
POST   /api/auth/password-change/          - Change password
GET    /api/auth/users/                    - List all users
```

### Chat
```
GET    /api/chat/conversations/                          - List conversations
POST   /api/chat/conversations/create/                   - Create conversation
GET    /api/chat/conversations/<id>/                     - Get conversation details
DELETE /api/chat/conversations/<id>/delete/              - Delete/leave conversation
GET    /api/chat/conversations/<id>/messages/            - Get messages
POST   /api/chat/conversations/<id>/mark-read/           - Mark messages as read
POST   /api/chat/messages/create/                        - Create message
PUT    /api/chat/messages/<id>/                          - Update message
DELETE /api/chat/messages/<id>/delete/                   - Delete message
```

### WebSocket
```
ws://localhost:8000/ws/chat/<conversation_id>/  - WebSocket connection for realtime chat
```

## WebSocket Protocol

### Client -> Server Messages

**Send Message:**
```json
{
    "type": "chat_message",
    "content": "Hello, World!"
}
```

**Typing Indicator:**
```json
{
    "type": "typing",
    "is_typing": true
}
```

**Read Receipt:**
```json
{
    "type": "read_receipt",
    "message_id": 123
}
```

### Server -> Client Messages

**New Message:**
```json
{
    "type": "chat_message",
    "message": {
        "id": 123,
        "sender": {...},
        "content": "Hello, World!",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

**Typing Indicator:**
```json
{
    "type": "typing",
    "user_id": 1,
    "username": "john",
    "is_typing": true
}
```

**User Status:**
```json
{
    "type": "user_status",
    "user_id": 1,
    "username": "john",
    "status": "online"
}
```

## Project Structure

```
django_chat_server/
├── authentication/          # Authentication app
│   ├── models.py           # User, PasswordResetToken models
│   ├── serializers.py      # Auth serializers
│   ├── views.py            # Auth views
│   ├── urls.py             # Auth URLs
│   └── admin.py            # Auth admin
├── chat/                    # Chat app
│   ├── models.py           # Conversation, Message models
│   ├── serializers.py      # Chat serializers
│   ├── views.py            # Chat views
│   ├── consumers.py        # WebSocket consumers
│   ├── routing.py          # WebSocket routing
│   ├── urls.py             # Chat URLs
│   └── admin.py            # Chat admin
├── chat_server/            # Project settings
│   ├── settings.py         # Django settings
│   ├── urls.py             # Main URLs
│   └── asgi.py             # ASGI config
├── templates/              # Frontend templates
│   └── index.html          # Test frontend
├── manage.py
└── requirements.txt
```

## Database Models

### User
- Custom user model with email authentication
- Online/offline status tracking
- Profile information

### Conversation
- Supports private and group chats
- Tracks participants and messages
- Auto-updates timestamp on new messages

### Message
- Stores chat messages
- Supports text and system messages
- Edit tracking
- Read status tracking

### ConversationParticipant
- Links users to conversations
- Tracks admin status (for groups)
- Unread message count

## Time & Space Complexity

All views and models are optimized for performance:
- **Database Queries**: O(1) for lookups (indexed fields)
- **Message List**: O(n) where n is number of messages
- **User List**: O(n) where n is number of users
- **WebSocket Operations**: O(1) for sending/receiving

Database indexes are strategically placed on:
- User email and username
- Conversation type and update time
- Message conversation and creation time
- All foreign keys

## Testing

### Using the Frontend
1. Navigate to http://localhost:8000/
2. Register two users in different browser windows/tabs
3. Login with both users
4. Create a conversation
5. Send messages and test realtime features

### Using API Tools (Postman/cURL)
1. Register a user: `POST /api/auth/register/`
2. Login: `POST /api/auth/login/`
3. Use the access token for authenticated requests
4. Create conversations and send messages

### Admin Panel
Access http://localhost:8000/admin/ to:
- View all users, conversations, and messages
- Monitor system activity
- Manage user permissions

## Production Deployment

### Environment Variables
Create a `.env` file:
```
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=your-database-url
REDIS_URL=redis://localhost:6379
```

### Redis Setup (Required for Production)
```bash
# Install Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac
brew install redis

# Start Redis
redis-server
```

Update `settings.py` to use Redis for channels:
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### Run with Daphne
```bash
daphne -b 0.0.0.0 -p 8000 chat_server.asgi:application
```

## License
MIT License

## Author
Your Name

## Support
For issues and questions, please open an issue on GitHub.
