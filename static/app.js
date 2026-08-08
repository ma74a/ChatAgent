/**
 * ChatAgent Frontend Application Logic
 * Integrates FastAPI Backend APIs: /conversations, /history/{thread_id}, /chat/stream, /upload
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Application State ---
    let activeThreadId = null;
    let conversations = [];
    let isStreaming = false;
    let autoTtsEnabled = false;
    let recognition = null;
    let isListening = false;
    let pendingAttachedFile = null;

    // --- DOM Elements ---
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const openSidebarBtn = document.getElementById('open-sidebar-btn');
    const closeSidebarBtn = document.getElementById('close-sidebar-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const conversationsList = document.getElementById('conversations-list');
    
    const activeChatTitle = document.getElementById('active-chat-title');
    const activeChatSubtitle = document.getElementById('active-chat-subtitle');
    const modelSelect = document.getElementById('model-select');
    const ttsGlobalToggle = document.getElementById('tts-global-toggle');
    const ttsIcon = document.getElementById('tts-icon');
    const ttsLabel = document.getElementById('tts-label');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    
    const contentScrollArea = document.getElementById('content-scroll-area');
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatMessages = document.getElementById('chat-messages');
    
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const filePreviewBar = document.getElementById('file-preview-bar');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileStatusDisplay = document.getElementById('file-status-display');
    const cancelUploadBtn = document.getElementById('cancel-upload-btn');
    
    const toastContainer = document.getElementById('toast-container');
    const suggestionCards = document.querySelectorAll('.suggestion-card');

    // --- Marked & Highlight Configuration ---
    if (window.marked) {
        marked.setOptions({
            gfm: true,
            breaks: true,
            highlight: function(code, lang) {
                if (window.hljs) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                }
                return code;
            }
        });
    }

    // --- Initialize App ---
    initApp();

    async function initApp() {
        setupEventListeners();
        initSpeechRecognition();
        await fetchConversations();
        showHomeView();
    }

    // --- Event Listeners ---
    function setupEventListeners() {
        // Mobile Sidebar Controls
        openSidebarBtn?.addEventListener('click', () => {
            sidebar?.classList.add('open');
            sidebarOverlay?.classList.add('active');
        });

        closeSidebarBtn?.addEventListener('click', closeMobileSidebar);
        sidebarOverlay?.addEventListener('click', closeMobileSidebar);

        // New Chat Action
        newChatBtn?.addEventListener('click', () => {
            startNewChat();
            closeMobileSidebar();
        });

        // Reset View Action
        clearChatBtn?.addEventListener('click', () => {
            if (chatMessages) chatMessages.innerHTML = '';
            showHomeView();
        });

        // Audio TTS Toggle
        ttsGlobalToggle?.addEventListener('click', () => {
            autoTtsEnabled = !autoTtsEnabled;
            if (autoTtsEnabled) {
                ttsGlobalToggle.classList.add('active');
                ttsIcon.className = 'fa-solid fa-volume-high';
                ttsLabel.textContent = 'Audio: On';
                showToast('Auto Read-Aloud enabled', 'info');
            } else {
                ttsGlobalToggle.classList.remove('active');
                ttsIcon.className = 'fa-solid fa-volume-xmark';
                ttsLabel.textContent = 'Audio: Off';
                if (window.speechSynthesis && window.speechSynthesis.speaking) {
                    window.speechSynthesis.cancel();
                }
            }
        });

        // Prompt Submissions
        sendBtn?.addEventListener('click', () => {
            const prompt = userInput.value.trim();
            if (prompt && !isStreaming) handlePromptSubmit(prompt);
        });

        userInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const prompt = userInput.value.trim();
                if (prompt && !isStreaming) handlePromptSubmit(prompt);
            }
        });

        // Auto-resize Textarea
        userInput?.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 140) + 'px';
        });

        // File Upload Controls
        uploadBtn?.addEventListener('click', () => fileInput?.click());
        fileInput?.addEventListener('change', handleFileUpload);
        cancelUploadBtn?.addEventListener('click', clearFilePreview);

        // Voice Microphone
        micBtn?.addEventListener('click', toggleListening);

        // Welcome Suggestion Cards
        suggestionCards.forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                if (prompt) handlePromptSubmit(prompt);
            });
        });
    }

    function closeMobileSidebar() {
        sidebar?.classList.remove('open');
        sidebarOverlay?.classList.remove('active');
    }

    // --- View Switching ---
    function showHomeView() {
        activeThreadId = null;
        welcomeScreen?.classList.remove('hidden');
        chatMessages?.classList.add('hidden');
        if (activeChatTitle) activeChatTitle.textContent = 'ChatAgent';
        renderConversationsList();
    }

    function showThreadView(title = 'Chat Thread') {
        welcomeScreen?.classList.add('hidden');
        chatMessages?.classList.remove('hidden');
        if (activeChatTitle) activeChatTitle.textContent = title;
    }

    // --- API Calls: Conversations ---
    async function fetchConversations() {
        try {
            const response = await fetch('/conversations');
            if (!response.ok) throw new Error('Failed to fetch conversations');
            conversations = await response.json();
            renderConversationsList();
        } catch (err) {
            console.error('Fetch conversations error:', err);
            renderConversationsList();
        }
    }

    function renderConversationsList() {
        if (!conversationsList) return;
        conversationsList.innerHTML = '';

        // If backend has no chats yet, render the sample items from user ASCII diagram
        if (conversations.length === 0) {
            const sampleTopics = [
                { thread_id: null, title: 'Machine Learning', prompt: 'What are the key concepts of Machine Learning?' },
                { thread_id: null, title: 'LangGraph Notes', prompt: 'Explain how LangGraph works for stateful multi-agent systems' },
                { thread_id: null, title: 'Resume', prompt: 'How do I query my uploaded Resume or PDF documents?' },
                { thread_id: null, title: 'RAG', prompt: 'Explain Retrieval-Augmented Generation (RAG) with ChromaDB' }
            ];

            sampleTopics.forEach(item => {
                const div = document.createElement('div');
                div.className = 'chat-item';
                div.textContent = item.title;
                div.addEventListener('click', () => {
                    handlePromptSubmit(item.prompt);
                    closeMobileSidebar();
                });
                conversationsList.appendChild(div);
            });
            return;
        }

        conversations.forEach(item => {
            const div = document.createElement('div');
            div.className = `chat-item ${item.thread_id === activeThreadId ? 'active' : ''}`;
            div.setAttribute('data-thread-id', item.thread_id);
            div.textContent = item.title || 'New Chat';

            div.addEventListener('click', () => {
                selectConversation(item.thread_id, item.title);
                closeMobileSidebar();
            });

            conversationsList.appendChild(div);
        });
    }

    async function startNewChat() {
        try {
            const response = await fetch('/conversations', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to create new chat');
            const data = await response.json();
            activeThreadId = data.thread_id;

            await fetchConversations();
            showThreadView(data.title || 'New Chat');
            if (chatMessages) chatMessages.innerHTML = '';
        } catch (err) {
            console.error(err);
            showToast('Could not create new chat', 'error');
        }
    }

    async function selectConversation(threadId, title) {
        activeThreadId = threadId;
        showThreadView(title);
        await loadHistory(threadId);
        renderConversationsList();
    }

    async function loadHistory(threadId) {
        try {
            const response = await fetch(`/history/${threadId}`);
            if (!response.ok) throw new Error('Failed to fetch chat history');
            const msgs = await response.json();

            if (!chatMessages) return;
            chatMessages.innerHTML = '';

            if (msgs.length === 0) {
                showHomeView();
                return;
            }

            msgs.forEach(msg => {
                appendMessageBubble(msg.role, msg.content);
            });

            scrollToBottom();
        } catch (err) {
            console.error(err);
            showToast('Error loading chat history', 'error');
        }
    }

    // --- Message Submissions & Streaming ---
    async function handlePromptSubmit(promptText) {
        if (!promptText) return;

        // If no thread active, create one first via API
        if (!activeThreadId) {
            try {
                const response = await fetch('/conversations', { method: 'POST' });
                if (response.ok) {
                    const data = await response.json();
                    activeThreadId = data.thread_id;
                }
            } catch (e) {
                console.error('Thread init error:', e);
            }
        }

        const generatedTitle = promptText.length > 35 ? promptText.substring(0, 35) + '...' : promptText;
        showThreadView(generatedTitle);

        // Instantly update sidebar UI title
        const existingConv = conversations.find(c => c.thread_id === activeThreadId);
        if (existingConv) {
            existingConv.title = generatedTitle;
        } else {
            conversations.unshift({ thread_id: activeThreadId, title: generatedTitle });
        }
        renderConversationsList();

        // Append User Message bubble
        appendMessageBubble('user', promptText);
        userInput.value = '';
        userInput.style.height = 'auto';

        // Prepare Assistant Stream Bubble
        const assistantBubbleInfo = appendAssistantStreamingBubble();
        const { msgContentEl, wrapperEl } = assistantBubbleInfo;

        isStreaming = true;
        setSendButtonState(true);

        const selectedModel = modelSelect ? modelSelect.value : 'gemini-3.5-flash-lite';
        let fullContent = '';

        try {
            const response = await fetch('/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    thread_id: activeThreadId,
                    message: promptText,
                    model_name: selectedModel
                })
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;

                        try {
                            const data = JSON.parse(jsonStr);

                            if (data.type === 'chunk') {
                                fullContent += data.content;
                                msgContentEl.innerHTML = renderMarkdown(fullContent);
                                applyCodeHighlighting(msgContentEl);
                                scrollToBottom();
                            } else if (data.type === 'tool_call') {
                                appendToolStepBadge(wrapperEl, data.name, data.args);
                            } else if (data.type === 'error') {
                                fullContent += `\n\n*[Error: ${data.content}]*`;
                                msgContentEl.innerHTML = renderMarkdown(fullContent);
                            } else if (data.type === 'done') {
                                // Stream completed
                            }
                        } catch (e) {
                            console.error('SSE JSON parse error:', e, jsonStr);
                        }
                    }
                }
            }

            await fetchConversations();
            if (autoTtsEnabled && fullContent) {
                speakText(fullContent);
            }

        } catch (err) {
            console.error('Streaming error:', err);
            msgContentEl.innerHTML = renderMarkdown(fullContent + `\n\n*[Connection error: ${err.message}]*`);
            showToast('Streaming response failed', 'error');
        } finally {
            isStreaming = false;
            setSendButtonState(false);
            scrollToBottom();
        }
    }

    // --- Message Rendering Helpers ---
    function appendMessageBubble(role, content) {
        if (!chatMessages) return;

        const row = document.createElement('div');
        row.className = `msg-row ${role === 'user' ? 'user-msg' : 'assistant-msg'}`;

        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerHTML = role === 'user' 
            ? '<i class="fa-solid fa-user"></i>' 
            : '<i class="fa-solid fa-robot"></i>';

        const wrapper = document.createElement('div');
        wrapper.className = 'msg-content-wrapper';

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.innerHTML = renderMarkdown(content);

        wrapper.appendChild(bubble);
        row.appendChild(avatar);
        row.appendChild(wrapper);

        chatMessages.appendChild(row);
        applyCodeHighlighting(bubble);
        scrollToBottom();
    }

    function appendAssistantStreamingBubble() {
        const row = document.createElement('div');
        row.className = 'msg-row assistant-msg';

        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerHTML = '<i class="fa-solid fa-robot"></i>';

        const wrapper = document.createElement('div');
        wrapper.className = 'msg-content-wrapper';

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.innerHTML = '<span class="typing-indicator"><i class="fa-solid fa-circle-notch fa-spin"></i> Thinking...</span>';

        wrapper.appendChild(bubble);
        row.appendChild(avatar);
        row.appendChild(wrapper);

        chatMessages.appendChild(row);
        scrollToBottom();

        return { msgContentEl: bubble, wrapperEl: wrapper };
    }

    function appendToolStepBadge(wrapperEl, toolName, toolArgs) {
        if (!wrapperEl) return;
        const toolId = escapeHtml(toolName || 'tool');
        const existing = wrapperEl.querySelector(`.tool-step-badge[data-tool="${toolId}"]`);
        if (existing) return;

        const stepCard = document.createElement('div');
        stepCard.className = 'tool-step-card tool-step-badge';
        stepCard.setAttribute('data-tool', toolId);

        let friendlyName = toolName;
        if (toolName === 'github_search' || toolName.includes('github')) {
            friendlyName = 'Searching GitHub repositories...';
        } else if (toolName === 'arxiv_search' || toolName.includes('arxiv')) {
            friendlyName = 'Searching arXiv research papers...';
        } else if (toolName === 'tavily_search_results_json' || toolName.includes('tavily') || toolName.includes('search')) {
            friendlyName = 'Searching the web...';
        } else if (toolName === 'retrieve_documents' || toolName.includes('retrieve') || toolName.includes('rag') || toolName.includes('doc')) {
            friendlyName = 'Searching uploaded documents (RAG)...';
        } else if (toolName.includes('memory')) {
            friendlyName = 'Accessing long-term memory...';
        } else if (toolName.includes('calc') || toolName.includes('sympy') || toolName.includes('math')) {
            friendlyName = 'Executing mathematical calculation...';
        } else {
            friendlyName = `Using tool: ${toolName}`;
        }

        stepCard.innerHTML = `
            <i class="fa-solid fa-bolt"></i>
            <span>${escapeHtml(friendlyName)}</span>
        `;
        wrapperEl.insertBefore(stepCard, wrapperEl.firstChild);
    }

    function renderMarkdown(text) {
        if (window.marked && text) {
            return marked.parse(text);
        }
        return escapeHtml(text || '');
    }

    function applyCodeHighlighting(container) {
        if (window.hljs && container) {
            container.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
    }

    function scrollToBottom() {
        if (contentScrollArea) {
            contentScrollArea.scrollTop = contentScrollArea.scrollHeight;
        }
    }

    function setSendButtonState(disabled) {
        if (!sendBtn) return;
        sendBtn.disabled = disabled;
        if (disabled) {
            sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        } else {
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> <span class="send-label">Send</span>';
        }
    }

    // --- File Upload Handler ---
    async function handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!activeThreadId) {
            try {
                const response = await fetch('/conversations', { method: 'POST' });
                if (response.ok) {
                    const data = await response.json();
                    activeThreadId = data.thread_id;
                }
            } catch (err) {
                console.error(err);
            }
        }

        // Show File Preview Bar
        if (filePreviewBar) {
            filePreviewBar.classList.remove('hidden');
            if (fileNameDisplay) fileNameDisplay.textContent = file.name;
            if (fileStatusDisplay) {
                fileStatusDisplay.textContent = 'Uploading...';
                fileStatusDisplay.style.color = '#60a5fa';
            }
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('thread_id', activeThreadId || '');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'File upload failed');
            }

            const result = await response.json();
            if (fileStatusDisplay) {
                fileStatusDisplay.textContent = 'Indexed in RAG!';
                fileStatusDisplay.style.color = '#34d399';
            }
            showToast(`Document '${file.name}' indexed successfully!`, 'success');
        } catch (err) {
            console.error(err);
            if (fileStatusDisplay) {
                fileStatusDisplay.textContent = 'Failed';
                fileStatusDisplay.style.color = '#f87171';
            }
            showToast(err.message, 'error');
        }
    }

    function clearFilePreview() {
        if (fileInput) fileInput.value = '';
        if (filePreviewBar) filePreviewBar.classList.add('hidden');
    }

    // --- Speech Recognition ---
    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            if (micBtn) micBtn.style.display = 'none';
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            if (userInput) {
                userInput.value = (userInput.value ? userInput.value + ' ' : '') + transcript;
            }
        };

        recognition.onend = () => {
            isListening = false;
            micBtn?.classList.remove('listening');
        };
    }

    function toggleListening() {
        if (!recognition) return;
        if (isListening) {
            recognition.stop();
            isListening = false;
            micBtn?.classList.remove('listening');
        } else {
            recognition.start();
            isListening = true;
            micBtn?.classList.add('listening');
            showToast('Listening for voice prompt...', 'info');
        }
    }

    // --- Audio Speech Synthesis ---
    function speakText(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();

        // Strip HTML tags for clean speech
        const cleanText = text.replace(/<[^>]*>/g, '').replace(/[*_#`]/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    // --- Utilities ---
    function showToast(message, type = 'info') {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fa-solid ${type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i> <span>${escapeHtml(message)}</span>`;

        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
