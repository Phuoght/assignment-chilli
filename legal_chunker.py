import os
import re
import json
import time
from pathlib import Path
from tqdm import tqdm

import numpy as np
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
INPUT_DIR   = "./docs/law_VN"
OUTPUT_DIR  = "./vectorstore"
INDEX_NAME  = "law"
JSONL_PATH  = "chunks.jsonl"
EMBED_MODEL = "BAAI/bge-m3"

CHUNK_MAX = 600
OVERLAP   = 80

# Pattern pháp lý Việt Nam (Cải tiến sâu)
RE_LAW_NAME = re.compile(r"(LUẬT|BỘ LUẬT|NGHỊ ĐỊNH|THÔNG TƯ|VĂN BẢN HỢP NHẤT)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỹ\s\n]+?)(?=\n\s*\n|Luật số|Căn cứ|\n[a-z])", re.I | re.M)
RE_YEAR     = re.compile(r"(\d{4})/(QH|VBHN|ND-CP|TT-)", re.I)
RE_YEAR_ALT = re.compile(r"năm\s+(\d{4})", re.I)
RE_CHAPTER  = re.compile(r"Chương\s+([IVXLCDM\d]+)", re.I)
RE_ARTICLE  = re.compile(r"^Điều\s+(\d+)", re.I | re.M)
RE_CLAUSE   = re.compile(r"^(Khoản\s+\d+|[a-z]\)\s+|[0-9]+\.\s+)", re.I | re.M)
RE_NOTE      = re.compile(r"^\[(\d+)\]", re.M)
RE_EFFECTIVE = re.compile(r"có hiệu lực (kể )?từ ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.I)
RE_EFFECTIVE_ALT = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")

def clean_text(text):
    if not text: return "N/A"
    # Loại bỏ dấu xuống dòng và khoảng trắng thừa
    text = text.replace('\n', ' ')
    return re.sub(r'\s+', ' ', text).strip()

# ─────────────────────────────────────────────────────────────
# DOC READER (Windows Optimized)
# ─────────────────────────────────────────────────────────────
def read_doc_file(file_path):
    """Đọc file .doc bằng win32com (Yêu cầu cài Word) hoặc fallback unstructured"""
    ext = file_path.suffix.lower()
    
    if ext == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(str(file_path))
        return "\n".join([d.page_content for d in loader.load()])
    
    # Thử dùng win32com cho .doc (Tốt nhất trên Windows)
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(file_path.absolute()))
        text = doc.Content.Text
        # Convert Word special chars
        text = text.replace('\r', '\n').replace('\x07', '') 
        doc.Close()
        # word.Quit() # Đừng quit nếu còn xử lý tiếp, hoặc quit ở ngoài
        return text
    except Exception as e:
        print(f"⚠️ win32com failed for {file_path.name}: {e}. Trying unstructured...")
        try:
            from langchain_community.document_loaders import UnstructuredWordDocumentLoader
            loader = UnstructuredWordDocumentLoader(str(file_path))
            return "\n".join([d.page_content for d in loader.load()])
        except Exception as e2:
            print(f"❌ Unstructured cũng thất bại: {e2}")
            return ""

