/* ─────────────────────────────────────────────
   Chilli KB — Frontend Logic (NotebookLM style)
───────────────────────────────────────────── */

// ── DOM refs ──────────────────────────────────
const inputForm        = document.getElementById('inputForm');
const inputField       = document.getElementById('inputField');
const sendBtn          = document.getElementById('sendBtn');
const newChatBtn       = document.getElementById('newChatBtn');
const messagesContainer = document.getElementById('messagesContainer');
const chatContent      = document.getElementById('chatContent');
const typingIndicator  = document.getElementById('typingIndicator');
const welcomeScreen    = document.getElementById('welcomeScreen');
const sidebarToggle    = document.getElementById('sidebarToggle');
const sidebar          = document.getElementById('sidebar');
const modeItems        = document.querySelectorAll('.mode-item');
const langToggle       = document.getElementById('langToggle');

// ── I18n / Localization ────────────────────────
const i18n = {
    vi: {
        lang: 'VN',
        newChat: 'Hội thoại mới',
        searchMode: 'Chế độ tìm kiếm',
        modeGlobal: 'Tìm kiếm chung',
        modeInternal: 'Chính sách nội bộ',
        modeLegal: 'Pháp lý & Tuân thủ',
        history: 'Lịch sử hội thoại',
        historyEmpty: 'Chưa có hội thoại nào',
        welcomeTitle: 'Chilli Knowledge Base',
        welcomeSub: 'Hỏi bất cứ điều gì về các văn bản quy phạm pháp luật và chính sách nội bộ.<br>Tôi sẽ tìm kiếm trong các tài liệu hợp nhất để đưa ra câu trả lời chính xác.',
        inputPlaceholder: 'Hỏi về quy định công ty, nhân sự, quy trình và pháp luật...',
        inputHint: 'Chilli KB tìm kiếm trên tất cả tài liệu công ty · Câu trả lời kèm trích dẫn nguồn',
        sourcesUsed: 'nguồn đã sử dụng',
        suggestedTitle: 'Dựa trên câu trả lời, bạn có thể muốn hỏi:',
        modes: {
            all: [
                { q: "Luật Xây dựng quy định gì về giấy phép xây dựng?", icon: "🏗️" },
                { q: "Quy trình giám định tư pháp được thực hiện như thế nào?", icon: "⚖️" },
                { q: "Quy định về thời gian làm việc và nghỉ ngơi của công ty?", icon: "⏰" },
                { q: "Chính sách đi công tác và thanh toán chi phí?", icon: "✈️" }
            ],
            internal: [
                { q: "Quy định về thời gian làm việc và nghỉ ngơi của công ty?", icon: "⏰" },
                { q: "Chính sách đi công tác và thanh toán chi phí?", icon: "✈️" },
                { q: "Quy trình xin nghỉ phép và phê duyệt?", icon: "📝" },
                { q: "Chế độ bảo hiểm và phúc lợi nhân viên?", icon: "🏥" }
            ],
            legal: [
                { q: "Luật Xây dựng quy định gì về giấy phép xây dựng?", icon: "🏗️" },
                { q: "Quy trình giám định tư pháp được thực hiện như thế nào?", icon: "⚖️" },
                { q: "Luật Nhà ở quy định như thế nào về sở hữu nhà ở của người nước ngoài?", icon: "🏠" },
                { q: "Các quy định về bảo vệ môi trường trong xây dựng?", icon: "🌿" }
            ]
        }
    },
    en: {
        lang: 'EN',
        newChat: 'New Chat',
        searchMode: 'Search Mode',
        modeGlobal: 'Global Search',
        modeInternal: 'Internal Policies',
        modeLegal: 'Legal & Compliance',
        history: 'Chat History',
        historyEmpty: 'No conversations yet',
        welcomeTitle: 'Chilli Knowledge Base',
        welcomeSub: 'Ask anything about legal documents and internal policies.<br>I will search across consolidated documents to provide accurate answers.',
        inputPlaceholder: 'Ask about company policies, HR, process and legal...',
        inputHint: 'Chilli KB searches across all company documents · Answers include source citations',
        sourcesUsed: 'sources used',
        suggestedTitle: 'Based on the answer, you might want to ask:',
        modes: {
            all: [
                { q: "What does the Construction Law say about building permits?", icon: "🏗️" },
                { q: "How is the judicial expertise process performed?", icon: "⚖️" },
                { q: "What are the company's working hours and rest periods?", icon: "⏰" },
                { q: "Policies on business trips and expense reimbursements?", icon: "✈️" }
            ],
            internal: [
                { q: "What are the company's working hours and rest periods?", icon: "⏰" },
                { q: "Policies on business trips and expense reimbursements?", icon: "✈️" },
                { q: "Leave application and approval process?", icon: "📝" },
                { q: "Employee insurance and welfare benefits?", icon: "🏥" }
            ],
            legal: [
                { q: "What does the Construction Law say about building permits?", icon: "🏗️" },
                { q: "How is the judicial expertise process performed?", icon: "⚖️" },
                { q: "What are the housing ownership rules for foreigners?", icon: "🏠" },
                { q: "Environmental protection rules in construction?", icon: "🌿" }
            ]
        }
    }
};

