# ================= PATH FIX =================
import sys, os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

# ================= IMPORTS =================
import streamlit as st  # type: ignore
import json
import uuid
from datetime import datetime

# IMPORT YOUR BACKEND (UNCHANGED)
import backend.engine as engine

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Engineering Standards & Compliance Chatbot",
    layout="wide",
    page_icon="📘"
)

# ================= STORAGE =================
META_PATH = os.path.join("storage", "metadata.json")

def load_documents():
    if not os.path.exists(META_PATH):
        return []
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return sorted(set(m["document"] for m in meta if "document" in m))

# ================= SESSION STATE =================
if "page" not in st.session_state:
    st.session_state.page = "Chatbot"

if "documents" not in st.session_state:
    st.session_state.documents = load_documents()

if "mode" not in st.session_state:
    st.session_state.mode = "Auto"

if "active_document" not in st.session_state:
    st.session_state.active_document = "All Documents"

# ---- CHATGPT STYLE STATE ----
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# ================= STYLES =================
st.markdown("""
<style>
body { background-color: #f6f7fb; }

.chat-user {
    background: #2563eb;
    color: white;
    padding: 12px;
    border-radius: 12px;
    margin: 8px 0;
    text-align: right;
}

.chat-bot {
    background: white;
    padding: 14px;
    border-radius: 12px;
    margin: 8px 0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("## 📘 Compliance Bot")
    st.caption("Engineering Standards Assistant")
    st.divider()

    # ---- NAVIGATION ----
    if st.button("💬 Chatbot", use_container_width=True):
        st.session_state.page = "Chatbot"

    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.page = "Dashboard"

    if st.button("📂 Documents", use_container_width=True):
        st.session_state.page = "Documents"

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.page = "Settings"

    st.divider()

    # ---- NEW CHAT ----
    if st.button("➕ New Chat", use_container_width=True):
        chat_id = str(uuid.uuid4())
        st.session_state.chats[chat_id] = {
            "title": "New Chat",
            "messages": [],
            "created": datetime.now().strftime("%d %b %H:%M")
        }
        st.session_state.active_chat_id = chat_id
        st.session_state.page = "Chatbot"

    st.markdown("### 💬 Chat History")

    if not st.session_state.chats:
        st.caption("No chats yet.")
    else:
        for cid, chat in reversed(st.session_state.chats.items()):
            label = chat["title"]
            if st.button(label, key=f"chat_{cid}"):
                st.session_state.active_chat_id = cid
                st.session_state.page = "Chatbot"

    st.divider()

    # ---- UPLOAD ----
    st.markdown("### 📄 Upload PDF")
    uploaded = st.file_uploader("Drag & drop or browse PDF", type=["pdf"])

    if uploaded:
        with st.spinner("Indexing document..."):
            ok = engine.ingest_pdf(uploaded)

        if ok:
            if uploaded.name not in st.session_state.documents:
                st.session_state.documents.append(uploaded.name)
            st.success("Indexed successfully")
        else:
            st.error("No readable content found")

# ================= DASHBOARD =================
if st.session_state.page == "Dashboard":
    st.title("📊 Dashboard")
    c1, c2 = st.columns(2)
    c1.metric("📄 Documents", len(st.session_state.documents))
    c2.metric("💬 Chats", len(st.session_state.chats))

# ================= DOCUMENTS =================
elif st.session_state.page == "Documents":
    st.title("📂 Documents")
    for doc in st.session_state.documents:
        col1, col2 = st.columns([4, 1])
        col1.markdown(f"📄 **{doc}**")
        if col2.button("❌ Remove", key=f"remove_{doc}"):
            if engine.remove_document(doc):
                st.session_state.documents.remove(doc)
                st.success(f"{doc} removed")
                st.rerun()

# ================= SETTINGS =================
elif st.session_state.page == "Settings":
    st.title("⚙️ Settings")

    st.session_state.mode = st.radio(
        "Answer Style",
        ["Auto", "Strict", "Assist"],
        horizontal=True
    )

    st.divider()
    st.markdown("### 📄 Active Document Scope")

    docs = ["All Documents"] + st.session_state.documents
    st.session_state.active_document = st.selectbox(
        "Answer questions using:",
        docs
    )

# ================= CHATBOT =================
else:
    st.title("📘 Engineering Standards & Compliance Chatbot")

    if not st.session_state.active_chat_id:
        st.info("➕ Start a new chat from the sidebar.")
        st.stop()

    chat = st.session_state.chats[st.session_state.active_chat_id]

    # ---- SHOW HISTORY ----
    for msg in chat["messages"]:
        st.markdown(f"<div class='chat-user'>{msg['question']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chat-bot'>{msg['answer']}</div>", unsafe_allow_html=True)

        if msg["sources"]:
            with st.expander("📄 Sources"):
                for s in msg["sources"]:
                    st.markdown(f"- {s}")

    # ---- INPUT ----
    question = st.chat_input("Ask a standards / compliance question...")

    if question:
        with st.spinner("Analyzing document..."):
            answer, sources = engine.ask_question(
                question,
                st.session_state.mode,
                st.session_state.active_document
            )

        # ---- AUTO TITLE GENERATION ----
        if chat["title"] == "New Chat":
            chat["title"] = question[:40]

        chat["messages"].append({
            "question": question,
            "answer": answer,
            "sources": sources,
            "time": datetime.now().strftime("%H:%M")
        })

        st.rerun()
