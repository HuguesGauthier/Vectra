# Installation

Vectra can be deployed quickly via Docker (recommended) or manually for development.

## 🚀 Quick Start (Docker)

The easiest way to launch Vectra in production or for a quick test.

1. **Clone the project**:

   ```bash
   git clone https://github.com/HuguesGauthier/Vectra.git
   cd Vectra
   ```

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit the .env file with your API keys (Gemini, etc.)
   ```

3. **Launch services**:
   ```bash
   docker-compose up -d
   ```

Access the UI at: [http://localhost:9000](http://localhost:9000)

---

## 🛠️ Manual Installation (Development)

If you wish to modify the code or contribute to the project.

### Prerequisites

- **Python 3.10+**
- **Node.js** (for the frontend)
- **Databases**: PostgreSQL, Qdrant, and Redis must be accessible.

### Backend

1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Launch the API:
   ```bash
   python main.py
   ```

### Frontend

1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Launch the development server:
   ```bash
   npm run dev
   ```
