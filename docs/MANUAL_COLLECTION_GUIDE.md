# Manual Discord Data Collection and Fine-Tuning Guide

This guide walks you through the process of manually collecting your Discord messages and using them to fine-tune your AI clone.

## Step 1: Collect Your Messages

### Option A: Copy-Paste from Discord

1. Open Discord and navigate to your DMs or channels
2. Copy several message exchanges (your messages and the messages you were responding to)
3. Paste them into a text file in this format:

```
Friend: Hey, how's it going?
You: not much, just working on this ai project
Friend: That sounds cool! What does it do?
You: it's a discord bot that learns to talk like me
```

4. Save the file as `discord_conversations.txt`

### Option B: Use the Sample Data

We've provided a sample conversation in `sample_conversation.txt` that you can edit with your own messages.

## Step 2: Convert to Training Format

Run the conversion script to transform your conversations into the format needed for fine-tuning:

```bash
python convert_messages.py discord_conversations.txt
```

This will create two files:
- `training_data_TIMESTAMP.json` - The JSONL file for fine-tuning
- `training_data_TIMESTAMP_raw.json` - The raw message data

## Step 3: Prepare Training Data

Split your data into training, validation, and testing sets:

```bash
python prepare_training_data.py training_data_TIMESTAMP_raw.json shaco_manual --min-tokens 5
```

This will create three files:
- `shaco_manual_train.jsonl` - Training data
- `shaco_manual_val.jsonl` - Validation data
- `shaco_manual_test.jsonl` - Testing data

## Step 4: Fine-Tune the Model

Use the OpenAI API to fine-tune a GPT-4 model with your data:

```bash
python finetune_model.py shaco_manual_train.jsonl --validation-file shaco_manual_val.jsonl
```

This process may take several hours to complete. The script will periodically check the status of your fine-tuning job.

## Step 5: Test Your Fine-Tuned Model

Once fine-tuning is complete, test your model:

```bash
python test_fine_tuned.py
```

Enter prompts to see how your AI clone responds!

## Tips for Better Results

1. **Collect diverse conversations** - Include a variety of topics and response styles
2. **Include context** - Make sure to include the messages you were responding to
3. **Aim for at least 50-100 examples** - More data generally leads to better results
4. **Review your data** - Make sure it accurately represents how you communicate

## Troubleshooting

- **API Key Issues**: Make sure your OpenAI API key is set in the `.env` file
- **File Format Errors**: Check that your conversation format follows the example exactly
- **Fine-Tuning Errors**: Check the OpenAI documentation for specific error messages

## Next Steps

After successfully fine-tuning your model, you can:

1. Deploy it as a Discord bot
2. Collect more data to improve its responses
3. Experiment with different system prompts to guide its behavior
