# 🧠 Kernal Agent - AI Engine (The Brain)

> **Hackathon Track:** Gemini & Multimodality  
> **Role:** The Intelligence Layer (Vision, Reasoning, Planning)

This is the Python-based microservice that acts as the **"Brain"** for Kernal Agent. It uses FastAPI to host a low-latency WebSocket server that connects to the Desktop Client (C#). It leverages **Google Gemini 2.5 Flash Vision** to perceive the screen and generate executable automation plans using a "One-Shot Learning" approach.

---

## ⚡ Key Features

| Feature | Description |
|---------|-------------|
| **Real-time Vision Pipeline** | Processes incoming Base64 screenshots via WebSockets |
| **Gemini 2.5 Flash Integration** | Uses `gemini-2.5-flash` for state-of-the-art multimodal reasoning |
| **Structured Action Plans** | Returns strict JSON instructions (`CLICK`, `TYPE`, `WAIT`) rather than unstructured text |
| **Smart Rate Limiting** | Implements exponential backoff and image compression (1024px resizing) to handle API quotas gracefully |
| **Set-of-Mark (SoM) Logic** | Designed to interpret numbered UI tags for 100% accurate clicking |

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI (WebSockets)
- **AI Model:** Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Libraries:** `google-genai`, `Pillow` (Image Processing), `Pydantic` (Data Validation)

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- A [Google AI Studio](https://aistudio.google.com/) API Key

### 2. Installation

```bash
# Clone the repo and navigate to backend
cd Backend

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the `Backend/` root directory:

```env
# Your Google Gemini API Key
GEMINI_API_KEY=your_key_starts_with_AIza...
```

### 4. Running the Server

Start the "Nervous System" (WebSocket Server) on `localhost:8000`:

```bash
python -m app.main
```

You should see:
```
🧠 Starting Kernal Agent Brain...
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 5. Testing the Brain (Mock Client)

We have included a test script to verify the pipeline without needing the Desktop App. This script simulates a client sending a user intent and a dummy screenshot.

```bash
python tests/test_brain.py
```

---

## 📂 Project Structure

```
Backend/
├── app/
│   ├── main.py              # Application Entry Point & Server Config
│   ├── api/
│   │   └── websocket.py     # WebSocket Route (/ws/stream) handling
│   ├── engine/
│   │   └── vision.py        # Core Logic: Image processing & Gemini API calls
│   └── core/
│       ├── config.py        # Environment variables & Model settings
│       └── schemas.py       # Pydantic Data Models (KernalAction)
├── tests/
│   └── test_brain.py        # Standalone WebSocket client for testing
└── requirements.txt         # Python dependencies
```

---

## 🔌 API Contract (WebSocket)

The Brain listens on: `ws://localhost:8000/ws/stream`

### 1. Input Format (Client → Server)

**Set User Intent:**
```json
{
  "type": "intent_update",
  "payload": "Find the 'Export' button and click it."
}
```

**Send a Vision Frame:**
```json
{
  "type": "frame",
  "image": "BASE64_STRING_OF_SCREENSHOT..."
}
```

### 2. Output Format (Server → Client)

**Action Plan Response:**
```json
{
  "type": "action",
  "payload": {
    "explanation": "I identified the export icon in the top right.",
    "action_type": "CLICK",
    "coordinate_label": 42,
    "text_payload": null
  }
}
```

---

## 🏆 Why This Wins

- **Native OS Integration** — Not a browser extension, but a true desktop agent
- **Vision-First Architecture** — Uses pixels, not DOM, making it immune to UI changes
- **One-Shot Learning** — Watch once, automate forever
- **Enterprise-Grade Design** — Modular, scalable, production-ready

---

<p align="center">
  <b>Built for the Gemini Hackathon 🚀</b>
</p>