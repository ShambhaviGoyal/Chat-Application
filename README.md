# Live Chat Room

A real-time chat application built with Flask, Flask-SocketIO, SQLAlchemy, and modern JavaScript.  
Features include multiple themed chat rooms, secure user authentication, private messaging, emoji reactions, typing indicators, and light/dark themes — all wrapped in a responsive UI.

---
## Demo
[Click here to view the video demo](https://i.imgur.com/YUUgBOi.mp4)
## Features

### User Authentication
- Secure signup, login, and logout with Flask-Login and bcrypt password hashing.  
- Unique username and email validation during signup.  
- Session management with protected routes for logged-in users only.

### Real-Time Chat
- Multiple themed chat rooms:  
  Open Mic, Code & Coffee, XP Zone, Study Squad, Lo-Fi Corner, Meme Stream, Wellness Wave.  
- Join and leave rooms dynamically.  
- Public messaging broadcast in real-time within rooms.  
- Private messaging to specific users.  
- Persistent chat history per room stored in memory.

### Interactive Features
- Typing indicators with context-aware messages:  
  “X is typing...”, “X and Y are typing...”, “Several people are typing...”  
- Emoji reactions to messages with toggling for each user.  
- Active users list updated in real-time.  
- Responsive UI supporting light and dark themes.

---

## Project Structure

```
main.py
instance/
    chat_users.db
static/
    chat.js
    styles-dark.css
    styles-light.css
templates/
    index.html
    login.html
    signup.html
    username_form.html
```

---

## Getting Started

### Prerequisites
- Python 3.7 or higher  
- Node.js (optional, only for advanced JS development)

### Installation

Clone the repo:
```bash
git clone https://github.com/ShambhaviGoyal/live-chat-room.git
cd live-chat-room
```
Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
Install dependencies:
```bash
pip install -r requirements.txt
```
If requirements.txt is missing, install manually:
```bash
pip install flask flask-socketio flask-sqlalchemy flask-bcrypt flask-login
```
Run the app
```bash
python main.py
```
Open your browser at:
```bash
http://localhost:8080/
```
## Usage

- Create an account by signing up or log in if you already have credentials.
- Select any chat room from the sidebar to join conversations.
- Send messages in rooms or privately by specifying a username.
- React to messages with emojis.
- See who’s typing in your chat room in real time.
- Toggle between light and dark UI themes.

---

## Customization

- **Chat Rooms:** Modify the `CHAT_ROOMS` list inside `main.py` to add, remove, or rename rooms.
- **Themes:** Customize the CSS files `static/styles-light.css` and `static/styles-dark.css` to change the UI look.
- **Database:** User data is stored in SQLite at `instance/chat_users.db`.

---

## Technologies Used

- Backend: Flask, Flask-SocketIO, Flask-Login, Flask-Bcrypt, Flask-SQLAlchemy
- Frontend: Jinja2 Templates, Vanilla JavaScript
- Database: SQLite
- Real-Time: Socket.IO WebSockets
- Security: Password hashing and session management

## License

MIT License

Built with Flask, Flask-SocketIO, SQLAlchemy, and ❤️
