# AI Clone Training Data Scripts

This directory contains scripts for preparing training data for the AI clone project.

## Create Combined Training Data

The `create_combined_training_data.py` script generates a combined JSONL dataset that includes both text messages and emails with proper channel markers. This allows training a single model that can handle both communication channels while maintaining the user's unique personality.

### Features:

- Processes both email and text message data
- Adds clear channel markers in system messages
- Creates a balanced dataset with examples from both channels
- Automatically splits data into training and validation sets
- Preserves the user's unique communication style for each channel

### Usage:

```bash
cd scripts
python create_combined_training_data.py
```

### Output:

The script generates three files in the `models` directory:
- `combined_channel_model.jsonl`: The complete dataset
- `combined_channel_model_train.jsonl`: Training split (90%)
- `combined_channel_model_val.jsonl`: Validation split (10%)

### Fine-tuning:

After generating the JSONL files, you can fine-tune your model using:

```bash
openai api fine_tunes.create -t models/combined_channel_model_train.jsonl -v models/combined_channel_model_val.jsonl -m gpt-4o-mini
```

## Channel-Specific System Messages

The script uses different system messages for each channel:

### Text Messages:
```
You are an AI clone that responds to messages as if you were the user. 
The following is a text message conversation. Respond in the user's texting style, 
which is typically casual with minimal capitalization and punctuation.
```

### Emails:
```
You are an AI clone that responds to messages as if you were the user. 
The following is an email conversation. Respond in the user's email style, 
which is typically more formal and structured than text messages.
```

This helps the model distinguish between the two communication channels and adapt its response style accordingly.
