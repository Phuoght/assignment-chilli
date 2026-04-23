/* ─────────────────────────────────────────────
   Chilli KB — Frontend Logic (NotebookLM style)
───────────────────────────────────────────── */

// ── DOM refs ──────────────────────────────────
const inputForm        = document.getElementById('inputForm');
const inputField       = document.getElementById('inputField');
const sendBtn          = document.getElementById('sendBtn');
const clearBtn         = document.getElementById('clearBtn');
const messagesContainer = document.getElementById('messagesContainer');
const chatContent      = document.getElementById('chatContent');
const typingIndicator  = document.getElementById('typingIndicator');
const welcomeScreen    = document.getElementById('welcomeScreen');
const apiKeyInput      = document.getElementById('apiKeyInput');
const statusDot        = document.getElementById('statusDot');
const statusText       = document.getElementById('statusText');
const queryCountEl     = document.getElementById('queryCount');
const docListEl        = document.getElementById('docList');
const sidebarToggle    = document.getElementById('sidebarToggle');
const sidebar          = document.getElementById('sidebar');

// ── State ─────────────────────────────────────
let isLoading    = false;
let queryCount   = 0;

// ── API key persistence ───────────────────────
const STORED_KEY = 'chilli_api_key';

function loadApiKey() {
    const saved = localStorage.getItem(STORED_KEY);
    if (saved) {
        apiKeyInput.value = saved;
        setApiStatus(true);
    }
}

function setApiStatus(valid) {
    if (valid) {
        statusDot.classList.add('active');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('active');
        statusText.textContent = 'Not set';
    }
}

apiKeyInput.addEventListener('input', () => {
    const key = apiKeyInput.value.trim();
    if (key.startsWith('sk-ant-') && key.length > 20) {
        localStorage.setItem(STORED_KEY, key);
        setApiStatus(true);
    } else {
        setApiStatus(false);
    }
});

// ── Sidebar toggle ────────────────────────────
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// ── Load KB status from API ───────────────────
async function loadKbStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (docListEl) {
            docListEl.innerHTML = '';
            if (data.docs && data.docs.length > 0) {
                data.docs.forEach(name => {
                    const cleanName = name.replace(/^\d+_/, '').replace('.docx', '').replace(/_/g, ' ');
                    const item = document.createElement('div');
                    item.className = 'doc-item';
                    item.innerHTML = `<span class="doc-icon">📄</span>${cleanName}`;
                    docListEl.appendChild(item);
                });
            } else {
                docListEl.innerHTML = '<div class="doc-loading">No documents loaded</div>';
            }
        }
    } catch (e) {
        console.error('Status fetch error', e);
    }
}

// ── Auto-resize textarea ──────────────────────
inputField.addEventListener('input', () => {
    inputField.style.height = 'auto';
    inputField.style.height = Math.min(inputField.scrollHeight, 160) + 'px';
});

// ── Markdown renderer ─────────────────────────
function renderMarkdown(text) {
    let html = text;

    // Escape HTML first
    html = html
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Headers
    html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^#### (.+)$/gm,  '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm,   '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm,    '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm,     '<h1>$1</h1>');

    // Bold & italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g,      '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g,          '<em>$1</em>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Horizontal rule
    html = html.replace(/^---+$/gm, '<hr>');

    // Unordered list items
    html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    // Ordered list items
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>[\s\S]*?<\/li>)(\s*<li>[\s\S]*?<\/li>)*/g, (match) => {
        return '<ul>' + match + '</ul>';
    });

    // Paragraphs (double newlines)
    html = html.replace(/\n\n+/g, '</p><p>');
    // Single newlines → <br>
    html = html.replace(/\n/g, '<br>');

    // Wrap if not already a block element
    if (!/^<(h[1-5]|ul|ol|hr|p)/.test(html.trim())) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

// ── Citation injection ────────────────────────
function injectCitations(html, references) {
    if (!references || references.length === 0) return html;

    return html.replace(/\[(\d+)\]/g, (match, num) => {
        const idx = parseInt(num) - 1;
        if (idx < 0 || idx >= references.length) return match;
        const ref = references[idx];
        const file = escHtml(ref.file);
        const preview = escHtml(ref.content);
        return `<span class="citation" tabindex="0" aria-label="Source ${num}: ${ref.file}">${num}<span class="citation-tooltip"><span class="tooltip-file">📄 ${file}</span><span class="tooltip-preview">${preview}</span></span></span>`;
    });
}

