# Smart Contract Discovery System

<div align="center">

*Pengembangan Smart Contract Discovery System Berbasis Konteks Semantik*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![Rust](https://img.shields.io/badge/Rust-2021-orange.svg)](https://www.rust-lang.org/)

**📝 Tugas Akhir - Institut Teknologi Bandung**  
*Kenneth Ezekiel Suprantoni (13521089)*

</div>

## 🎯 Overview

Smart Contract Discovery System adalah sistem pencarian Smart Contract berbasis semantik yang memungkinkan pengguna menemukan Smart Contract yang relevan menggunakan query dalam bahasa alami. Sistem ini memanfaatkan **Semantic Enrichment dengan Large Language Models (LLM)** untuk memberikan hasil pencarian yang lebih akurat dan kontekstual dibandingkan metode pencarian berbasis kata kunci tradisional.

### 🚀 Key Features

- **🧠 Semantic Search**: Pencarian berbasis makna menggunakan vector embeddings dan LLM
- **🔍 Natural Language Queries**: Mendukung pencarian dengan bahasa alami
- **📊 Smart Contract Analysis**: Analisis mendalam terhadap kode Smart Contract
- **🛡️ Security Insights**: Deteksi potensi risiko keamanan
- **🎨 Modern UI**: Interface yang user-friendly dengan Next.js dan Tailwind CSS
- **⚡ Real-time Search**: Pencarian cepat dengan caching dan optimisasi

## 🏗️ Architecture

Sistem ini terdiri dari beberapa komponen utama:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   Data Sources  │
│   (Next.js)     │◄──►│   (FastAPI)      │◄──►│   - DgraphDB    │
│                 │    │                  │    │   - ChromaDB    │
│   - Search UI   │    │   - Retriever    │    │   - Ethereum    │
│   - Results     │    │   - Enrichment   │    │     Archive     │
│   - Details     │    │   - Vector DB    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 🔧 Technology Stack

**Frontend:**
- Next.js 15 with App Router
- TypeScript
- Tailwind CSS + Radix UI
- React Hook Form

**Backend:**
- FastAPI (Python)
- LangChain for LLM integration
- OpenAI GPT models
- HuggingFace embeddings

**Databases:**
- DgraphDB (Graph database untuk Smart Contract data)
- ChromaDB (Vector database untuk semantic search)

**Data Extraction:**
- eth2dgraph (Rust) untuk ekstraksi data dari Ethereum
- Alchemy Archive Node sebagai data source

## 📁 Project Structure

```
tugas-akhir/
├── impl/                          # Implementation code
│   ├── eth2dgraph/               # Rust-based Ethereum data extractor
│   │   ├── src/                  # Rust source code
│   │   ├── Cargo.toml           # Rust dependencies
│   │   └── docker-compose.yml   # DgraphDB setup
│   ├── system/                   # Python backend system
│   │   ├── src/
│   │   │   ├── api/             # FastAPI endpoints
│   │   │   ├── core/            # Core business logic
│   │   │   │   ├── data_access/ # Database clients
│   │   │   │   ├── data_processing/ # LLM enrichment
│   │   │   │   └── data_retrieval/ # Search & retrieval
│   │   │   └── utils/           # Utility functions
│   │   ├── config/              # Configuration files
│   │   ├── requirements.txt     # Python dependencies
│   │   └── openapi.yaml         # API documentation
│   └── web/                      # Next.js frontend
│       ├── app/                 # App router pages
│       ├── components/          # React components
│       ├── hooks/               # Custom React hooks
│       ├── lib/                 # Utility libraries
│       └── package.json         # Node dependencies
└── src/                          # LaTeX thesis documentation
    ├── thesis.tex               # Main thesis document
    ├── chapters/                # Thesis chapters
    └── config/                  # LaTeX configuration
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- **Node.js 18+** 
- **Rust 2021 edition**
- **Docker & Docker Compose**
- **OpenAI API Key**

### 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/username/tugas-akhir.git
   cd tugas-akhir
   ```

2. **Setup DgraphDB (Data Storage)**
   ```bash
   cd impl/eth2dgraph
   docker-compose up -d
   ```

3. **Setup Backend System**
   ```bash
   cd impl/system
   pip install -r requirements.txt
   
   # Configure environment variables
   cp .env.example .env
   # Edit .env file with your API keys
   ```

4. **Setup Frontend**
   ```bash
   cd impl/web
   npm install
   ```

### 🏃‍♂️ Running the System

1. **Start the Backend API**
   ```bash
   cd impl/system
   python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend**
   ```bash
   cd impl/web
   npm run dev
   ```

3. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - DgraphDB UI (Ratel): http://localhost:8001

## 📖 Usage

### Basic Search
```
Query: "ERC20 token with mint and burn functions"
Results: Smart contracts that implement ERC20 standard with minting/burning capabilities
```

### Advanced Search
```
Query: "DeFi lending protocol with liquidation mechanism and oracle integration"
Results: Detailed analysis of DeFi contracts with specific functionalities
```

### API Usage
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "NFT marketplace with royalty system",
       "limit": 10,
       "data": true
     }'
```

## 🔬 Data Pipeline

1. **Extraction**: eth2dgraph extracts Smart Contract data from Ethereum Archive Node
2. **Storage**: Raw data stored in DgraphDB 
3. **Enrichment**: LLM processes contracts for semantic understanding
4. **Vectorization**: Embeddings create vector representations
5. **Search**: ChromaDB enables semantic similarity search

## 🧪 Testing

The system includes comprehensive testing methodologies:

- **Relevansi Hasil Pencarian (UK1)**: Accuracy measurement using labeled datasets
- **Kualitas Semantik Data (UK2)**: Semantic expressiveness evaluation  
- **Kemiripan Hasil (UK3)**: Semantic similarity scoring
- **Konsistensi Hasil (UK4)**: Jaccard Index for result consistency

## 📚 Research Publication

This work is part of the final thesis:
> **"Pengembangan Smart Contract Discovery System Berbasis Konteks Semantik"**  
> Kenneth Ezekiel Suprantoni (13521089)  
> Institut Teknologi Bandung, 2025

## 📧 Contact

**Kenneth Ezekiel Suprantoni**  
- Institution: Institut Teknologi Bandung
- Program: Teknik Informatika

---

<div align="center">
Made with ❤️ for the advancement of blockchain technology and semantic search
</div>
