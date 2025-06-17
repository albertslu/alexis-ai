# Fine-Tuning Guide for AI Clone

This guide will walk you through the process of fine-tuning your AI clone with your Discord message history.

## Prerequisites

- Discord Bot Token with Message Content Intent enabled
- OpenAI API Key
- Your Discord User ID
- Discord Guild (Server) IDs where your messages are located

## Step 1: Collect Your Discord Message History

First, collect your message history from Discord:

```bash
python collect_discord_data.py
```

This will:
- Connect to Discord using your bot token
- Collect your messages from the specified servers
- Save them to JSON and CSV files with a timestamp

## Step 2: Prepare Training Data

Next, prepare your data for fine-tuning by splitting it into training, validation, and testing sets:

```bash
python prepare_training_data.py discord_messages_TIMESTAMP.json shaco_data
```

This will:
- Filter your messages based on length and content
- Format them for GPT fine-tuning
- Split them into three files:
  - `shaco_data_train.jsonl` (80% of data)
  - `shaco_data_val.jsonl` (10% of data)
  - `shaco_data_test.jsonl` (10% of data)

## Step 3: Fine-Tune the Model

Now, fine-tune the model using your training data:

```bash
python finetune_model.py shaco_data_train.jsonl --validation-file shaco_data_val.jsonl
```

This will:
- Upload your training and validation files to OpenAI
- Create a fine-tuning job using GPT-4 Turbo
- Monitor the job until completion
- Save the fine-tuned model ID to a file

## Step 4: Update Your Configuration

Once fine-tuning is complete, update your `.env` file with the new model ID:

```
AI_MODEL=ft:gpt-4-turbo-XXXX
```

Replace `ft:gpt-4-turbo-XXXX` with your actual fine-tuned model ID.

## Step 5: Test Your Fine-Tuned Model

Test your fine-tuned model to see if it sounds more like you:

```bash
python test_response.py
```

Enter different messages and see how your AI clone responds. The responses should now match your communication style more closely.

## Step 6: Deploy Your AI Clone

Once you're satisfied with the fine-tuned model, you can deploy your AI clone:

```bash
python run.py
```

## Tips for Better Fine-Tuning

1. **More Data = Better Results**: The more message history you provide, the better the model will learn your style.

2. **Quality Over Quantity**: Focus on meaningful conversations rather than short, generic messages.

3. **Regular Updates**: Fine-tune your model periodically as you accumulate more message history.

4. **Adjust System Prompt**: If needed, modify the system prompt in `prepare_training_data.py` to better reflect your communication style.

5. **Test Thoroughly**: Use the test script to verify that the model captures your style before deploying.

## Troubleshooting

- **API Rate Limits**: OpenAI has rate limits. If you hit them, wait and try again.
- **Cost Management**: Fine-tuning costs money. Monitor your OpenAI usage.
- **Discord API Limitations**: Discord may limit how far back you can fetch messages.

## Advanced Configuration

You can adjust various parameters:

- Message filtering: `--min-tokens` and `--max-tokens` in `prepare_training_data.py`
- Data split ratios: `--train-size`, `--val-size`, and `--test-size` in `prepare_training_data.py`
- Fine-tuning parameters: See OpenAI's documentation for advanced options
