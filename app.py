import os
import re
import json
import secrets
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from flask import Flask, render_template, request, jsonify, session
from langchain_community.document_loaders import DirectoryLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
DOCS_DIR     = "docs"
FAISS_INDEX  = "vectorstore/law.faiss"
EMBED_MODEL  = "BAAI/bge-m3"
CHUNK_SIZE   = 1000
CHUNK_OVERLAP = 200
TOP_K        = 8
MAX_TOKENS   = 1500

NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY")
NINEROUTER_MODEL = os.getenv("NINEROUTER_MODEL", "maple-combo")

SYSTEM_PROMPT = """You are Chilli Legal & HR Assistant — an expert in Vietnamese legal documents and company policies for Chilli.

Your role:
- Answer questions accurately using ONLY the provided document context
- Vietnamese legal documents can be complex; explain them clearly and professionally
- Always cite your sources using [1], [2], etc. inline
- If the answer is not in the context, respond: "I couldn't find this in our documents. Please contact HR at hr@chilli.com"
- Format answers with clear structure: bullet points, numbered lists, bold key terms
- Respond in the same language as the question (English or Vietnamese)
- Never fabricate legal advice or extrapolate beyond the documents"""

# ─────────────────────────────────────────────────────────────
# Hybrid RAG Retriever (FAISS + BM25 + Reciprocal Rank Fusion)
# ─────────────────────────────────────────────────────────────
class HybridRetriever:
    def __init__(self, docs: list[Document] = None):
        print(f"🔧 Initializing HybridRetriever with {EMBED_MODEL}...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        self.chunks = []
        if docs:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", ".", " "],
            )
            self.chunks = splitter.split_documents(docs)

        # Enrich metadata
        # FAISS vector store
        if Path(FAISS_INDEX).exists():
            self.vectorstore = FAISS.load_local(
                str(Path(FAISS_INDEX).parent), 
                self.embeddings, 
                index_name=Path(FAISS_INDEX).name.replace('.faiss', ''),
                allow_dangerous_deserialization=True
            )
            print(f"✅ Loaded FAISS from {FAISS_INDEX}")
            
            # Load chunks for BM25 from JSONL if possible
            if Path("chunks.jsonl").exists():
                print("📖 Loading chunks from chunks.jsonl for BM25...")
                with open("chunks.jsonl", "r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        self.chunks.append(Document(page_content=data["text"], metadata=data["metadata"]))
            else:
                # Sync from vectorstore (less metadata)
                print("⚠️ chunks.jsonl not found, syncing from vectorstore...")
                self.chunks = [
                    Document(page_content=self.vectorstore.docstore.search(id).page_content, 
                             metadata=self.vectorstore.docstore.search(id).metadata)
                    for id in self.vectorstore.index_to_docstore_id.values()
                ]
        else:
            if not docs:
                raise ValueError("FAISS index not found and no documents provided to build one.")
            
            print("⚠️ FAISS index not found. Building with default splitter...")
            splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            self.chunks = splitter.split_documents(docs)
            for i, chunk in enumerate(self.chunks):
                chunk.metadata["chunk_id"] = i
                chunk.metadata["file"] = Path(chunk.metadata.get("source", "unknown")).name
            self.vectorstore = FAISS.from_documents(self.chunks, self.embeddings)
            self.vectorstore.save_local(str(Path(FAISS_INDEX).parent), index_name=Path(FAISS_INDEX).name.replace('.faiss', ''))
        
        for i, chunk in enumerate(self.chunks):
            chunk.metadata["chunk_id"] = i

        # BM25 sparse retriever
        tokenized_corpus = [
            re.findall(r"[\w]+", doc.page_content.lower())
            for doc in self.chunks
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.chunk_map = {i: doc for i, doc in enumerate(self.chunks)}
        print(f"✅ BM25 built over {len(self.chunks)} chunks")

    def retrieve(self, query: str, k: int = TOP_K) -> list[Document]:
        """Hybrid retrieval: FAISS + BM25 fused with Reciprocal Rank Fusion (RRF)."""
        # Dense retrieval
        vector_docs = self.vectorstore.similarity_search(query, k=k * 2)

        # Sparse retrieval
        tokenized_query = re.findall(r"[\w]+", query.lower())
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][: k * 2]

        # RRF fusion (k=60 is standard)
        rrf: dict[int, float] = {}
        for rank, doc in enumerate(vector_docs):
            idx = doc.metadata.get("chunk_id")
            if idx is not None:
                rrf[idx] = rrf.get(idx, 0) + 1 / (rank + 60)
        for rank, idx in enumerate(bm25_top_indices):
            rrf[idx] = rrf.get(idx, 0) + 1 / (rank + 60)

        # Take top-k by RRF score
        top_indices = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.chunk_map[i] for i, _ in top_indices if i in self.chunk_map]

    def generate_suggested_questions(self, recent_queries: list[str] = None, n: int = 3) -> list[str]:
        """Generate context-aware follow-up questions using Claude."""
        sample = "\n".join(
            f"[{c.metadata['file']}]: {c.page_content[:200]}"
            for c in self.chunks[:12]
        )
        history_block = ""
        if recent_queries:
            history_block = "\n\nRECENT QUESTIONS ASKED (do NOT repeat):\n" + "\n".join(
                f"- {q}" for q in recent_queries[-5:]
            )

        prompt = f"""You are an HR knowledge base assistant for Chilli company.
Based on the document excerpts below, suggest {n} SPECIFIC, USEFUL follow-up questions an employee might ask.

DOCUMENT EXCERPTS:
{sample}
{history_block}

RULES:
- Each question must be answerable from the documents
- Avoid generic questions like "What is the policy?"
- Be specific (e.g., "How many sick leave days can I carry over?")
- 8–15 words each
- Format: numbered list 1. 2. 3.
- Questions in English only"""

        try:
            if not NINEROUTER_API_KEY:
                return []
            client = Anthropic(api_key=NINEROUTER_API_KEY, base_url="http://localhost:20128/v1")
            resp = client.messages.create(
                model=NINEROUTER_MODEL,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            questions = []
            for line in text.split("\n"):
                line = line.strip()
                if re.match(r"^\d+\.", line):
                    q = re.sub(r"^\d+\.\s*", "", line).strip()
                    if q and len(q) > 8:
                        questions.append(q)
            return questions[:n]
        except Exception as e:
            print(f"Suggested questions error: {e}")
            return []


# ─────────────────────────────────────────────────────────────
# Document Loader
# ─────────────────────────────────────────────────────────────
def load_documents() -> list[Document] | None:
    if not Path(DOCS_DIR).exists():
        return None
    
    # Support for both .docx and old .doc files
    docs = []
    
    # Try loading .docx
    try:
        docx_loader = DirectoryLoader(DOCS_DIR, glob="**/*.docx", loader_cls=Docx2txtLoader)
        docs.extend(docx_loader.load())
    except Exception as e:
        print(f"⚠️ Docx loading error: {e}")

    # Try loading .doc (requires unstructured or similar)
    try:
        from langchain_community.document_loaders import UnstructuredWordDocumentLoader
        # List all .doc files
        doc_files = list(Path(DOCS_DIR).glob("**/*.doc"))
        for f in doc_files:
            try:
                loader = UnstructuredWordDocumentLoader(str(f))
                docs.extend(loader.load())
            except Exception as e:
                print(f"⚠️ Error loading {f}: {e}")
    except Exception as e:
        print(f"⚠️ Doc loading (.doc) requires 'unstructured'. Falling back. {e}")

    return docs if docs else None


# Global Retriever Cache
# ─────────────────────────────────────────────────────────────
_retriever: HybridRetriever | None = None

def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        # Check if index exists first
        if Path(FAISS_INDEX).exists():
            _retriever = HybridRetriever()
        else:
            docs = load_documents()
            if not docs:
                raise ValueError("FAISS index not found and no documents available. Please run legal_chunker.py first.")
            _retriever = HybridRetriever(docs)
    return _retriever


# Initialize on startup is now handled at the bottom of the file


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "messages" not in session:
        session["messages"] = []
    doc_files = [p.name for p in Path(DOCS_DIR).glob("**/*.docx")] if Path(DOCS_DIR).exists() else []
    return render_template("index.html", doc_count=len(doc_files))


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data  = request.json or {}
        query = data.get("message", "").strip()

        if not query:
            return jsonify({"error": "Message is required"}), 400
        if not NINEROUTER_API_KEY:
            return jsonify({"error": "NineRouter API key is not configured in .env"}), 500

        retriever = get_retriever()
        docs = retriever.retrieve(query)

        # Build context string
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("file", doc.metadata.get("source", "Unknown"))
            context_parts.append(
                f"<document id='{i+1}' source='{source}'>\n{doc.page_content}\n</document>"
            )
        context = "\n\n".join(context_parts)

        # Build conversation history (last 6 turns)
        if "messages" not in session:
            session["messages"] = []

        messages = []
        for m in session["messages"][-6:]:
            messages.append({"role": m["role"], "content": m["content"]})

        # Current user message with RAG context
        prompt_instructions = """Bạn là chuyên gia về văn bản pháp quy và chính sách tại Chilli. Hãy trả lời câu hỏi dựa trên các tài liệu hợp nhất được cung cấp theo phong cách NotebookLM.

💡 HƯỚNG DẪN TRẢ LỜI:
1. CHỈ sử dụng thông tin từ tài liệu được cung cấp. Không dùng kiến thức bên ngoài.
2. CẤU TRÚC TRẢ LỜI:
   - Mở đầu: Tóm tắt ý chính của quy định (1-2 câu).
   - Nội dung chi tiết: Chia thành các mục (##, ###), giải thích rõ các điều khoản, quy trình.
   - Trích dẫn: Luôn ghi [1], [2]... ngay sau thông tin lấy từ nguồn tương ứng.
3. VĂN PHONG: Trang trọng, chính xác, khách quan.
4. ĐỘ DÀI: Trả lời đầy đủ, chi tiết."""

        user_content = f"""{prompt_instructions}

📚 TÀI LIỆU THAM KHẢO:
{context}

❓ CÂU HỎI:
{query}"""
        messages.append({"role": "user", "content": user_content})

        # Call AI via NineRouter (using Anthropic compatible client)
        client = Anthropic(api_key=NINEROUTER_API_KEY, base_url="http://localhost:20128/v1")
        resp = client.messages.create(
            model=NINEROUTER_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        answer = resp.content[0].text

        # Build references list for frontend
        references = []
        for i, doc in enumerate(docs):
            meta = doc.metadata
            # Hiển thị tiêu đề thông minh: Tên Luật + Điều
            display_name = f"{meta.get('law_name', meta.get('file', 'Unknown'))} - {meta.get('article', 'N/A')}"
            if meta.get('clause') and meta.get('clause') != 'Toàn văn':
                display_name += f" ({meta.get('clause')})"
            
            preview = " ".join(doc.page_content.split())
            if len(preview) > 250:
                preview = preview[:250] + "…"
                
            references.append({
                "id": i + 1,
                "file": display_name,
                "content": preview,
                "full_meta": meta
            })

        # Save to session
        session["messages"].append({"role": "user", "content": query, "ts": datetime.now().isoformat()})
        session["messages"].append({"role": "assistant", "content": answer, "ts": datetime.now().isoformat()})
        session.modified = True

        # Suggested questions
        recent_q = [m["content"] for m in session["messages"] if m["role"] == "user"]
        suggested = retriever.generate_suggested_questions(recent_q)

        return jsonify({
            "response": answer,
            "references": references,
            "suggested_questions": suggested,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    session["messages"] = []
    session.modified = True
    return jsonify({"status": "ok"})


@app.route("/api/status", methods=["GET"])
def status():
    doc_files = list(Path(DOCS_DIR).glob("**/*.docx")) if Path(DOCS_DIR).exists() else []
    index_ready = Path(FAISS_INDEX).exists()
    return jsonify({
        "doc_count": len(doc_files),
        "index_ready": index_ready,
        "docs": [f.name for f in doc_files],
    })


if __name__ == "__main__":
    # Pre-load retriever once on startup
    try:
        get_retriever()
        print("🚀 Server is ready and model is loaded!")
    except Exception as e:
        print(f"⚠️ Error during pre-loading: {e}")
        
    app.run(debug=True, host="0.0.0.0", port=5000)
