let token = localStorage.getItem('token');
if (!token) window.location.href = '/index.html';

let currentChatId = null;
let currentUser = null;
let currentAbortController = null;
let lastUserMessage = null;
let allChats = [];

// === THEME ===
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}
applyTheme(localStorage.getItem('theme') || 'dark');

// === API ===
async function api(method, path, body = null, signal = null) {
    const opts = { method, headers: { 'Authorization': 'Bearer ' + token } };
    if (signal) opts.signal = signal;
    if (body && !(body instanceof FormData)) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
        opts.body = body;
    }
    const res = await fetch(path, opts);
    if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('token');
        window.location.href = '/index.html';
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function loadUser() {
    currentUser = await api('GET', '/auth/me');
    document.getElementById('userInfo').textContent = currentUser.username;
}

async function loadModels() {
    try {
        const health = await fetch('/api/v1/health').then(r => r.json());
        const selector = document.getElementById('modelSelector');
        selector.innerHTML = '';
        for (const model of health.allowed_models || ['phi-2']) {
            const opt = document.createElement('option');
            opt.value = model;
            opt.textContent = model;
            selector.appendChild(opt);
        }
    } catch (e) {
        document.getElementById('modelSelector').innerHTML = '<option value="phi-2">phi-2</option>';
    }
}

// === CHATS ===
async function loadChats() {
    allChats = await api('GET', '/api/v1/chats');
    const chatList = document.getElementById('chatList');
    chatList.innerHTML = '';
    for (const chat of allChats) {
        const wrap = document.createElement('div');
        wrap.className = 'chat-item-wrap' + (chat.id === currentChatId ? ' active' : '');

        const item = document.createElement('div');
        item.className = 'chat-item';
        item.textContent = chat.title;
        item.title = chat.title;
        item.onclick = () => selectChat(chat.id);

        const menuBtn = document.createElement('button');
        menuBtn.className = 'chat-item-menu-btn';
        menuBtn.textContent = '⋯';
        menuBtn.onclick = (e) => { e.stopPropagation(); openChatMenu(e, chat.id); };

        wrap.appendChild(item);
        wrap.appendChild(menuBtn);
        chatList.appendChild(wrap);
    }
}

async function selectChat(chatId) {
    currentChatId = chatId;
    loadChats();
    loadMessages();
}

async function createChat() {
    const chat = await api('POST', '/api/v1/chats', { title: 'New Chat', model: document.getElementById('modelSelector').value });
    currentChatId = chat.id;
    loadChats();
    loadMessages();
}

async function renameChat(chatId) {
    const chat = allChats.find(c => c.id === chatId);
    const newTitle = prompt('Rename chat:', chat ? chat.title : '');
    if (!newTitle || !newTitle.trim()) return;
    await api('PATCH', `/api/v1/chats/${chatId}`, { title: newTitle.trim() });
    loadChats();
}

async function deleteChat(chatId) {
    if (!confirm('Delete this chat permanently?')) return;
    await api('DELETE', `/api/v1/chats/${chatId}`);
    if (chatId === currentChatId) {
        currentChatId = null;
        document.getElementById('messagesArea').innerHTML = '';
    }
    loadChats();
}

// === CONTEXT MENU ===
function openChatMenu(e, chatId) {
    const menu = document.getElementById('chatMenu');
    menu.classList.remove('hidden');
    menu.style.left = e.clientX + 'px';
    menu.style.top = e.clientY + 'px';
    menu.dataset.chatId = chatId;
}

document.getElementById('chatMenu').addEventListener('click', (e) => {
    const action = e.target.dataset.action;
    const chatId = parseInt(document.getElementById('chatMenu').dataset.chatId);
    document.getElementById('chatMenu').classList.add('hidden');
    if (action === 'rename') renameChat(chatId);
    else if (action === 'delete') deleteChat(chatId);
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('.chat-item-menu-btn') && !e.target.closest('.context-menu')) {
        document.getElementById('chatMenu').classList.add('hidden');
    }
});