let currentLang = localStorage.getItem('chilli_lang') || 'vi';

function updateUIStrings() {
    const t = i18n[currentLang];
    
    // Toggle classes for the sliding switch
    if (currentLang === 'vi') {
        langToggle.classList.remove('en-active');
        langToggle.querySelector('.vn-text').classList.add('active');
        langToggle.querySelector('.en-text').classList.remove('active');
    } else {
        langToggle.classList.add('en-active');
        langToggle.querySelector('.vn-text').classList.remove('active');
        langToggle.querySelector('.en-text').classList.add('active');
    }

    document.getElementById('newChatLabel').innerText = t.newChat;
    document.getElementById('searchModeLabel').innerText = t.searchMode;
    document.getElementById('modeGlobalLabel').innerText = t.modeGlobal;
    document.getElementById('modeInternalLabel').innerText = t.modeInternal;
    document.getElementById('modeLegalLabel').innerText = t.modeLegal;
    document.getElementById('historyLabel').innerText = t.history;
    const historyEmpty = document.getElementById('historyEmptyLabel');
    if (historyEmpty) historyEmpty.innerText = t.historyEmpty;
    
    document.getElementById('welcomeTitle').innerText = t.welcomeTitle;
    document.getElementById('welcomeSub').innerHTML = t.welcomeSub;
    inputField.placeholder = t.inputPlaceholder;
    document.querySelector('.input-hint').innerText = t.inputHint;
    
    renderWelcomeCards();
}

// ── State ─────────────────────────────────────
let isLoading    = false;
let currentMode  = 'all';
let currentChatId = null;
let conversations = JSON.parse(localStorage.getItem('chilli_conversations') || '{}');

const LOGO_URL = "/static/images/Outlook-Chilli.png";

// ── Sidebar toggle ────────────────────────────
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// ── Mode selection ────────────────────────────
modeItems.forEach(item => {
    item.addEventListener('click', () => {
        modeItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        currentMode = item.getAttribute('data-mode');
        renderWelcomeCards();
        showToast(`Mode switched to: ${item.querySelector('.mode-name').textContent}`);
    });
});

function renderWelcomeCards() {
    const container = document.getElementById('welcomeCards');
    if (!container) return;
    
    const questions = i18n[currentLang].modes[currentMode] || i18n[currentLang].modes.all;
    container.innerHTML = questions.map(item => `
        <button class="welcome-card" data-q="${escHtml(item.q)}">
            <span class="wc-icon">${item.icon}</span>
            <span class="wc-text">${escHtml(item.q)}</span>
        </button>
    `).join('');

    container.querySelectorAll('.welcome-card').forEach(card => {
        card.addEventListener('click', () => {
            const q = card.getAttribute('data-q');
            inputField.value = q;
            inputField.dispatchEvent(new Event('input'));
            inputForm.dispatchEvent(new Event('submit'));
        });
    });
}

// ── Auto-resize textarea ──────────────────────
inputField.addEventListener('input', () => {
    inputField.style.height = 'auto';
    inputField.style.height = Math.min(inputField.scrollHeight, 160) + 'px';
});

