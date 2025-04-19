let db = null;
let isResponseGenerating = false;
let temporaryMod = false;
const chats = [{ id: 1, name: 'Chat 1', messages: [] }];
let currentChatId = 1;
let nextChatId = 2;

// 🆕 Helper: get user_id from localStorage or generate a new one
function getUserId() {
    let userId = localStorage.getItem("user_id");
    if (!userId) {
        userId = Math.random().toString(36).substring(2, 15);  // generate random ID
        localStorage.setItem("user_id", userId);
    }
    return userId;
}

const menuToggle = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('.sidebar');
const content = document.querySelector('.content');
const backdrop = document.querySelector('.backdrop');
const sendButton = document.querySelector('.send');
const textarea = document.querySelector('.message-box textarea');
const temporaryButton = document.querySelector('.temporary');

function initDatabase() {
    return new Promise((resolve, reject) => {
        if (!window.indexedDB) {
            console.error("Your browser doesn't support IndexedDB");
            reject("IndexedDB not supported");
            return;
        }

        const request = indexedDB.open("ChatDatabase", 1);

        request.onerror = (event) => {
            console.error("Database error: ", event.target.error);
            reject("Error opening database");
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            if (!db.objectStoreNames.contains("chats")) {
                const chatsStore = db.createObjectStore("chats", { keyPath: "id" });
                chatsStore.createIndex("name", "name", { unique: false });
            }

            if (!db.objectStoreNames.contains("messages")) {
                const messagesStore = db.createObjectStore("messages", { keyPath: "id", autoIncrement: true });
                messagesStore.createIndex("chatId", "chatId", { unique: false });
            }
        };

        request.onsuccess = (event) => {
            db = event.target.result;
            loadChatsFromDatabase().then(resolve);
        };
    });
}

function saveChat(chat) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(["chats"], "readwrite");
        const store = transaction.objectStore("chats");
        const request = store.put(chat);

        request.onsuccess = resolve;
        request.onerror = (event) => reject(event.target.error);
    });
}

function saveMessage(message) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(["messages"], "readwrite");
        const store = transaction.objectStore("messages");
        const request = store.add(message);

        request.onsuccess = resolve;
        request.onerror = (event) => reject(event.target.error);
    });
}

function loadChatsFromDatabase() {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(["chats"], "readonly");
        const store = transaction.objectStore("chats");
        const request = store.getAll();

        request.onsuccess = (event) => {
            const loadedChats = event.target.result;

            if (loadedChats.length > 0) {
                chats.length = 0;
                loadedChats.forEach(chat => {
                    chats.push(chat);
                    if (chat.id >= nextChatId) {
                        nextChatId = chat.id + 1;
                    }
                });

                loadMessagesForChat(currentChatId).then(() => {
                    renderChatList();
                    renderMessages();
                    resolve();
                });
            } else {
                const defaultChat = { id: 1, name: 'Chat 1', messages: [] };
                saveChat(defaultChat).then(() => {
                    chats.push(defaultChat);
                    resolve();
                });
            }
        };

        request.onerror = (event) => reject(event.target.error);
    });
}

function loadMessagesForChat(chatId) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(["messages"], "readonly");
        const store = transaction.objectStore("messages");
        const index = store.index("chatId");
        const request = index.getAll(IDBKeyRange.only(chatId));

        request.onsuccess = (event) => {
            const messages = event.target.result;
            const currentChat = chats.find(chat => chat.id === chatId);

            if (currentChat) {
                currentChat.messages = messages.map(msg => ({
                    text: msg.text,
                    type: msg.type
                }));
                resolve();
            } else {
                reject(`Chat with ID ${chatId} not found`);
            }
        };

        request.onerror = (event) => reject(event.target.error);
    });
}

function deleteMessagesForChat(chatId) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(["messages"], "readwrite");
        const store = transaction.objectStore("messages");
        const index = store.index("chatId");
        const request = index.openKeyCursor(IDBKeyRange.only(chatId));

        request.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                store.delete(cursor.primaryKey);
                cursor.continue();
            } else {
                resolve();
            }
        };

        request.onerror = (event) => reject(event.target.error);
    });
}

