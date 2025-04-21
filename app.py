from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import pickle
from redis import Redis
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma

# ====== Load environment variables ======
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# ====== Flask setup ======
app = Flask(__name__)
CORS(app)

# ====== Redis setup ======
redis_client = Redis(host='localhost', port=6379, decode_responses=False)

# ====== LangChain setup ======
CHROMA_PATH = "chroma"
embedding_function = OpenAIEmbeddings()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": 3})

llm = ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0)

# ====== Prompt Template ======
qa_prompt = PromptTemplate.from_template(
"""
You are a knowledgeable and friendly chatbot specializing in human trafficking awareness for teenagers, parents, and educators. Your role is to explain concepts clearly, compassionately, and informatively based on the provided documents.

Guidelines:
- Avoid copying text directly. Instead, rephrase, summarize, and logically expand upon the information provided.
- Do not introduce information that is not supported by the documents. Stay accurate and grounded.
- Do not bullet list the points, answer in paragraphs.
- If the user's question cannot be answered from the documents, reply exactly with:
  "INSUFFICIENT_CONTEXT: The available documents do not provide enough information to answer this question accurately."
- If the user's input is a casual greeting (like "hi", "hello", "thanks"), reply exactly with:
  "GENERIC_CONVERSATION: The user input is a greeting or casual statement, not a factual question."

Context:
{context}

Question: {question}
Answer:
"""
)

# ====== Routes ======

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/preview")
def preview():
    return render_template("preview.html")

@app.route("/chat", methods=["POST"])
def chat():
    print("🟢 Received a new POST request at /chat")

    user_message = request.json.get("message")
    user_id = request.json.get("user_id")

    if not user_message or not user_id:
        print("❌ Missing message or user_id")
        return jsonify({"error": "Message and user_id are required."}), 400

    print(f"📝 User {user_id} sent: {user_message}")

    # ==== Casual conversation handling ====
    casual_phrases = {"hi", "hello", "hey", "good morning", "good evening", "what's up", "yo", "hiya", "sup"}
    thank_you_phrases = {"thank you", "thanks", "thx", "ty", "thank you so much", "many thanks", "thanks a lot", "ok", "okay"}
    bye_phrases = {"bye", "goodbye", "see you", "take care", "good night", "gn"}

    normalized = user_message.lower().strip()

    if normalized in casual_phrases:
        print("👋 Detected casual greeting.")
        return jsonify({"response": "Hello! How can I assist you today? 😊", "sources": []})
    
    if normalized in thank_you_phrases:
        print("🙏 Thank you detected.")
        return jsonify({"response": "You're very welcome! 😊 Let me know if you have any more questions!", "sources": []})

    if normalized in bye_phrases:
        print("👋 Goodbye detected.")
        return jsonify({"response": "Goodbye! 👋 Stay safe and take care!", "sources": []})

    # ==== Load user memory ====
    memory_key = f"memory:{user_id}"
    memory_blob = redis_client.get(memory_key)

    if memory_blob:
        memory = pickle.loads(memory_blob)
        print(f"📦 Loaded memory for user {user_id}")
    else:
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="question",
            output_key="answer",
            return_messages=True
        )
        print(f"✨ Created new memory for user {user_id}")

    # ==== Expand very short queries ====
    if len(user_message.split()) <= 5:
        print("✍️ Expanding short query for better retrieval...")
        user_message = f"Provide a detailed explanation about: {user_message}. Include definitions, examples, and context."


    # ==== Create Conversation Chain ====
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": qa_prompt},
        output_key="answer"
    )

    # ==== Run RAG ====
    print("🔄 Running ConversationalRetrievalChain (RAG)...")
    result = conversation_chain.invoke({"question": user_message})
    response_text = result["answer"]
    source_docs = result.get("source_documents", [])

    print(f"✅ Response generated: {response_text}")

    # ==== Handle fallback cases ====
    if "GENERIC_CONVERSATION" in response_text:
        print("👋 Generic conversation detected.")
        return jsonify({"response": "Hello! How can I assist you today?", "sources": []})

    if "INSUFFICIENT_CONTEXT" in response_text:
        print("⚠️ Insufficient context detected — fallback triggered.")
        fallback_llm = ChatOpenAI()
        fallback_response = fallback_llm.invoke(
            f"You are a helpful chatbot for human trafficking awareness.\n\nUser: {user_message}\nAssistant:"
        )
        response_text = getattr(fallback_response, "content", str(fallback_response))

        # 🆕 Save fallback answer to memory
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(f"[Fallback] {response_text}")
        redis_client.set(memory_key, pickle.dumps(memory))
        print(f"💾 Memory updated with fallback for user {user_id}")

        return jsonify({
            "response": response_text,
            "sources": []
        })

    # ==== Save successful conversation ====
    redis_client.set(memory_key, pickle.dumps(memory))
    print(f"💾 Memory saved for user {user_id}")

    # ==== Extract sources for front-end ====
    sources = []
    for doc in source_docs:
        url = doc.metadata.get("url") or doc.metadata.get("source") or doc.metadata.get("filename")
        if url and url not in sources:
            print(f"🔎 Found source: {url}")
            sources.append(url)

    print("📤 Sending final response to client.")
    return jsonify({
        "response": response_text,
        "sources": sources
    })

# ====== Run the Server ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