# ─────────────────────────────────────────────────────────────
# CHUNKER AGENT
# ─────────────────────────────────────────────────────────────
class LegalChunkerAgent:
    def __init__(self):
        print(f"🚀 Khởi tạo Legal-Chunker-Agent với model: {EMBED_MODEL}")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    def get_token_count(self, text):
        return len(text.split()) * 1.3 

    def process_file(self, file_path, word_app=None):
        print(f"📄 Đang xử lý: {file_path.name}")
        
        # Đọc text
        if file_path.suffix.lower() == ".doc" and word_app:
            try:
                doc = word_app.Documents.Open(str(file_path.absolute()))
                full_text = doc.Content.Text.replace('\r', '\n').replace('\x07', '')
                doc.Close()
            except:
                full_text = read_doc_file(file_path)
        else:
            full_text = read_doc_file(file_path)
            
        if not full_text.strip():
            return []

        # Trích xuất metadata chung
        header_text = "\n".join(full_text.split("\n")[:20])
        law_match = RE_LAW_NAME.search(header_text)
        law_name = clean_text(law_match.group(0)) if law_match else file_path.stem.replace('-', ' ')
        
        # Tìm năm
        year_match = RE_YEAR.search(full_text) or RE_YEAR_ALT.search(law_name)
        year = year_match.group(1) if year_match else "N/A"
        
        # Tìm ngày hiệu lực
        eff_match = RE_EFFECTIVE.search(full_text)
        if eff_match:
            d, m, y = eff_match.group(2), eff_match.group(3), eff_match.group(4)
            effective_date = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
        else:
            eff_alt = RE_EFFECTIVE_ALT.search(full_text)
            effective_date = eff_alt.group(1) if eff_alt else "N/A"

        # 2. Tách theo Điều
        art_splits = re.split(r"(?=\nĐiều\s+\d+)", "\n" + full_text)
        
        current_chapter = "N/A"
        chunks = []
        
        for art_block in art_splits:
            art_block = art_block.strip()
            if not art_block: continue
            
            # Cập nhật Chương hiện tại
            chap_match = RE_CHAPTER.search(art_block)
            if chap_match: current_chapter = f"Chương {chap_match.group(1)}"
            
            # Lấy số hiệu Điều
            art_match = RE_ARTICLE.search(art_block)
            art_num = f"Điều {art_match.group(1)}" if art_match else "N/A"
            
            # 3. Tách theo Khoản/Ghi chú
            cl_splits = re.split(r"(?=\n(?:Khoản\s+\d+|[0-9]+\.\s+|[a-z]\)\s+|\[\d+\]))", "\n" + art_block)
            
            for cl_block in cl_splits:
                cl_text = cl_block.strip()
                if not cl_text: continue
                
                # Phân loại block
                is_note = RE_NOTE.match(cl_text)
                if is_note:
                    display_art = f"{art_num} (Ghi chú)"
                    cl_num = f"Ghi chú {is_note.group(1)}"
                else:
                    display_art = art_num
                    cl_match = RE_CLAUSE.search(cl_text)
                    cl_num = cl_match.group(0).strip() if cl_match else "Toàn văn"

                # 4. Chunking theo độ dài
                if len(cl_text) > CHUNK_MAX:
                    step = CHUNK_MAX - OVERLAP
                    for i in range(0, len(cl_text), step):
                        sub = cl_text[i : i + CHUNK_MAX]
                        chunks.append(self.create_chunk(
                            text=sub, law=law_name, year=year, chap=current_chapter,
                            art=display_art, clause=f"{cl_num} (Phần {i//step + 1})",
                            eff=effective_date, src=file_path.name
                        ))
                else:
                    chunks.append(self.create_chunk(
                        text=cl_text, law=law_name, year=year, chap=current_chapter,
                        art=display_art, clause=cl_num, eff=effective_date, src=file_path.name
                    ))
        return chunks

    def create_chunk(self, text, law, year, chap, art, clause, eff, src, chunk_id=0):
        header = f"[{law}] [{year}], [{chap}], [{art}], [{clause}], hiệu lực: [{eff}]\n"
        full_text = header + text
        metadata = {
            "law_name": clean_text(law),
            "year": clean_text(year),
            "chapter": clean_text(chap),
            "article": clean_text(art),
            "clause": clean_text(clause),
            "effective_date": clean_text(eff),
            "source": src,
            "file": src, # Đồng bộ với app.py
            "chunk_id": chunk_id
        }
        return {"text": full_text, "metadata": metadata, "source_file": src}

    def run(self):
        all_chunks = []
        path = Path(INPUT_DIR)
        # Lọc danh sách file hợp lệ (bỏ file tạm ~$ và chỉ lấy .doc/.docx)
        law_files = [
            f for f in path.glob("*.*") 
            if f.suffix.lower() in [".doc", ".docx"] and not f.name.startswith("~$")
        ]
        
        if not law_files:
            print(f"❌ Không tìm thấy file trong {INPUT_DIR}")
            return

        # Khởi tạo Word một lần duy nhất để tối ưu
        word_app = None
        try:
            import win32com.client
            word_app = win32com.client.Dispatch("Word.Application")
            word_app.Visible = False
        except:
            print("⚠️ Không thể khởi tạo Word. Sẽ dùng fallback.")

        for f in tqdm(law_files, desc="Processing Laws"):
            try:
                file_chunks = self.process_file(f, word_app)
                # Gán ID cho từng chunk
                for i, c in enumerate(file_chunks):
                    c['metadata']['chunk_id'] = len(all_chunks) + i
                all_chunks.extend(file_chunks)
            except Exception as e:
                print(f"❌ Lỗi {f.name}: {e}")

        if word_app:
            word_app.Quit()

        if not all_chunks:
            print("❌ Không có dữ liệu để index!")
            return

        # Xuất JSONL
        with open(JSONL_PATH, 'w', encoding='utf-8') as f:
            for c in all_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        # Lưu Vector Store
        print(f"🧠 Đang tạo index cho {len(all_chunks)} chunks...")
        docs = [Document(page_content=c['text'], metadata=c['metadata']) for c in all_chunks]
        vectorstore = FAISS.from_documents(docs, self.embeddings)
        
        if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        vectorstore.save_local(OUTPUT_DIR, index_name=INDEX_NAME)
        print(f"✅ Hoàn tất! Index tại {OUTPUT_DIR}/{INDEX_NAME}")

if __name__ == "__main__":
    LegalChunkerAgent().run()
