"""
Test Discord Bot for AI Clone

A simplified version of the Discord bot for testing purposes.
This version skips the fine-tuning process and uses a base GPT model.
"""

import os
import json
import random
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
import openai

# Load environment variables
load_dotenv()

# Discord configuration
TOKEN = os.getenv('DISCORD_TOKEN')
USER_ID = int(os.getenv('DISCORD_USER_ID'))
RESPONSE_CHANNELS = [int(id) for id in os.getenv('RESPONSE_CHANNELS', '').split(',') if id]
RESPONSE_PROBABILITY = float(os.getenv('RESPONSE_PROBABILITY', '1.0'))
SUPERVISED_MODE = os.getenv('SUPERVISED_MODE', 'true').lower() == 'true'

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Store pending responses for supervised mode
pending_responses = {}

# Store conversation history
conversation_history = {}

async def generate_response(channel_id, context_messages):
    """Generate a response using GPT model."""
    try:
        # Format messages for the API
        messages = [
            {"role": "system", "content": "You are an AI assistant that responds like the user would respond in a Discord conversation. Keep responses conversational and in the style of the user. Respond as if you are the user."}
        ]
        
        # Add conversation history for context
        if channel_id in conversation_history:
            messages.extend(conversation_history[channel_id])
        
        # Add current context messages
        for msg in context_messages:
            role = "user" if msg['author_id'] != USER_ID else "assistant"
            messages.append({
                "role": role,
                "content": msg['content']
            })
        
        # Generate response
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Using a base model for testing
            messages=messages,
            max_tokens=150,
            temperature=0.7,
            top_p=0.95
        )
        
        response_text = response.choices[0].message.content
        
        # Update conversation history
        if channel_id not in conversation_history:
            conversation_history[channel_id] = []
        
        # Add the latest user message and response to history
        if context_messages:
            last_user_msg = context_messages[-1]
            conversation_history[channel_id].append({
                "role": "user",
                "content": last_user_msg['content']
            })
        
        conversation_history[channel_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        # Keep history limited to last 10 exchanges
        if len(conversation_history[channel_id]) > 20:
            conversation_history[channel_id] = conversation_history[channel_id][-20:]
        
        return response_text
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f"Supervised mode: {'Enabled' if SUPERVISED_MODE else 'Disabled'}")
    print(f"Response probability: {RESPONSE_PROBABILITY}")
    print(f"Responding in channels: {RESPONSE_CHANNELS if RESPONSE_CHANNELS else 'All channels'}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Handle direct messages (DMs)
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # Check if we should respond based on channel settings
    should_respond_to_channel = False
    
    # If RESPONSE_CHANNELS contains "dm" or is empty, respond to DMs
    dm_enabled = not RESPONSE_CHANNELS or 'dm' in [str(id).lower() for id in RESPONSE_CHANNELS]
    
    if is_dm and dm_enabled:
        should_respond_to_channel = True
    elif not is_dm and RESPONSE_CHANNELS and message.channel.id in RESPONSE_CHANNELS:
        should_respond_to_channel = True
    elif not is_dm and not RESPONSE_CHANNELS:
        # If no channels specified, respond in all channels
        should_respond_to_channel = True
        
    if not should_respond_to_channel:
        return
    
    # Only respond to messages not from the user (simulating a conversation with yourself)
    if message.author.id == USER_ID:
        return
    
    # Decide whether to respond based on probability
    if random.random() > RESPONSE_PROBABILITY:
        return
    
    # Get context (previous messages)
    context_messages = []
    async for ctx_msg in message.channel.history(limit=5, before=message):
        context_messages.append({
            'author_id': ctx_msg.author.id,
            'author_name': ctx_msg.author.name,
            'content': ctx_msg.content
        })
    
    # Add the current message to the context
    context_messages.append({
        'author_id': message.author.id,
        'author_name': message.author.name,
        'content': message.content
    })
    
    # Reverse the list to get chronological order
    context_messages.reverse()
    
    # Generate response
    response_text = await generate_response(message.channel.id, context_messages)
    
    if response_text:
        if SUPERVISED_MODE:
            # Store the response for approval
            pending_responses[message.id] = {
                'channel': message.channel,
                'response': response_text,
                'context': context_messages
            }
            
            # Send a DM to the user for approval
            user = await bot.fetch_user(USER_ID)
            embed = discord.Embed(title="Approve Response?", color=0x00ff00)
            embed.add_field(name="Original Message", value=message.content, inline=False)
            embed.add_field(name="Generated Response", value=response_text, inline=False)
            embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
            embed.add_field(name="Server", value=message.guild.name, inline=True)
            
            # Add approval buttons
            view = ApprovalView(message.id)
            await user.send(embed=embed, view=view)
        else:
            # Send the response directly
            await message.channel.send(response_text)
    
    await bot.process_commands(message)

# Approval view for supervised mode
class ApprovalView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.message_id = message_id
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id in pending_responses:
            response_data = pending_responses[self.message_id]
            await response_data['channel'].send(response_data['response'])
            del pending_responses[self.message_id]
            await interaction.response.send_message("Response approved and sent!")
            self.stop()
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id in pending_responses:
            del pending_responses[self.message_id]
            await interaction.response.send_message("Response rejected.")
            self.stop()
    
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id in pending_responses:
            response_data = pending_responses[self.message_id]
            
            # Create a modal for editing
            modal = EditResponseModal(self.message_id, response_data['response'])
            await interaction.response.send_modal(modal)
            self.stop()

# Modal for editing responses
class EditResponseModal(discord.ui.Modal, title="Edit Response"):
    def __init__(self, message_id, response_text):
        super().__init__()
        self.message_id = message_id
        self.response_input = discord.ui.TextInput(
            label="Edit your response",
            style=discord.TextStyle.paragraph,
            default=response_text,
            required=True
        )
        self.add_item(self.response_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.message_id in pending_responses:
            response_data = pending_responses[self.message_id]
            await response_data['channel'].send(self.response_input.value)
            del pending_responses[self.message_id]
            await interaction.response.send_message("Edited response sent!")

# Command to test the bot
@bot.command(name='test')
async def test_bot(ctx):
    """Test if the bot is working."""
    await ctx.send("I'm working! I'll respond to messages in the configured channels.")

# Command to clear conversation history
@bot.command(name='clear')
async def clear_history(ctx):
    """Clear the conversation history for this channel."""
    if ctx.author.id != USER_ID:
        await ctx.send("You are not authorized to use this command.")
        return
    
    if ctx.channel.id in conversation_history:
        conversation_history[ctx.channel.id] = []
        await ctx.send("Conversation history cleared for this channel.")
    else:
        await ctx.send("No conversation history found for this channel.")

if __name__ == "__main__":
    # Check if token is provided
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file")
    elif not openai.api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
    else:
        bot.run(TOKEN)
