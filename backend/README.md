# EVUA Backend

A FastAPI-based backend service for the EVUA project that provides LLM integration, code parsing, and chat functionality.

## Features

- **LLM Integration**: Support for Ollama models
- **Code Parsing**: Multi-language code analysis (Python, JavaScript, Java)
- **Chat API**: RESTful endpoints for conversational AI
- **Database Support**: MongoDB integration for data persistence
- **History Management**: Conversation history tracking

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- MongoDB (optional, for database features)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd EVUA/backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   Create a `.env` file in the backend directory (see Environment Configuration below).

6. **Start Ollama (if not running):**
   ```bash
   ollama serve
   ```

7. **Pull required models:**
   ```bash
   ollama pull opencoder:1.5b
   # or any other model you prefer
   ```

## Environment Configuration

Create a `.env` file in the backend directory with the following variables:

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=opencoder:1.5b

# Database Configuration (Optional)
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=evua_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Environment Variables Explained

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` | Yes |
| `DEFAULT_MODEL` | Default LLM model to use | `opencoder:1.5b` | Yes |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` | No |
| `DATABASE_NAME` | Database name | `evua_db` | No |
| `API_HOST` | FastAPI host | `0.0.0.0` | No |
| `API_PORT` | FastAPI port | `8000` | No |
| `DEBUG` | Enable debug mode | `True` | No |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` | No |

## Running the Application

1. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

2. **Access the API:**
   - API Base URL: `http://localhost:8000`
   - Interactive API Docs: `http://localhost:8000/docs`
   - OpenAPI Schema: `http://localhost:8000/openapi.json`

## API Endpoints

### Chat Endpoints

- `POST /api/chat` - Send a chat message to the LLM
- `GET /api/models` - Get available Ollama models

### Health Check

- `GET /health` - Application health status

## Project Structure

```
backend/
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── setup.py            # Package configuration
├── .env                # Environment variables (create this)
├── README.md           # This file
├── chat/               # Chat-related modules
├── config/             # Configuration files
├── core/               # Core parsing functionality
│   ├── parser.py       # Main parser interface
│   ├── pyParser.py     # Python code parser
│   ├── javaParser.py   # Java code parser
│   └── jsParser.mjs    # JavaScript parser
├── db/                 # Database modules
├── llm/                # LLM integration
│   ├── models.py       # Model management
│   ├── prompts.py      # Prompt templates
│   └── fallback.py     # Fallback handlers
├── schemas/            # Pydantic schemas
├── services/           # Business logic services
│   ├── llm_service.py  # LLM service layer
│   ├── db_service.py   # Database service
│   └── history_Manager.py # History management
├── tests/              # Test files
└── utils/              # Utility functions
```

## Development

### Running Tests

```bash
# Run specific test files
python tests/ollamatest.py
python tests/Mongodbtest.py
```

### Code Formatting

Make sure to follow Python coding standards:

```bash
# Install development dependencies
pip install black flake8 isort

# Format code
black .
isort .

# Check code quality
flake8 .
```

## Troubleshooting

### Common Issues

1. **"Invalid URL 'None'" Error:**
   - Ensure `OLLAMA_HOST` is set in your `.env` file
   - Verify Ollama is running: `curl http://localhost:11434/api/version`

2. **Model Not Found:**
   - Check available models: `ollama list`
   - Pull required model: `ollama pull <model-name>`

3. **CORS Issues:**
   - Update `ALLOWED_ORIGINS` in `.env` to include your frontend URL

4. **Port Already in Use:**
   - Change `API_PORT` in `.env` or kill the process using the port

### Logs

Check application logs for detailed error information when running with `--reload` flag.

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests if applicable
4. Ensure all tests pass
5. Submit a pull request