function renderChatList() {
    const chatList = document.querySelector('.chat-list');
    chatList.innerHTML = '';

    chats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        chatItem.innerHTML = `
            <div class="chat-name">${chat.name}</div>
            <div class="last-message">${chat.messages[chat.messages.length - 1]?.text || 'No messages yet'}</div>
        `;

        chatItem.addEventListener('click', () => switchChat(chat.id));
        chatList.appendChild(chatItem);
    });
}

function switchChat(chatId) {
    currentChatId = chatId;
    loadMessagesForChat(chatId).then(() => {
        renderChatList();
        renderMessages();
    });
}

function renderMessages() {
    const chatContainer = document.querySelector('.chat-container');
    chatContainer.innerHTML = '';

    const currentChat = chats.find(chat => chat.id === currentChatId);
    currentChat.messages.forEach(msg => {
        addMessage(msg.text, msg.type, false);
    });
}

function addMessage(text, type, save = true) {
    const chatContainer = document.querySelector('.chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = text;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (save && (type === 'sent' || type === 'received')) {
        const currentChat = chats.find(chat => chat.id === currentChatId);
        const newMessage = { text, type };
        currentChat.messages.push(newMessage);

        if (!temporaryMod) {
            saveMessage({
                chatId: currentChatId,
                text,
                type,
                timestamp: new Date().getTime()
            });
        }

        renderChatList();
    }

    if (temporaryMod) {
        const messages = document.querySelectorAll('.message');
        const lastMessage = messages[messages.length - 1];
        lastMessage.classList.add('temp-message');
    }
}

function sendMessage() {
    const message = textarea.value.trim();

    if (message && !isResponseGenerating) {
        addMessage(message, 'sent');
        textarea.value = '';
        textarea.style.height = '24px';
        textarea.style.overflowY = 'hidden';
        adjustChatContainerHeight();

        isResponseGenerating = true;
        textarea.disabled = true;
        sendButton.classList.add('disabled');

        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.appendChild(typingIndicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message, user_id: getUserId() })  // 🆕 sending user_id now
        })
        .then(response => response.json())
        .then(data => {
            chatContainer.removeChild(typingIndicator);

            const responseText = data.response || "Sorry, no response.";

            addMessage(responseText, 'received');

            // Append sources if any
            if (data.sources && data.sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.style.marginTop = '6px';
                sourcesDiv.style.fontSize = '13px';

                sourcesDiv.innerHTML = `<strong>Sources:</strong><br>` + data.sources.map(link =>
                    `<a href="${link}" target="_blank" style="color: #007bff; text-decoration: none;">${link}</a><br>`
                ).join('');

                const lastMessage = document.querySelector('.message.received:last-of-type');
                lastMessage.appendChild(sourcesDiv);
            }

            isResponseGenerating = false;
            textarea.disabled = false;
            sendButton.classList.remove('disabled');
            textarea.focus();
        })
        .catch(error => {
            console.error("Error fetching from backend:", error);
            chatContainer.removeChild(typingIndicator);

            addMessage("⚠️ Error getting response from server.", "received");
            isResponseGenerating = false;
            textarea.disabled = false;
            sendButton.classList.remove("disabled");
        });
    }
}

function adjustChatContainerHeight() {
    const messageBox = document.querySelector('.message-box');
    const chatContainer = document.querySelector('.chat-container');
    const topBarHeight = 60;
    const messageBoxHeight = messageBox.offsetHeight;
    const padding = 40;

    chatContainer.style.height = `calc(100vh - ${messageBoxHeight + topBarHeight + padding}px)`;
}

// Event listeners
menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('active');
    backdrop.classList.toggle('active');
});

backdrop.addEventListener('click', () => {
    sidebar.classList.remove('active');
    backdrop.classList.remove('active');
});

document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !menuToggle.contains(e.target) && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        content.classList.remove('sidebar-active');
    }
});

textarea.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

textarea.addEventListener('input', function() {
    this.style.height = 'auto';
    const minHeight = 24;
    const maxHeight = 100;
    const newHeight = Math.min(Math.max(this.scrollHeight, minHeight), maxHeight);
    this.style.height = newHeight + 'px';
    this.style.overflowY = this.scrollHeight > maxHeight ? 'auto' : 'hidden';
    adjustChatContainerHeight();
});

document.addEventListener('DOMContentLoaded', () => {
    initDatabase()
        .then(() => {
            renderChatList();
            renderMessages();
            adjustChatContainerHeight();
        })
        .catch(error => {
            console.error("Failed to initialize database:", error);
        });
});