// ── Markdown renderer ─────────────────────────
function renderMarkdown(text) {
    let html = text;

    // 1. Strip <think> blocks FIRST
    html = html.replace(/<think>[\s\S]*?<\/think>/gi, '');
    html = html.replace(/<think>[\s\S]*/gi, '');

    // 2. Escape HTML
    html = html
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Handle escaped <br> tags if model sends them
    html = html.replace(/&lt;br\s*\/?&gt;/gi, '<br>');

    // 3. Tables (BEFORE paragraphs)
    const tableRegex = /^\|(.+)\|\n\|( *[-:]+ *\|)+\n((\|.*\|\n?)*)/gm;
    html = html.replace(tableRegex, (match) => {
        const rows = match.trim().split('\n');
        const header = rows[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
        const body = rows.slice(2).map(row => {
            const cells = row.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
            return `<tr>${cells}</tr>`;
        }).join('');
        return `<div class="table-wrapper"><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`;
    });

    // 4. Blockquotes
    html = html.replace(/^&gt;\s+(.+)$/gm, '<blockquote>$1</blockquote>');

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

    // Wrap consecutive <blockquote> in one
    html = html.replace(/(<blockquote>[\s\S]*?<\/blockquote>)(\s*<blockquote>[\s\S]*?<\/blockquote>)*/g, (match) => {
        return '<div class="quote-wrapper">' + match + '</div>';
    });


    // Paragraphs (only for lines NOT in blocks)
    html = html.replace(/\n\n+/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Final check for un-wrapped content
    if (!/^<(h[1-5]|ul|ol|hr|p|div|blockquote|table)/.test(html.trim())) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

// ── Citation injection ────────────────────────
function injectCitations(html, references) {
    if (!references || references.length === 0) return html;

    // Matches [1] or [1]() or [ 1 ]() etc.
    return html.replace(/\[\s*(\d+)\s*\](?:\(\))?/g, (match, num) => {
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
    if (chatContent) {
        chatContent.scrollTo({
            top: chatContent.scrollHeight,
            behavior: 'smooth'
        });
    }
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

// ── Add assistant message (Streaming version) ─────────────────────
function addAssistantMessage() {
    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.innerHTML = `
        <div class="bot-avatar"><img src="${LOGO_URL}" alt="Chilli"></div>
        <div class="bot-content">
            <div class="message-text"><span class="streaming-dot"></span></div>
            <div class="message-actions" style="display:none;">
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
            </div>
            <div class="sources-area"></div>
            <div class="suggestions-area"></div>
        </div>`;

    messagesContainer.appendChild(div);
    const textEl = div.querySelector('.message-text');
    let fullText = "";

    return {
        append(chunk) {
            fullText += chunk;
            textEl.innerHTML = renderMarkdown(fullText);
            scrollBottom();
        },
        finalize(references = [], suggestions = []) {
            textEl.innerHTML = injectCitations(renderMarkdown(fullText), references);
            div.querySelector('.message-actions').style.display = 'flex';
            
            // Sources
            if (references.length > 0) {
                const rows = references.map(ref => `
                    <div class="source-row">
                        <div class="source-badge">${ref.id}</div>
                        <div class="source-info">
                            <span class="source-file">📄 ${escHtml(ref.file)}</span>
                            <span class="source-preview">${escHtml(ref.content)}</span>
                        </div>
                    </div>`).join('');
                div.querySelector('.sources-area').innerHTML = `
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

            // Suggestions
            if (suggestions.length > 0) {
                const btns = suggestions.map(q =>
                    `<button class="suggestion-btn" data-q="${escHtml(q)}">${escHtml(q)}</button>`
                ).join('');
                div.querySelector('.suggestions-area').innerHTML = `<div class="suggestions-wrap">${btns}</div>`;
                
                div.querySelectorAll('.suggestion-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const q = btn.getAttribute('data-q');
                        inputField.value = q;
                        inputField.dispatchEvent(new Event('input'));
                        inputForm.dispatchEvent(new Event('submit'));
                    });
                });
            }
            scrollBottom();
        }
    };
}

// ── Toggle sources panel ──────────────────────
function toggleSources(header) {
    header.classList.toggle('open');
}

// ── Loading state ─────────────────────────────
function setLoading(val) {
    isLoading = val;
    typingIndicator.innerHTML = `
        <div class="typing-avatar"><img src="${LOGO_URL}" alt="Chilli"></div>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    typingIndicator.style.display = val ? 'flex' : 'none';
    sendBtn.disabled = val;
    inputField.disabled = val;
    if (!val) inputField.focus();
    scrollBottom();
}

// ── Send message (Streaming) ──────────────────────────────
async function sendMessage(text) {
    if (!currentChatId) {
        currentChatId = 'chat_' + Date.now();
    }

    // Initialize conversation in state if new
    if (!conversations[currentChatId]) {
        conversations[currentChatId] = {
            id: currentChatId,
            title: text.substring(0, 35) + (text.length > 35 ? '...' : ''),
            timestamp: Date.now(),
            messages: []
        };
    }

    addUserMessage(text);
    
    // Get history BEFORE adding current message to the array (to avoid duplicating current msg in history)
    const history = conversations[currentChatId].messages.slice(-6);
    
    // Now add current user message to actual storage
    conversations[currentChatId].messages.push({ role: 'user', content: text });

    setLoading(true);
    const controller = addAssistantMessage();
    typingIndicator.style.display = 'none';

    let references = [];
    let suggestions = [];
    let fullResponse = "";

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: text, 
                mode: currentMode,
                lang: currentLang,
                history: history
            }),
        });

        if (!res.ok) {
            const data = await res.json();
            setLoading(false);
            controller.append(`⚠️ Error: ${data.error || 'Server error'}`);
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Store the last partial line

            for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;
                
                const dataStr = trimmedLine.slice(6);
                if (dataStr === '[DONE]') continue;
                
                try {
                    const payload = JSON.parse(dataStr);
                    if (payload.token) {
                        fullResponse += payload.token;
                        controller.append(payload.token);
                    }
                    if (payload.references) {
                        references = payload.references;
                    }
                    if (payload.suggested_questions) {
                        suggestions = payload.suggested_questions;
                    }
                } catch (e) {
                    console.warn("Failed to parse stream chunk:", dataStr);
                }
            }
        }

        setLoading(false);
        controller.finalize(references, suggestions);
        
        // Update assistant message in history
        conversations[currentChatId].messages.push({ 
            role: 'assistant', 
            content: fullResponse, 
            references: references, 
            suggestions: suggestions 
        });
        
        localStorage.setItem('chilli_conversations', JSON.stringify(conversations));
        loadHistory();

    } catch (err) {
        setLoading(false);
        console.error(err);
        controller.append('⚠️ Network error — please check your connection.');
    }
}

// ── Chat history logic ───────────────────────
function loadHistory() {
    const historyEl = document.getElementById('chatHistory');
    if (!historyEl) return;
    
    const keys = Object.keys(conversations).sort((a,b) => conversations[b].timestamp - conversations[a].timestamp);
    
    if (keys.length === 0) {
        historyEl.innerHTML = '<div class="history-empty">No conversations yet</div>';
        return;
    }

    historyEl.innerHTML = keys.map(id => `
        <div class="history-item ${id === currentChatId ? 'active' : ''}" data-id="${id}">
            <div class="history-title" onclick="switchChat('${id}')">${escHtml(conversations[id].title)}</div>
            <button class="history-delete" onclick="deleteChat('${id}')" title="Delete conversation">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `).join('');
}

function saveConversation(id, title, messages) {
    if (!conversations[id]) {
        conversations[id] = {
            id,
            title,
            timestamp: Date.now(),
            messages: []
        };
    }
    conversations[id].messages = messages;
    localStorage.setItem('chilli_conversations', JSON.stringify(conversations));
    loadHistory();
}

function switchChat(id) {
    if (isLoading) return;
    currentChatId = id;
    const chat = conversations[id];
    if (!chat) return;

    messagesContainer.innerHTML = '';
    hideWelcome();
    
    chat.messages.forEach(msg => {
        if (msg.role === 'user') {
            addUserMessage(msg.content);
        } else {
            const controller = addAssistantMessage();
            controller.append(msg.content);
            controller.finalize(msg.references || [], msg.suggestions || []);
        }
    });
    
    loadHistory();
    showToast('Loaded conversation');
}

function deleteChat(id) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    delete conversations[id];
    localStorage.setItem('chilli_conversations', JSON.stringify(conversations));
    
    if (currentChatId === id) {
        startNewChat(false);
    } else {
        loadHistory();
    }
    showToast('Conversation deleted');
}

// ── New Chat ──────────────────────────────────
async function startNewChat(confirmNeeded = false) {
    try {
        await fetch('/api/clear', { method: 'POST' });
        messagesContainer.innerHTML = '';
        welcomeScreen.style.display = 'flex';
        currentChatId = null;
        renderWelcomeCards();
        loadHistory();
        if (confirmNeeded) showToast('✓ Started new conversation');
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

newChatBtn.addEventListener('click', startNewChat);


// ── Lang Toggle ──────────────────────────────
if (langToggle) {
    langToggle.addEventListener('click', () => {
        currentLang = currentLang === 'vi' ? 'en' : 'vi';
        localStorage.setItem('chilli_lang', currentLang);
        updateUIStrings();
        showToast(`✓ Language set to ${currentLang === 'vi' ? 'Tiếng Việt' : 'English'}`);
    });
}

// ── Init ──────────────────────────────────────
window.addEventListener('load', () => {
    updateUIStrings();
    loadHistory();
});
