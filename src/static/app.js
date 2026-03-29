/**
 * agent-webbridge — Chat Client
 * 
 * Handles WebSocket connection to the agent and UI interactions.
 * Supports streaming responses with incremental rendering.
 */

class ChatClient {
    constructor() {
        // DOM Elements
        this.elements = {
            status: document.getElementById('connection-status'),
            statusText: document.querySelector('.status-text'),
            agentName: document.getElementById('agent-name'),
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
        };

        // State
        this.ws = null;
        this.connected = false;
        this.apiKey = '';
        this.wsUrl = '';
        this.agentName = 'Agent';
        this.pendingFiles = [];
        this.messageQueue = [];
        this.sessionId = null;
        
        // Streaming state - tracks current streaming message per sender
        this._streamingMessages = {}; // sender_id -> { element, content }

        // Initialize
        this.bindEvents();
        this.loadSettings();
        this.autoConnect();
    }

    bindEvents() {
        // Send message
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.elements.messageInput.addEventListener('input', () => this.updateSendButton());

        // File attachment
        this.elements.attachBtn.addEventListener('click', () => this.elements.fileInput.click());
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Settings
        this.elements.settingsBtn.addEventListener('click', () => this.openSettings());
        this.elements.closeSettings.addEventListener('click', () => this.closeSettings());
        this.elements.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) this.closeSettings();
        });
        this.elements.connectBtn.addEventListener('click', () => this.handleConnect());
    }

    loadSettings() {
        this.apiKey = localStorage.getItem('api_key') || '';
        this.wsUrl = localStorage.getItem('ws_url') || '/ws';
        this.agentName = localStorage.getItem('agent_name') || 'Agent';

        this.elements.apiKeyInput.value = this.apiKey;
        this.elements.wsUrlInput.value = this.wsUrl;
        this.elements.agentNameInput.value = this.agentName;
        this.elements.agentName.textContent = this.agentName;
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
                console.log('WebSocket connected');
                // Send auth
                this.ws.send(JSON.stringify({
                    type: 'auth',
                    api_key: this.apiKey
                }));
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed', event.code, event.reason);
                this.connected = false;
                this.setStatus('disconnected', 'Disconnected');
                this.updateSendButton();

                // Auto-reconnect after 3 seconds
                if (this.apiKey) {
                    setTimeout(() => this.connect(), 3000);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.setStatus('disconnected', 'Connection error');
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            this.setStatus('disconnected', 'Failed to connect');
        }
    }

    handleMessage(data) {
        try {
            const msg = JSON.parse(data);
            console.log('Received:', msg.type, msg);

            switch (msg.type) {
                case 'auth_success':
                    this.connected = true;
                    this.sessionId = msg.session_id;
                    this.setStatus('connected', 'Connected');
                    this.updateSendButton();
                    this.elements.welcome.classList.add('hidden');
                    break;

                case 'stream_start':
                    // Streaming begins - create placeholder message
                    this._startStreamingMessage(msg.chat_id || 'agent');
                    break;

                case 'chunk':
                    // Append chunk to streaming message
                    this._appendToStreamingMessage(msg.chat_id || 'agent', msg.content);
                    break;

                case 'message':
                    // Final complete message (or non-streaming message)
                    // If we were streaming, finalize the message
                    if (this._streamingMessages[msg.chat_id || 'agent']) {
                        this._finalizeStreamingMessage(msg.chat_id || 'agent', msg.content, msg.media);
                    } else {
                        // Non-streaming message
                        this.addMessage(msg.content, 'agent', msg.media);
                    }
                    break;

                case 'error':
                    console.error('Server error:', msg.error);
                    // End any active streaming
                    this._finalizeStreamingMessage('agent', `Error: ${msg.error}`, []);
                    break;

                case 'pong':
                    // Keepalive response, ignore
                    break;

                default:
                    console.log('Unknown message type:', msg.type);
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }
    
    // ========== Streaming Methods ==========
    
    _startStreamingMessage(chatId) {
        // Remove any existing streaming message for this chat
        if (this._streamingMessages[chatId]) {
            this._finalizeStreamingMessage(chatId, '', []);
        }
        
        // Create placeholder message element
        const messageEl = document.createElement('div');
        messageEl.className = 'message agent streaming';
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-avatar">🤖</span>
                <span>${this.agentName}</span>
                <span class="streaming-indicator">●</span>
            </div>
            <div class="message-content streaming-content"></div>
            <div class="message-time">${time}</div>
        `;
        
        this.elements.messages.appendChild(messageEl);
        this.scrollToBottom();
        
        this._streamingMessages[chatId] = {
            element: messageEl,
            content: ''
        };
    }
    
    _appendToStreamingMessage(chatId, chunk) {
        const stream = this._streamingMessages[chatId];
        if (!stream) return;
        
        stream.content += chunk;
        
        // Update the content element
        const contentEl = stream.element.querySelector('.streaming-content');
        if (contentEl) {
            contentEl.innerHTML = this.formatContent(stream.content) + '<span class="cursor">▊</span>';
        }
        
        this.scrollToBottom();
    }
    
    _finalizeStreamingMessage(chatId, finalContent, media = []) {
        const stream = this._streamingMessages[chatId];
        if (!stream) {
            // No streaming in progress, just add the message normally
            if (finalContent) {
                this.addMessage(finalContent, 'agent', media);
            }
            return;
        }
        
        // Use final content if provided, otherwise use accumulated content
        const content = finalContent || stream.content;
        
        // Remove streaming class and cursor
        const contentEl = stream.element.querySelector('.streaming-content');
        if (contentEl) {
            contentEl.classList.remove('streaming-content');
            contentEl.innerHTML = this.formatContent(content);
        }
        
        // Remove streaming indicator
        const indicator = stream.element.querySelector('.streaming-indicator');
        if (indicator) indicator.remove();
        
        stream.element.classList.remove('streaming');
        
        // Add media if present
        if (media && media.length > 0) {
            const timeEl = stream.element.querySelector('.message-time');
            if (timeEl) {
                const mediaHtml = media.map(m => {
                    if (m.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
                        return `<img src="${m}" alt="attachment">`;
                    }
                    return `<a href="${m}" target="_blank">📎 ${m.split('/').pop()}</a>`;
                }).join('');
                timeEl.insertAdjacentHTML('beforebegin', mediaHtml);
            }
        }
        
        // Clean up
        delete this._streamingMessages[chatId];
        this.scrollToBottom();
    }

    async sendMessage() {
        const content = this.elements.messageInput.value.trim();
        
        if (!content && this.pendingFiles.length === 0) return;
        if (!this.connected) return;

        // Handle file uploads first if any
        let media = [];
        if (this.pendingFiles.length > 0) {
            media = await this.uploadFiles();
        }

        // Build message
        const message = {
            type: 'message',
            content: content,
            sender_id: this.apiKey, // Use full API key as sender ID
            media: media,
            metadata: {
                timestamp: Date.now()
            }
        };

        // Add to chat
        this.addMessage(content, 'user', media);

        // Clear input
        this.elements.messageInput.value = '';
        this.clearFilePreview();
        this.updateSendButton();

        // Send via WebSocket
        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(message));
        }
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
                fileItem.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:var(--text-muted);">${file.name}</div>`;
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
        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Process content for code blocks
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

    formatContent(content) {
        // Escape HTML
        let formatted = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Code blocks
        formatted = formatted.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
        });

        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    scrollToBottom() {
        this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    }

    showTyping() {
        const typing = document.createElement('div');
        typing.className = 'message agent typing';
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

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.chatClient = new ChatClient();
});
