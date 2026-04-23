import os
import re
import json
import secrets
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from flask import Flask, render_template, request, jsonify, session, Response
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Config
EMBED_MODEL  = "BAAI/bge-m3"
TOP_K        = 20
MAX_TOKENS   = 2000
NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY")
NINEROUTER_MODEL = os.getenv("NINEROUTER_MODEL", "maple-combo")

SYSTEM_PROMPT = """<system>
  <identity>
    <role>Chilli Legal & HR Assistant</role>
    <expertise>Pháp luật Việt Nam và chính sách nhân sự</expertise>
  </identity>

  <core_instruction>
    <guideline>Chỉ trích dẫn từ Context được cung cấp, không thêm thông tin từ kiến thức chung</guideline>
    <guideline>Giải thích rõ ràng các thuật ngữ chuyên môn và tiếng nước ngoài</guideline>
    <guideline>Khi không có thông tin, hãy nói thẳng ra thay vì guessing</guideline>
    <guideline>TUYỆT ĐỐI KHÔNG sử dụng các thẻ HTML (như &lt;br&gt;, &lt;b&gt;, &lt;i&gt;). Chỉ sử dụng Markdown thuần túy.</guideline>
  </core_instruction>

  <style>
    <tone>Chuyên nghiệp nhưng thân thiện, chi tiết nhưng dễ tiếp cận</tone>
    <approach>Tự do chọn cách trình bày phù hợp với từng câu hỏi (không bắt buộc theo format cố định)</approach>
    <formatting>Sử dụng Markdown một cách tự nhiên để làm cho nội dung dễ đọc</formatting>
  </style>

  <citation>
    <method>Trích dẫn nguồn bằng [1], [2]... sau mỗi thông tin từ Context</method>
    <requirement>Rõ ràng nhưng không cườn cứng</requirement>
  </citation>
</system>
"""

# ─────────────────────────────────────────────────────────────
# Hybrid RAG Retriever
# ─────────────────────────────────────────────────────────────
class HybridRetriever:
    def __init__(self, index_name: str, jsonl_file: str, embeddings):
        self.index_name = index_name
        self.chunks = []
        self.vectorstore = None
        self.bm25 = None
        self.chunk_map = {}

        print(f"🔧 [Init] Setting up Retriever for [{index_name}]...")
        
        # Load FAISS
        faiss_dir = "vectorstore"
        if (Path(faiss_dir) / f"{index_name}.faiss").exists() or (Path(faiss_dir) / f"{index_name}.index").exists():
            self.vectorstore = FAISS.load_local(
                faiss_dir, 
                embeddings, 
                index_name=index_name,
                allow_dangerous_deserialization=True
            )
            print(f"   ✅ FAISS [{index_name}] Loaded.")
        
        # Load Chunks & BM25 (with Cache)
        bm25_cache_path = Path(faiss_dir) / f"{index_name}_bm25.pkl"
        
        if Path(jsonl_file).exists():
            # Load Chunks
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    self.chunks.append(Document(page_content=data["text"], metadata=data["metadata"]))
            self.chunk_map = {i: doc for i, doc in enumerate(self.chunks)}

            # Try loading BM25 from cache
            if bm25_cache_path.exists():
                try:
                    with open(bm25_cache_path, "rb") as f:
                        self.bm25 = pickle.load(f)
                    print(f"   ✅ BM25 [{index_name}] Loaded from cache.")
                except Exception as e:
                    print(f"   ⚠️ [Warning] Failed to load BM25 cache: {e}. Rebuilding...")
            
            # Build if not loaded
            if not self.bm25:
                print(f"   🔨 Building BM25 index for [{index_name}] (this may take a while)...")
                tokenized_corpus = [re.findall(r"[\w\u4e00-\u9fff]+", doc.page_content.lower()) for doc in self.chunks]
                self.bm25 = BM25Okapi(tokenized_corpus)
                
                # Save cache
                with open(bm25_cache_path, "wb") as f:
                    pickle.dump(self.bm25, f)
                print(f"   ✅ BM25 [{index_name}] Built and Cached ({len(self.chunks)} chunks).")

    def retrieve(self, query: str, k: int = TOP_K) -> list[Document]:
        if not self.vectorstore or not self.bm25:
            print(f"⚠️ [Error] Retriever [{self.index_name}] is not properly initialized.")
            return []

        print(f"   🔎 [{self.index_name}] Step 1: Dense Search (FAISS)...")
        vector_docs = self.vectorstore.similarity_search(query, k=k * 2)
        
        print(f"   🔎 [{self.index_name}] Step 2: Sparse Search (BM25)...")
        tokenized_query = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][: k * 2]

        print(f"   🔎 [{self.index_name}] Step 3: RRF Fusion...")
        rrf = {}
        for rank, doc in enumerate(vector_docs):
            idx = doc.metadata.get("chunk_id")
            if idx is not None: rrf[idx] = rrf.get(idx, 0) + 1 / (rank + 60)
        for rank, idx in enumerate(bm25_top_indices):
            rrf[idx] = rrf.get(idx, 0) + 1 / (rank + 60)

        top_indices = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.chunk_map[i] for i, _ in top_indices if i in self.chunk_map]

