let socket = io();
let currentRoom = 'Open Mic';
let username = document.getElementById('username').textContent;
let roomMessages = []; // Store current room messages for indexing

// Highlight active room UI
function highlightActiveRoom(room) {
  document.querySelectorAll('.room-item').forEach((item) => {
    item.classList.remove('active-room');
    if (item.textContent.trim() === room) {
      item.classList.add('active-room');
    }
  });
}

// Join a chat room
window.joinRoom = function(newRoom) {
  if (currentRoom === newRoom) return;

  if (currentRoom) {
    socket.emit('leave', { room: currentRoom });
  }

  currentRoom = newRoom;
  document.getElementById('chat').innerHTML = '';
  roomMessages = [];
  socket.emit('join', { room: currentRoom });
  highlightActiveRoom(currentRoom);
};

// Add a message to the chat UI
function addMessage(sender, message, type, timestamp = null, index = null, reactions = {}) {
  const chat = document.getElementById('chat');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}`;

  const time = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Detect images and display inline
  const imageRegex = /(https?:\/\/.*\.(?:png|jpg|jpeg|gif))/gi;
  let htmlMessage = message.replace(imageRegex, (url) => {
    return `<br><img src="${url}" style="max-width: 200px; max-height: 200px; border-radius: 10px; margin-top: 5px;">`;
  });

  // Build reactions HTML
  let reactionsHtml = '';
  for (const [emoji, users] of Object.entries(reactions)) {
    reactionsHtml += `<span class="reaction-btn" data-index="${index}" data-emoji="${emoji}">${emoji} ${users.length}</span> `;
  }
  // Optional: Add common emojis not yet reacted on
  const defaultEmojis = ['👍', '❤️', '😂', '😮', '😢', '👏'];
  for (const emoji of defaultEmojis) {
    if (!(emoji in reactions)) {
      reactionsHtml += `<span class="reaction-btn" data-index="${index}" data-emoji="${emoji}">${emoji}</span> `;
    }
  }

  messageDiv.innerHTML = `
    <strong>${sender}</strong> <span style="font-size: 0.8em; color: gray;">[${time}]</span><br>
    ${htmlMessage}
    <div class="reactions" style="margin-top:5px; cursor:pointer;">${reactionsHtml}</div>
  `;

  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;

  // Add click listeners on reaction buttons
  messageDiv.querySelectorAll('.reaction-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = btn.getAttribute('data-index');
      const emoji = btn.getAttribute('data-emoji');
      socket.emit('reaction', { room: currentRoom, index: Number(idx), emoji: emoji });
    });
  });
}

// Send a message (public or private)
function sendMessage() {
  const input = document.getElementById('message');
  const message = input.value.trim();
  if (!message) return;

  if (message.startsWith('@')) {
    // Private message format: @username message
    const [target, ...msgParts] = message.substring(1).split(' ');
    const privateMsg = msgParts.join(' ');
    if (privateMsg) {
      socket.emit('message', {
        msg: privateMsg,
        type: 'private',
        target: target,
      });
    }
  } else {
    // Public room message
    socket.emit('message', {
      msg: message,
      room: currentRoom,
    });
  }

  input.value = '';
  input.focus();
}

// Insert private message mention on user click
function insertPrivateMessage(user) {
  document.getElementById('message').value = `@${user} `;
  document.getElementById('message').focus();
}

// Handle pressing enter in message input
function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Typing indicator handling
let typing = false;
let timeout;

function timeoutFunction() {
  typing = false;
  socket.emit('typing', { typing: false, room: currentRoom });
}

document.getElementById('message').addEventListener('input', () => {
  if (!typing) {
    typing = true;
    socket.emit('typing', { typing: true, room: currentRoom });
  }
  clearTimeout(timeout);
  timeout = setTimeout(timeoutFunction, 1200);
});

// Socket event listeners
socket.on('connect', () => {
  joinRoom(currentRoom);
  highlightActiveRoom(currentRoom);
});

socket.on('message', (data) => {
  // Add new message to local and UI
  roomMessages.push(data);
  addMessage(
    data.username,
    data.msg,
    data.username === username ? 'own' : 'other',
    data.timestamp,
    roomMessages.length - 1,
    data.reactions || {}
  );
});

socket.on('private_message', (data) => {
  addMessage(data.from, `[Private] ${data.msg}`, 'private', data.timestamp);
});

socket.on('status', (data) => {
  if (data.type === 'typing') {
    document.getElementById('typing-status').textContent = data.msg;
  } else {
    addMessage('System', data.msg, 'system', data.timestamp);
  }
});

socket.on('active_users', (data) => {
  const userList = document.getElementById('active-users');
  userList.innerHTML = data.users
    .map(
      (user) => `
        <div class="user-item" onclick="insertPrivateMessage('${user}')">
          ${user} ${user === username ? '(you)' : ''}
        </div>
      `
    )
    .join('');
});

// Load chat history when joining room
socket.on('chat_history', (data) => {
  if (data.room === currentRoom) {
    roomMessages = data.messages;
    document.getElementById('chat').innerHTML = '';
    data.messages.forEach((msg, i) => {
      addMessage(
        msg.username,
        msg.msg,
        msg.username === username ? 'own' : 'other',
        msg.timestamp,
        i,
        msg.reactions || {}
      );
    });
  }
});

// Update reactions in real time
socket.on('reaction_update', (data) => {
  if (roomMessages[data.index]) {
    roomMessages[data.index].reactions = data.reactions;
  }

  const chat = document.getElementById('chat');
  const messageDiv = chat.children[data.index];
  if (!messageDiv) return;

  const reactionContainer = messageDiv.querySelector('.reactions');
  if (reactionContainer) {
    reactionContainer.innerHTML = Object.entries(data.reactions)
      .map(([emoji, users]) => `<span class="reaction-btn" data-index="${data.index}" data-emoji="${emoji}">${emoji} ${users.length}</span>`)
      .join(' ');
    
    // Re-bind click listeners for updated reactions
    reactionContainer.querySelectorAll('.reaction-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = btn.getAttribute('data-index');
        const emoji = btn.getAttribute('data-emoji');
        socket.emit('reaction', { room: currentRoom, index: Number(idx), emoji: emoji });
      });
    });
  }
});

// Request notification permission on page load
document.addEventListener('DOMContentLoaded', () => {
  if ('Notification' in window) {
    Notification.requestPermission();
  }
});
