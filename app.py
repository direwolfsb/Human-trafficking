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

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Flask setup
app = Flask(__name__)
CORS(app)

# Redis setup (use ElastiCache endpoint if on AWS)
redis_client = Redis(host='localhost', port=6379, decode_responses=False)

# Updated Prompt
qa_prompt = PromptTemplate.from_template(
"""
You are a knowledgeable and friendly chatbot specializing in human trafficking awareness for teenagers, parents, and educators. Your role is to explain concepts clearly, compassionately, and informatively based on the provided documents.

Guidelines:
- Avoid copying text directly. Instead, rephrase, summarize, and logically expand upon the information provided.
- Do not introduce information that is not supported by the documents. Stay accurate and grounded.
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


# LangChain setup
CHROMA_PATH = "chroma"
embedding_function = OpenAIEmbeddings()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": 3})

llm = ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/preview")
def preview():
    return render_template("preview.html")

@app.route("/chat", methods=["POST"])
def chat():


    print("🟢 Received a new POST request at /chat")
    # Step 0: Check for casual greetings before anything
   

    user_message = request.json.get("message")
    user_id = request.json.get("user_id")  # 📌 User must send user_id!

    casual_phrases = ["hi", "hello", "hey", "good morning", "good evening","what's up" "yo", "hiya", "sup"]

    normalized = user_message.lower().strip()

    if normalized in casual_phrases:
        print("👋 Detected simple casual greeting — skipping RAG completely!")
        return jsonify({
            "response": "Hello! How can I assist you today? 😊",
            "sources": []
        })
    thank_you_phrases = ["thank you", "thanks", "thx", "ty", "thank you so much", "many thanks", "thanks a lot", "ok", "okay"] 
    bye_phrases = ["bye", "goodbye", "see you", "take care", "good night", "gn"]

    if normalized in thank_you_phrases:
        print("🎉 Thank you detected — sending appreciation response.")
        return jsonify({
            "response": "You're very welcome! 😊 Let me know if you have any more questions!",
            "sources": []
        })

    if normalized in bye_phrases:
        print("👋 Goodbye detected — sending farewell response.")
        return jsonify({
            "response": "Goodbye! 👋 Stay safe and take care. If you need more information later, I'm always here!",
            "sources": []
        })
    if not user_message or not user_id:
        print("❌ Missing message or user_id")
        return jsonify({"error": "Message and user_id are required."}), 400

    print(f"📝 User {user_id} sent: {user_message}")

    # Load memory from Redis
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
        print(f"✨ New memory created for user {user_id}")

    # Create Conversational RAG chain
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": qa_prompt},
        output_key="answer"
    )

    # Step 1: Run RAG
    print("🔄 Running ConversationalRetrievalChain (RAG)...")
    result = conversation_chain.invoke({"question": user_message})
    response_text = result["answer"]
    source_docs = result.get("source_documents", [])

    print(f"✅ Response: {response_text}")

    # Step 2: Save updated memory back to Redis
    redis_client.set(memory_key, pickle.dumps(memory))
    print(f"💾 Memory saved for user {user_id}")

    # Step 3: Handle greetings and insufficient context
    if "GENERIC_CONVERSATION" in response_text:
        print("👋 Generic conversation detected")
        return jsonify({
            "response": "Hello! How can I assist you today?",
            "sources": []
        })

    if "INSUFFICIENT_CONTEXT" in response_text:
        print("⚠️ Insufficient context detected — fallback triggered")
        fallback_llm = ChatOpenAI()
        fallback_response = fallback_llm.invoke(
            f"You are a helpful chatbot for human trafficking awareness.\n\nUser: {user_message}\nAssistant:"
        )
        response_text = getattr(fallback_response, "content", str(fallback_response))
        return jsonify({
            "response": response_text,
            "sources": []
        })

    # Step 4: Extract sources
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

# Run the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
