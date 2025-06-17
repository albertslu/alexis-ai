# Alexis AI - Your Personal AI Assistant

Alexis AI is a web application that learns your communication style through natural conversation, then creates a personalized AI assistant that mimics how you talk. This project uses OpenAI's GPT-4 to analyze and replicate your unique communication patterns.

## Features

- Natural conversational training - just chat normally with Alexis
- Automatic communication style analysis (formality, verbosity, emoji usage, punctuation, capitalization)
- Seamless transition from training to personalized responses
- Real-time chat with your AI assistant that responds just like you would
- Modern, responsive web interface
- Conversation history tracking
- Integration with LinkedIn data to enhance professional context

## Project Structure

- **Frontend**: React-based UI for training and chatting with Alexis
- **Backend**: Flask API that handles training data and OpenAI integration
- **Scripts**: Utilities for data collection and model fine-tuning
- **RAG**: Retrieval Augmented Generation system for enhanced responses
  - **SimpleDataRepository**: Stores and retrieves messages from various sources

## Quick Start

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python app.py
```

## Environment Variables

Create a `.env` file in the root directory with:

```
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
AI_MODEL=gpt-4o-mini-2024-07-18
```

## Development Roadmap

- [x] Interactive training interface
- [x] Basic communication style analysis
- [x] Real-time chat with Alexis AI
- [x] Simple data repository for message storage
- [ ] Message data import from platforms
- [ ] RAG system for enhanced contextual responses
- [ ] Advanced style analysis
- [ ] Mobile app version

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Project Structure

- `backend/` - Core backend components
  - `config.py` - Configuration loading and validation
  - `ai_service.py` - OpenAI integration
- `data/` - Raw and processed data
  - `chat_history.json` - Conversation history for training
  - `training_data.json` - Processed training data
- `models/` - Fine-tuned models and training files
  - `improved_training_data.jsonl` - Enhanced training examples
- `utils/` - Utility functions and helpers
  - `prepare_user_training_data.py` - Prepares user data for fine-tuning
  - `linkedin_integration.py` - Integrates LinkedIn profile data
- `app.py` - Main entry point for the web application

## Collecting Your Training Data

### Interactive Chat Collection

The primary method for collecting training data is through the interactive chat interface:

1. Chat with Alexis naturally through the training interface
2. Your responses are automatically saved to the training data
3. The system analyzes your writing style and communication patterns

### LinkedIn Integration

You can enhance Alexis with professional context:

1. Connect your LinkedIn profile during setup
2. Professional details are integrated into the training data
3. Alexis learns to respond appropriately to professional questions

## Fine-tuning Your Model

1. Prepare the training data:
```bash
python utils/prepare_user_training_data.py data/chat_history.json models/clone
```

2. Fine-tune a model with OpenAI:
```bash
python scripts/finetune_model.py models/clone_train.jsonl --validation-file models/clone_val.jsonl
```

3. Test your fine-tuned model in the web interface

4. Update your `.env` file with the new model ID

## Key Improvements

The latest version includes significant improvements to the training process:

1. **Enhanced System Prompt**: Clear instructions to generate original responses in your style

2. **Natural Response Generation**: Prevents verbatim copying of LinkedIn data or previous messages

3. **Improved Training Examples**: Better examples that capture your communication style

4. **Style Analysis**: Automatically detects your writing patterns including punctuation, capitalization, and expression style

5. **Retrieval Augmented Generation (RAG)**: Working on implementing a RAG system that retrieves relevant past messages to provide better context for responses

6. **SimpleDataRepository**: A lightweight repository for storing and retrieving messages from various sources (Discord, LinkedIn, iMessage) without external dependencies

## Requirements

- Python 3.8+
- OpenAI API Access
- Web browser for the training interface
# Updated for Hackathon - Alexis AI Personal Assistant