// === MESSAGES ===
async function loadMessages() {
    if (!currentChatId) {
        document.getElementById('messagesArea').innerHTML = '';
        return;
    }
    const data = await api('GET', `/api/v1/chats/${currentChatId}/messages`);
    const area = document.getElementById('messagesArea');
    area.innerHTML = '';
    for (const msg of data) {
        renderMessage(msg.role, msg.content, msg.sources && msg.sources !== '[]' ? JSON.parse(msg.sources) : []);
    }
    area.scrollTop = area.scrollHeight;
}

function renderMessage(role, content, sources = []) {
    const area = document.getElementById('messagesArea');
    const div = document.createElement('div');
    div.className = 'message ' + role;

    if (role === 'user') {
        lastUserMessage = content;
    }

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;
    div.appendChild(bubble);

    if (sources && sources.length > 0) {
        const srcDiv = document.createElement('div');
        srcDiv.className = 'message-sources';
        srcDiv.innerHTML = 'Sources: ' + sources.map(s =>
            `<a href="${s.url || '#'}" target="_blank" class="source-link" title="${escapeHtml(s.title || '')}">[${s.number}]</a>`
        ).join(' ');
        bubble.appendChild(srcDiv);
    }

    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'msg-action-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = () => { navigator.clipboard.writeText(content); copyBtn.textContent = 'Copied'; setTimeout(()=>copyBtn.textContent='Copy', 1500); };
    actions.appendChild(copyBtn);

    if (role === 'user') {
        const editBtn = document.createElement('button');
        editBtn.className = 'msg-action-btn';
        editBtn.textContent = 'Edit';
        editBtn.onclick = () => editMessage(div, content);
        actions.appendChild(editBtn);
    }

    if (role === 'assistant') {
        const regenBtn = document.createElement('button');
        regenBtn.className = 'msg-action-btn';
        regenBtn.textContent = 'Regenerate';
        regenBtn.onclick = () => regenerate();
        actions.appendChild(regenBtn);
    }

    div.appendChild(actions);
    area.appendChild(div);
    return div;
}

function editMessage(msgDiv, content) {
    const bubble = msgDiv.querySelector('.message-bubble');
    bubble.style.display = 'none';
    const actions = msgDiv.querySelector('.message-actions');
    if (actions) actions.style.display = 'none';

    const editForm = document.createElement('div');
    editForm.style.cssText = 'display:flex; flex-direction:column; gap:8px; max-width:70%;';

    const ta = document.createElement('textarea');
    ta.className = 'edit-textarea';
    ta.value = content;
    ta.style.cssText = 'padding:10px; border:1px solid #d1d5db; border-radius:6px; font-size:14px; resize:vertical; min-height:60px;';
    editForm.appendChild(ta);

    const btns = document.createElement('div');
    btns.style.cssText = 'display:flex; gap:8px;';
    const save = document.createElement('button');
    save.className = 'msg-action-btn';
    save.style.cssText = 'background:#10a37f; color:white; border-color:#10a37f;';
    save.textContent = 'Save';
    save.onclick = () => {
        const newText = ta.value.trim();
        if (!newText) return;
        const area = document.getElementById('messagesArea');
        while (area.lastChild && area.lastChild !== msgDiv) area.removeChild(area.lastChild);
        area.removeChild(msgDiv);
        lastUserMessage = newText;
        sendMessage(newText);
    };
    const cancel = document.createElement('button');
    cancel.className = 'msg-action-btn';
    cancel.textContent = 'Cancel';
    cancel.onclick = () => {
        editForm.remove();
        bubble.style.display = '';
        if (actions) actions.style.display = '';
    };
    btns.appendChild(save);
    btns.appendChild(cancel);
    editForm.appendChild(btns);
    msgDiv.appendChild(editForm);
    ta.focus();
}

function regenerate() {
    if (!lastUserMessage) return;
    // remove last assistant bubble
    const area = document.getElementById('messagesArea');
    const msgs = area.querySelectorAll('.message');
    for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].classList.contains('assistant')) { msgs[i].remove(); break; }
    }
    sendMessage(lastUserMessage, true);
}

