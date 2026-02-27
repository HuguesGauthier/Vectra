# Installation

Vectra can be deployed quickly via Docker (recommended) or manually for development.

## 🚀 Quick Start (Docker)

Get Vectra running in 2 minutes:

1. **Clone the project**:

   ```bash
   git clone https://github.com/HuguesGauthier/Vectra.git
   cd Vectra
   ```

2. **Configure environment**:

   **Linux / macOS / PowerShell:**

   ```bash
   cp .env.example .env
   ```

   **Windows (Command Prompt):**

   ```cmd
   copy .env.example .env
   ```

   _(Then edit the `.env` file to add your API keys)_

3. **Launch services**:
   ```bash
   docker compose --profile dev up -d
   ```

### 🚀 Hardware Acceleration (Optional)

By default, Vectra runs in **CPU-only mode** for maximum compatibility.

If you have an **NVIDIA GPU** and want to use it, you don't need to change your `.env`. Simply add the GPU extension file to your command:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile prod up -d
```

Access the UI at: [http://localhost:9000](http://localhost:9000)

### Data Persistence (Docker)

To allows Vectra to access your local files and folders in Docker:

1. Define the base path of your documents in your `.env`:
   ```env
   VECTRA_DATA_PATH=D:/MyDocuments
   ```
2. Any connector created with a path starting with `D:/MyDocuments` will be automatically mapped to the internal Docker `/data` volume.

---

## 🏗️ Environments Setup

Vectra supports multiple environments using Docker Compose profiles.

### 🛠️ Hybrid Development (Recommended)

This mode runs the **Infrastructure** (Postgres, Qdrant, Redis, Ollama) in Docker and your **Application code** locally for better performance and debugging.

1. **Launch Infrastructure**:
   ```bash
   # Launches databases, infra and dev tools (pgAdmin, Redis Commander)
   docker compose --profile dev up -d
   ```
2. **Launch Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```
3. **Launch Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### 🚀 Production (Full Docker)

This mode builds and runs everything inside optimized Docker containers. It doesn't rely on local code once built.

```bash
# Use --profile prod to include the application services
docker compose --profile prod up -d --build
```

- **Frontend**: http://localhost (Port 80)
- **Backend API**: http://localhost:8000

---

## 📜 License

Vectra is open-source software licensed under the **GNU AGPL v3**.

> [!IMPORTANT]
> The **AGPL v3** is a "strong copyleft" license. If you modify Vectra or use it to provide a service over a network, you must make your modified source code available to the users of that service.

### 💼 Commercial Use

If you wish to:

- **Integrate Vectra** into a proprietary software product.
- **Build a commercial SaaS** without releasing your own source code.
- **Benefit from Enterprise Support** and priority features.

You must purchase a **Commercial License**. Please [contact the author](mailto:hugues.gauthier@gmail.com) for enterprise pricing and licensing options.