function escHtml(str) {
    return str
        .replace(/&amp;/g, '&')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Scroll to bottom ──────────────────────────
function scrollBottom() {
    chatContent.scrollTop = chatContent.scrollHeight;
}

// ── Hide welcome screen ───────────────────────
function hideWelcome() {
    if (welcomeScreen) welcomeScreen.style.display = 'none';
}

// ── Add user message bubble ───────────────────
function addUserMessage(text) {
    hideWelcome();
    const div = document.createElement('div');
    div.className = 'message message-user';
    div.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
    messagesContainer.appendChild(div);
    scrollBottom();
}

// ── Add assistant message ─────────────────────
function addAssistantMessage(text, references = [], suggestions = []) {
    let html = renderMarkdown(text);
    html = injectCitations(html, references);

    // Sources panel
    let sourcesHtml = '';
    if (references && references.length > 0) {
        const rows = references.map(ref => `
            <div class="source-row">
                <div class="source-badge">${ref.id}</div>
                <div class="source-info">
                    <span class="source-file">📄 ${escHtml(ref.file)}</span>
                    <span class="source-preview">${escHtml(ref.content)}</span>
                </div>
            </div>`).join('');
        sourcesHtml = `
            <div class="sources-panel">
                <div class="sources-header" onclick="toggleSources(this)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    ${references.length} source${references.length > 1 ? 's' : ''} used
                    <svg class="sources-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                </div>
                <div class="sources-body">${rows}</div>
            </div>`;
    }

    // Suggestion chips
    let suggestHtml = '';
    if (suggestions && suggestions.length > 0) {
        const btns = suggestions.map(q =>
            `<button class="suggestion-btn" data-q="${escHtml(q)}">${escHtml(q)}</button>`
        ).join('');
        suggestHtml = `<div class="suggestions-wrap">${btns}</div>`;
    }

    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.innerHTML = `
        <div class="bot-avatar">🌶️</div>
        <div class="bot-content">
            <div class="message-text">${html}</div>
            <div class="message-actions">
                <button class="action-btn" onclick="copyMsg(this)" title="Copy">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                    </svg>
                    Copy
                </button>
                <button class="action-btn" onclick="thumbUp(this)" title="Good answer">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/>
                    </svg>
                </button>
                <button class="action-btn" onclick="thumbDown(this)" title="Bad answer">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17"/>
                    </svg>
                </button>
            </div>
            ${sourcesHtml}
            ${suggestHtml}
        </div>`;

    messagesContainer.appendChild(div);

    // Wire suggestion buttons
    div.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const q = btn.getAttribute('data-q');
            inputField.value = q;
            inputField.dispatchEvent(new Event('input'));
            inputForm.dispatchEvent(new Event('submit'));
        });
    });

    scrollBottom();
}

// ── Toggle sources panel ──────────────────────
function toggleSources(header) {
    header.classList.toggle('open');
}

// ── Loading state ─────────────────────────────
function setLoading(val) {
    isLoading = val;
    typingIndicator.style.display = val ? 'flex' : 'none';
    sendBtn.disabled = val;
    inputField.disabled = val;
    if (!val) inputField.focus();
    scrollBottom();
}

// ── Send message ──────────────────────────────
async function sendMessage(text) {
    const apiKey = apiKeyInput.value.trim();
    // API key is now optional in frontend as it can be set via .env on server
    
    addUserMessage(text);
    setLoading(true);

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, api_key: apiKey }),
        });

        const data = await res.json();
        setLoading(false);

        if (!res.ok) {
            const errMsg = data.error || 'Server error';
            if (errMsg.includes('api_key') || errMsg.includes('authentication')) {
                showToast('🔑 Invalid API key — check your Anthropic key');
            } else if (errMsg.includes('rate')) {
                showToast('⏳ Rate limit hit — please wait a moment');
            } else {
                addAssistantMessage(`⚠️ Error: ${errMsg}`);
            }
            return;
        }

        queryCount++;
        if (queryCountEl) queryCountEl.textContent = queryCount;

        addAssistantMessage(data.response, data.references, data.suggested_questions);

    } catch (err) {
        setLoading(false);
        console.error(err);
        addAssistantMessage('⚠️ Network error — please check your connection.');
    }
}

// ── Clear chat ────────────────────────────────
async function clearChat() {
    try {
        await fetch('/api/clear', { method: 'POST' });
        messagesContainer.innerHTML = '';
        welcomeScreen.style.display = 'flex';
        queryCount = 0;
        if (queryCountEl) queryCountEl.textContent = 0;
        showToast('✓ Conversation cleared');
    } catch (e) {
        console.error(e);
    }
}

// ── Action buttons ────────────────────────────
function copyMsg(btn) {
    const text = btn.closest('.bot-content').querySelector('.message-text').innerText;
    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerHTML;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg> Copied!';
        btn.style.color = '#34a853';
        setTimeout(() => { btn.innerHTML = orig; btn.style.color = ''; }, 2000);
    });
}

function thumbUp(btn) {
    btn.style.color = '#34a853';
    showToast('👍 Thanks for the feedback!');
}

function thumbDown(btn) {
    btn.style.color = '#e8412b';
    showToast('👎 Feedback noted — we\'ll improve');
}

// ── Toast ─────────────────────────────────────
function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// ── Event listeners ───────────────────────────
inputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = inputField.value.trim();
    if (!msg || isLoading) return;
    inputField.value = '';
    inputField.style.height = 'auto';
    sendMessage(msg);
});

// Shift+Enter = newline, Enter = send
inputField.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        inputForm.dispatchEvent(new Event('submit'));
    }
});

clearBtn.addEventListener('click', clearChat);

// Welcome cards
document.querySelectorAll('.welcome-card').forEach(card => {
    card.addEventListener('click', () => {
        const q = card.getAttribute('data-q');
        inputField.value = q;
        inputField.dispatchEvent(new Event('input'));
        inputForm.dispatchEvent(new Event('submit'));
    });
});

// ── Init ──────────────────────────────────────
window.addEventListener('load', () => {
    loadApiKey();
    loadKbStatus();
    inputField.focus();
});