// === SEND ===
async function sendMessage(text, skipUserRender = false) {
    if (!text.trim()) return;
    const area = document.getElementById('messagesArea');
    lastUserMessage = text;

    if (!skipUserRender) {
        renderMessage('user', text, []);
        area.scrollTop = area.scrollHeight;
    }

    document.getElementById('inputMessage').value = '';
    document.getElementById('sendBtn').classList.add('hidden');
    document.getElementById('stopBtn').classList.remove('hidden');

    const typingMsg = document.createElement('div');
    typingMsg.className = 'message assistant';
    typingMsg.id = 'typingIndicator';
    typingMsg.innerHTML = '<div class="message-bubble"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
    area.appendChild(typingMsg);
    area.scrollTop = area.scrollHeight;

    currentAbortController = new AbortController();

    try {
        const useSearch = document.getElementById('searchToggle').checked;
        const endpoint = useSearch ? '/api/v1/search' : '/api/v1/query';

        const response = await api('POST', endpoint, {
            query: text,
            chat_id: currentChatId,
            search: useSearch,
            docs: true,
            stream: false
        }, currentAbortController.signal);

        const t = document.getElementById('typingIndicator');
        if (t) t.remove();

        currentChatId = response.chat_id;
        loadChats();

        renderMessage('assistant', response.answer || '', response.sources || []);
        area.scrollTop = area.scrollHeight;
    } catch (e) {
        const t = document.getElementById('typingIndicator');
        if (t) t.remove();
        const isAbort = e.name === 'AbortError';
        renderMessage('assistant', isAbort ? '[Generation stopped]' : 'Error: ' + e.message, []);
    } finally {
        document.getElementById('sendBtn').classList.remove('hidden');
        document.getElementById('stopBtn').classList.add('hidden');
        currentAbortController = null;
    }
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// === SCROLL ===
const messagesArea = document.getElementById('messagesArea');
const scrollBtn = document.getElementById('scrollBottomBtn');

messagesArea.addEventListener('scroll', () => {
    const atBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 50;
    scrollBtn.classList.toggle('hidden', atBottom);
});

scrollBtn.addEventListener('click', () => {
    messagesArea.scrollTo({ top: messagesArea.scrollHeight, behavior: 'smooth' });
});

// === EVENT BINDINGS ===
document.getElementById('newChatBtn').addEventListener('click', createChat);
document.getElementById('logoutBtn').addEventListener('click', () => {
    api('POST', '/auth/logout').then(() => {
        localStorage.removeItem('token');
        window.location.href = '/index.html';
    });
});

document.getElementById('themeBtn').addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    applyTheme(cur === 'dark' ? 'light' : 'dark');
});

document.getElementById('stopBtn').addEventListener('click', () => {
    if (currentAbortController) currentAbortController.abort();
});

document.getElementById('inputMessage').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(document.getElementById('inputMessage').value);
    }
});

document.getElementById('sendBtn').addEventListener('click', () => {
    sendMessage(document.getElementById('inputMessage').value);
});

document.getElementById('uploadBtn').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    const status = document.getElementById('uploadStatus');
    status.textContent = 'Uploading ' + file.name + '...';
    status.style.cssText = 'font-size:13px; color:#6b7280;';

    try {
        const res = await fetch('/api/v1/ingest/file', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData,
            timeout: 120000
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Upload failed');
        }

        status.innerHTML = '<div style="color: #10a37f; font-size: 13px; margin-top:4px;">File uploaded successfully. Indexing in background...</div>';
        console.log('Upload success:', data);
        setTimeout(() => { status.textContent = ''; }, 5000);
    } catch (e) {
        console.error('Upload error:', e);
        status.innerHTML = '<div style="color: #d32f2f; font-size: 13px; margin-top:4px;">Upload failed: ' + (e.message || 'Unknown error') + '</div>';
    }

    document.getElementById('fileInput').value = '';
});

window.addEventListener('load', async () => {
    await loadModels();
    await loadUser();
    await loadChats();
    if (currentChatId === null && allChats.length === 0) {
        await createChat();
    }
});
