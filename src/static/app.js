/**
 * agent-webbridge — Chat Client with Streaming Support
 */

class ChatClient {
    constructor() {
        this.elements = {
            status: document.getElementById('connection-status'),
            statusText: document.querySelector('.status-text'),
            agentName: document.getElementById('agent-name'),
            agentNameSidebar: document.getElementById('agent-name-sidebar'),
            chatContainer: document.getElementById('chat-container'),
            messages: document.getElementById('messages'),
            welcome: document.getElementById('welcome-message'),
            messageInput: document.getElementById('message-input'),
            sendBtn: document.getElementById('send-btn'),
            attachBtn: document.getElementById('attach-btn'),
            fileInput: document.getElementById('file-input'),
            filePreview: document.getElementById('file-preview'),
            settingsBtn: document.getElementById('settings-btn'),
            settingsModal: document.getElementById('settings-modal'),
            closeSettings: document.getElementById('close-settings'),
            connectBtn: document.getElementById('connect-btn'),
            apiKeyInput: document.getElementById('api-key-input'),
            agentNameInput: document.getElementById('agent-name-input'),
            wsUrlInput: document.getElementById('ws-url-input'),
            sidebar: document.getElementById('sidebar'),
            menuBtn: document.getElementById('menu-btn'),
        };

        this.ws = null;
        this.connected = false;
        this.apiKey = '';
        this.wsUrl = '';
        this.agentName = 'Agent';
        this.pendingFiles = [];
        this.sessionId = null;
        this.chats = [{ id: 'default', messages: [], name: 'New Chat' }];
        this.currentChatId = 'default';

        this.bindEvents();
        this.loadSettings();
        this.autoConnect();
    }