# ─────────────────────────────────────────────────────────────
# Singleton Manager
# ─────────────────────────────────────────────────────────────
class RAGManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGManager, cls).__new__(cls)
            cls._instance.retrievers = {}
            cls._instance._embeddings = None
        return cls._instance

    @property
    def embeddings(self):
        if self._embeddings is None:
            print(f"🚀 [System] Loading Embedding Model: {EMBED_MODEL}...")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=EMBED_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            print("✅ [System] Embedding Model Loaded.")
        return self._embeddings

    def get_retriever(self, mode="law"):
        if mode not in self.retrievers:
            if mode == "law":
                self.retrievers["law"] = HybridRetriever("law", "law_chunks.jsonl", self.embeddings)
            else:
                self.retrievers["internal"] = HybridRetriever("internal_policies", "internal_policies_chunks.jsonl", self.embeddings)
        return self.retrievers[mode]

rag_manager = RAGManager()

# ─────────────────────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        query = data.get("message", "").strip()
        ui_mode = data.get("mode", "all") 
        lang = data.get("lang", "vi")
        history = data.get("history", [])

        if not query: return jsonify({"error": "Message is required"}), 400
        
        if not NINEROUTER_API_KEY:
            return jsonify({"error": "NineRouter API key is not configured in .env"}), 500

        client = OpenAI(api_key=NINEROUTER_API_KEY, base_url="http://localhost:20128/v1")

        # Step 0: Query Rewriting for Memory
        search_query = query
        if history:
            try:
                rewrite_sys = "Nhiệm vụ: Viết lại câu hỏi của người dùng thành một câu khẳng định tìm kiếm RAG đầy đủ bằng tiếng Việt. QUY TẮC: 1. CHỈ trả về kết quả cuối cùng. 2. KHÔNG giải thích, không 'Dựa trên...', không 'Câu hỏi là...'. 3. KHÔNG sử dụng bất kỳ ngôn ngữ nào khác ngoài tiếng Việt."
                hist_context = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history[-2:]])
                rewrite_prompt = f"Lịch sử:\n{hist_context}\n\nCâu hỏi mới: {query}"
                
                rewrite_res = client.chat.completions.create(
                    model=NINEROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": rewrite_sys},
                        {"role": "user", "content": rewrite_prompt}
                    ],
                    max_tokens=100,
                    temperature=0
                )
                raw_rewrite = rewrite_res.choices[0].message.content.strip()
                # Clean meta-text if AI ignores instructions
                if "viết lại" in raw_rewrite.lower() or "câu hỏi" in raw_rewrite.lower():
                    lines = raw_rewrite.split('\n')
                    search_query = lines[-1].strip('- ').strip()
                else:
                    search_query = raw_rewrite
                
                print(f"🔍 [Query Rewrite]: '{query}' -> '{search_query}'")
            except Exception as e:
                print(f"⚠️ Rewrite Error: {e}")

        retriever_keys = []
        if ui_mode == "all":
            retriever_keys = ["law", "internal"]
        elif ui_mode == "legal":
            retriever_keys = ["law"]
        else:
            retriever_keys = ["internal"]

        all_docs = []
        for r_key in retriever_keys:
            r = rag_manager.get_retriever(r_key)
            all_docs.extend(r.retrieve(search_query, k=TOP_K))

        docs = all_docs[:TOP_K]
        context = "\n\n".join([f"<doc id='{i+1}'>{d.page_content}</doc>" for i, d in enumerate(docs)])
        refs = [{"id": i+1, "file": d.metadata.get("file", "Unknown"), "content": d.page_content[:250]} for i, d in enumerate(docs)]

        def generate():
            yield f"data: {json.dumps({'references': refs})}\n\n"

            # Prepare messages with Memory embedded in content
            history_str = ""
            if history:
                history_items = []
                for m in history:
                    role_label = "User" if m["role"] == "user" else "Chilli"
                    history_items.append(f"{role_label}: {m['content']}")
                history_str = "\n".join(history_items)

            # Combined Prompt with explicit sections
            user_content = f"""
### CONVERSATION HISTORY:
{history_str if history_str else "No previous messages."}

### SEARCHED CONTEXT:
{context}

### CURRENT QUESTION:
{query}
""".strip()

            messages = [
                {"role": "system", "content": f"{SYSTEM_PROMPT}\nScope: {ui_mode}.\nResponse Language: {lang} (Strictly answer in this language)."},
                {"role": "user", "content": user_content}
            ]

            stream = client.chat.completions.create(
                model=NINEROUTER_MODEL,
                max_tokens=MAX_TOKENS,
                messages=messages,
                stream=True
            )

            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Generate dynamic suggestions based on the response
            try:
                lang_name = "tiếng Việt" if lang == "vi" else "English"
                suggestion_sys = f"Bạn là trợ lý đề xuất câu hỏi. CHỈ trả về đúng 3 câu hỏi bằng {lang_name} liên quan đến câu trả lời trước đó. Định dạng: Mỗi câu hỏi trên một dòng. KHÔNG đánh số, KHÔNG giải thích, KHÔNG nói gì thêm."
                suggest_prompt = f"Câu trả lời: {full_response[:800]}\n\nĐề xuất 3 câu hỏi tiếp theo:"
                
                print(f"🤖 [Suggestion] Generating for {lang_name}...")
                
                suggestion_res = client.chat.completions.create(
                    model=NINEROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": suggestion_sys},
                        {"role": "user", "content": suggest_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.1
                )
                raw_content = suggestion_res.choices[0].message.content.strip()
                print(f"✅ [Suggestion] AI Returned: {raw_content}")
                
                print(f"DEBUG: Suggestions result: {raw_sugg}")
                suggestions = []
                for s in raw_sugg:
                    s_clean = s.strip('- ').strip('123. ').strip()
                    if s_clean and ('?' in s_clean or len(s_clean) > 10):
                        # Filter out meta-text
                        if not any(word in s_clean.lower() for word in ['let\'s', 'produce', 'output', 'here are', 'assistant']):
                            suggestions.append(s_clean)
                
                suggestions = suggestions[:3]
                if not suggestions: raise ValueError("Empty suggestions after parsing")
                print(f"🚀 [Suggestion] Final list: {suggestions}")
            except Exception as e:
                print(f"❌ [Suggestion Error]: {e}")
                suggestions = ["Tìm hiểu thêm về mục này", "Ví dụ cụ thể là gì?", "Quy trình thực hiện như thế nào?"]

            yield f"data: {json.dumps({'suggested_questions': suggestions})}\n\n"
            yield "data: [DONE]\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"❌ [Exception] Error in /api/chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"status": "ready", "modes": ["law", "internal"]})

if __name__ == "__main__":
    # ONLY pre-warm in the main worker process, not the reloader's watcher process
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("🔥 [System] Pre-warming RAG models in main worker...")
        # Note: Pre-warming will still take time on first run, 
        # but BM25 caching will make subsequent starts much faster.
        rag_manager.get_retriever("law")
        rag_manager.get_retriever("internal")
    else:
        print("🔍 [System] Flask watcher starting...")

    app.run(debug=True, host="0.0.0.0", port=5000)
