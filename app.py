from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os

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

# Prompt for retrieval-augmented generation
qa_prompt = PromptTemplate.from_template(
"""
You are a professional legal assistant chatbot specializing in human trafficking cases. Be concise, factual, and professional.

Answer the user's question using ONLY the context provided below. Do not make up information. Answer in paragraphs.

If the context does not support the question, reply with: "INSUFFICIENT_CONTEXT: The available documents do not provide enough information to answer this question accurately."

Context:
{context}

Question: {question}
Answer:
""")

# LangChain setup
CHROMA_PATH = "chroma"
embedding_function = OpenAIEmbeddings()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
retriever = db.as_retriever(search_kwargs={"k": 3})

llm = ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    input_key="question",
    output_key="answer",
    return_messages=True
)

fallback_memory = ConversationBufferMemory(return_messages=True)

conversation_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    return_source_documents=True,
    combine_docs_chain_kwargs={"prompt": qa_prompt},
    output_key="answer"
)

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
    if not user_message:
        print("❌ No message received in request body")
        return jsonify({"error": "Message is required."}), 400

    print(f"📝 User message: {user_message}")

    # Step 1: Run RAG directly
    print("🔄 Running ConversationalRetrievalChain (RAG) with LangChain...")
    result = conversation_chain.invoke({"question": user_message})
    response_text = result["answer"]
    source_docs = result.get("source_documents", [])

    print("✅ RAG response received:")
    print(response_text)

    # Step 2: Check for hallucination or vague answer
    print("🔍 Checking response for trigger words indicating hallucination or insufficient context...")
    fallback_trigger_phrases = [
        "The provided context does not include",
        "The provided context does not specifically",
        "If you require information",
        "No relevant information",
        "Do not make up information",
        "INSUFFICIENT_CONTEXT"
    ]
    should_fallback = any(trigger.lower() in response_text.lower() for trigger in fallback_trigger_phrases)

    if should_fallback:
        print("⚠️ RAG response appears vague or hallucinated — activating fallback to ChatGPT")

        fallback_llm = ChatOpenAI()
        fallback_memory.chat_memory.add_user_message(user_message)

        chat_history = fallback_memory.chat_memory.messages
        fallback_prompt = "You are a helpful chatbot for human trafficking awareness. Be accurate, compassionate, and informative.\n\n"
        for msg in chat_history:
            role = "User" if msg.type == "human" else "Assistant"
            fallback_prompt += f"{role}: {msg.content}\n"
        fallback_prompt += "Assistant:"

        print("🧠 Sending fallback prompt to ChatGPT...")
        fallback_response = fallback_llm.invoke(fallback_prompt)
        response_text = getattr(fallback_response, "content", str(fallback_response))
        fallback_memory.chat_memory.add_ai_message(response_text)

        print("✅ Fallback response generated.")
        return jsonify({
            "response": response_text,
            "sources": []
        })

    # ✅ Step 3: Extract source URLs
    print("🔗 Extracting source document URLs...")
    sources = []
    for doc in source_docs:
        url = doc.metadata.get("url")
        if url and url not in sources:
            print(f"🔎 Found source: {url}")
            sources.append(url)

    print("📤 Sending final response back to client.")
    return jsonify({
        "response": response_text,
        "sources": sources
    })

if __name__ == "__main__":
    app.run(debug=True)