    bindEvents() {
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.elements.messageInput.addEventListener('input', () => this.updateSendButton());

        this.elements.attachBtn.addEventListener('click', () => this.elements.fileInput.click());
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        this.elements.settingsBtn.addEventListener('click', () => this.openSettings());
        this.elements.closeSettings.addEventListener('click', () => this.closeSettings());
        this.elements.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) this.closeSettings();
        });
        this.elements.connectBtn.addEventListener('click', () => this.handleConnect());

        this.elements.menuBtn?.addEventListener('click', () => this.toggleSidebar());
    }

    toggleSidebar() {
        this.elements.sidebar?.classList.toggle('open');
    }

    loadSettings() {
        this.apiKey = localStorage.getItem('api_key') || '';
        this.wsUrl = localStorage.getItem('ws_url') || '/ws';
        this.agentName = localStorage.getItem('agent_name') || 'Agent';

        this.elements.apiKeyInput.value = this.apiKey;
        this.elements.wsUrlInput.value = this.wsUrl;
        this.elements.agentNameInput.value = this.agentName;
        this.elements.agentName.textContent = this.agentName;
        this.elements.agentNameSidebar.textContent = this.agentName;
    }

    saveSettings() {
        localStorage.setItem('api_key', this.apiKey);
        localStorage.setItem('ws_url', this.wsUrl);
        localStorage.setItem('agent_name', this.agentName);
    }

    openSettings() {
        this.elements.settingsModal.classList.remove('hidden');
    }

    closeSettings() {
        this.elements.settingsModal.classList.add('hidden');
    }

    handleConnect() {
        this.apiKey = this.elements.apiKeyInput.value.trim();
        this.wsUrl = this.elements.wsUrlInput.value.trim();
        this.agentName = this.elements.agentNameInput.value.trim() || 'Agent';

        this.saveSettings();
        this.elements.agentName.textContent = this.agentName;
        this.elements.agentNameSidebar.textContent = this.agentName;
        this.closeSettings();

        if (this.apiKey) {
            this.connect();
        }
    }

    autoConnect() {
        if (this.apiKey && !this.connected) {
            this.connect();
        }
    }

    updateSendButton() {
        const hasContent = this.elements.messageInput.value.trim() || this.pendingFiles.length > 0;
        this.elements.sendBtn.disabled = !hasContent || !this.connected;
    }

    setStatus(status, text) {
        this.elements.status.className = `status ${status}`;
        this.elements.statusText.textContent = text;
    }

    connect() {
        if (this.ws) {
            this.ws.close();
        }

        this.setStatus('connecting', 'Connecting...');

        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                this.ws.send(JSON.stringify({
                    type: 'auth',
                    api_key: this.apiKey
                }));
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onclose = (event) => {
                this.connected = false;
                this.setStatus('disconnected', 'Disconnected');
                this.updateSendButton();

                if (this.apiKey) {
                    setTimeout(() => this.connect(), 3000);
                }
            };

            this.ws.onerror = (error) => {
                this.setStatus('disconnected', 'Connection error');
            };

        } catch (error) {
            this.setStatus('disconnected', 'Failed to connect');
        }
    }

    handleMessage(data) {
        try {
            const msg = JSON.parse(data);

            switch (msg.type) {
                case 'auth_success':
                    this.connected = true;
                    this.sessionId = msg.session_id;
                    this.setStatus('connected', 'Connected');
                    this.updateSendButton();
                    this.elements.welcome.classList.add('hidden');
                    break;

                case 'message':
                    // Streaming: if we have partial content, append
                    if (msg.streaming) {
                        this.appendToLastMessage(msg.content);
                    } else {
                        this.addMessage(msg.content, 'agent', msg.media);
                    }
                    break;

                case 'error':
                    this.addMessage(`Error: ${msg.error}`, 'agent');
                    break;

                case 'pong':
                    break;
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }

    async sendMessage() {
        const content = this.elements.messageInput.value.trim();
        
        if (!content && this.pendingFiles.length === 0) return;
        if (!this.connected) return;

        let media = [];
        if (this.pendingFiles.length > 0) {
            media = await this.uploadFiles();
        }

        const message = {
            type: 'message',
            content: content,
            sender_id: this.apiKey.slice(0, 16),
            media: media,
            metadata: { timestamp: Date.now() }
        };

        // Add to chat immediately (optimistic UI)
        this.addMessage(content, 'user', media);

        this.elements.messageInput.value = '';
        this.clearFilePreview();
        this.updateSendButton();

        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(message));
        }

        // Show typing indicator (will be replaced when response comes)
        this.showTyping();
    }

    async uploadFiles() {
        const uploadedUrls = [];

        for (const file of this.pendingFiles) {
            try {
                const formData = new FormData();
                formData.append(file.name, file);

                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    uploadedUrls.push(...result.files);
                }
            } catch (error) {
                console.error('Upload failed:', error);
            }
        }

        return uploadedUrls;
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        this.pendingFiles = files;
        this.showFilePreview();
        this.updateSendButton();
    }

    showFilePreview() {
        this.elements.filePreview.innerHTML = '';
        this.elements.filePreview.classList.remove('hidden');

        for (let i = 0; i < this.pendingFiles.length; i++) {
            const file = this.pendingFiles[i];
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';

            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                fileItem.appendChild(img);
            } else {
                fileItem.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:10px;color:var(--text-muted);">${file.name}</div>`;
            }

            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-btn';
            removeBtn.innerHTML = '&times;';
            removeBtn.onclick = () => this.removeFile(i);
            fileItem.appendChild(removeBtn);

            this.elements.filePreview.appendChild(fileItem);
        }
    }

    removeFile(index) {
        this.pendingFiles.splice(index, 1);
        if (this.pendingFiles.length === 0) {
            this.clearFilePreview();
        } else {
            this.showFilePreview();
        }
        this.updateSendButton();
    }

    clearFilePreview() {
        this.pendingFiles = [];
        this.elements.filePreview.innerHTML = '';
        this.elements.filePreview.classList.add('hidden');
        this.elements.fileInput.value = '';
    }

    addMessage(content, sender, media = []) {
        // Remove typing indicator if exists
        this.hideTyping();

        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const processedContent = this.formatContent(content);

        let mediaHtml = '';
        if (media && media.length > 0) {
            mediaHtml = media.map(m => {
                if (m.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
                    return `<img src="${m}" alt="attachment">`;
                }
                return `<a href="${m}" target="_blank">📎 ${m.split('/').pop()}</a>`;
            }).join('');
        }

        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-avatar">${sender === 'user' ? '👤' : '🤖'}</span>
                <span>${sender === 'user' ? 'You' : this.agentName}</span>
            </div>
            <div class="message-content">${processedContent}${mediaHtml ? '<br>' + mediaHtml : ''}</div>
            <div class="message-time">${time}</div>
        `;

        this.elements.messages.appendChild(messageEl);
        this.scrollToBottom();
    }

    appendToLastMessage(content) {
        const messages = this.elements.messages.querySelectorAll('.message.agent');
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage) {
            const contentEl = lastMessage.querySelector('.message-content');
            if (contentEl) {
                contentEl.textContent += content;
                this.scrollToBottom();
            }
        }
    }

    formatContent(content) {
        let formatted = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        formatted = formatted.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
        });

        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    scrollToBottom() {
        this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    }

    showTyping() {
        if (document.getElementById('typing-indicator')) return;

        const typing = document.createElement('div');
        typing.className = 'message agent';
        typing.id = 'typing-indicator';
        typing.innerHTML = `
            <div class="message-header">
                <span class="message-avatar">🤖</span>
                <span>${this.agentName}</span>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        this.elements.messages.appendChild(typing);
        this.scrollToBottom();
    }

    hideTyping() {
        const typing = document.getElementById('typing-indicator');
        if (typing) typing.remove();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.chatClient = new ChatClient();
});
