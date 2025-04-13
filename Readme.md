# Human Trafficking RAG Model

## Overview
This project implements a Retrieval-Augmented Generation (RAG) model for answering questions about human trafficking based on a curated knowledge base. The model leverages OpenAI's embeddings and ChromaDB for efficient information retrieval and response generation.

## Data Sources
The knowledge base includes five impactful stories from the UNODC site, covering various aspects of human trafficking:
1. **A childhood of exploitation, violence and fear: the story of child trafficking** (July 2024)
2. **Mexico: Indigenous communities as agents of change in the eradication of human trafficking** (October 2024)
3. **Speaking up for survivors of human trafficking: Victoria Nyanjura’s story** (July 2024)
4. **Understanding Child Trafficking** (July 2024)
5. **Eight Latin American countries fighting human trafficking together** (April 2024)

## General Questions Handled
The model is trained to answer critical questions, such as:
- What is human trafficking, and how does it affect victims?
- What are the most common forms of human trafficking?
- How does human trafficking impact children differently from adults?
- What are the signs that someone might be a victim of human trafficking?
- What role do governments and organizations play in combating human trafficking?

## Project Structure
The system consists of two main components:

### Part 1: Processing and Storing PDF Documents in Chroma
#### `create_db.py`
This script processes PDF files, extracts text, splits it into chunks, and stores them in ChromaDB.

1. **Loading Environment Variables**
   - Loads the OpenAI API key from `.env`.
2. **Defining Paths**
   - `DATA_PATH`: Directory containing the PDF reports.
   - `CHROMA_PATH`: Directory where the processed data is stored.
3. **Extracting Text from PDFs**
   - Uses `PyPDF2` to extract text from each page.
   - Stores extracted text in a `langchain.schema.Document` object.
4. **Splitting Extracted Text**
   - Uses `RecursiveCharacterTextSplitter` to split text into chunks:
     - `chunk_size=300`
     - `chunk_overlap=100`
5. **Storing Data in ChromaDB**
   - Clears old data if it exists.
   - Converts text chunks into vector embeddings using OpenAI embeddings.
   - Saves the database persistently.

### Part 2: Querying Chroma Database (RAG Model)
#### `query_db.py`
This script enables querying stored knowledge using a command-line interface (CLI).

1. **Setting Up Environment Variables**
   - Loads the OpenAI API key.
2. **Defining Chroma Database Path**
   - Specifies `CHROMA_PATH` for stored embeddings.
3. **Creating a Query Prompt**
   - Uses a structured template to ensure responses are based only on retrieved context.
4. **Command-Line Querying**
   - Allows users to input queries via the CLI.
   - Example usage:
     ```bash
     python query_db.py "What is human trafficking?"
     ```
5. **Retrieving Relevant Context**
   - Uses `similarity_search_with_relevance_scores(query_text, k=3)` to retrieve the top 3 most relevant document chunks.
6. **Filtering Out Irrelevant Results**
   - If no relevant results are found or the highest similarity score is below `0.7`, the query is discarded.
7. **Formatting Retrieved Context for Query**
   - Structures the retrieved text before passing it to the model.
8. **Using OpenAI Chat Model for Answering Queries**
   - Passes the structured query to OpenAI's `ChatOpenAI()` model.
9. **Displaying the Response**
   - Prints the model's response in a readable format.

## Installation and Usage
### Prerequisites
- Python 3.8+
- OpenAI API Key
- Required libraries: `langchain`, `chromadb`, `PyPDF2`, `openai`, `dotenv`

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/human-trafficking-rag.git
   cd human-trafficking-rag
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file and add:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```
4. Run the database creation script:
   ```bash
   python create_db.py
   ```
5. Query the database:
   ```bash
   python query_db.py "What is human trafficking?"
   ```

## Future Enhancements
- Expanding the dataset with more case studies and research papers.
- Integrating a web-based interface for user-friendly interaction.
- Enhancing search efficiency with more advanced embeddings.
- Adding multilingual support to reach a broader audience.

## License
This project is licensed under the MIT License.

## Acknowledgments
- UNODC for the case studies and information sources.
- OpenAI for providing the embedding and chat models.
- The open-source community for contributing to NLP advancements.

