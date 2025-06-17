"""
Discord Bot for AI Clone

Handles Discord interactions and integrates with the AI service.
"""

import random
import discord
from discord.ext import commands
from .config import Config
from .ai_service import AIService

class DiscordBot:
    """Discord bot for the AI Clone"""
    
    def __init__(self):
        """Initialize the Discord bot"""
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize bot
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # Initialize AI service
        self.ai_service = AIService()
        
        # Store pending responses for supervised mode
        self.pending_responses = {}
        
        # Set up event handlers
        self._setup_event_handlers()
        self._setup_commands()
    
    def _setup_event_handlers(self):
        """Set up Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            """Called when the bot is ready"""
            print(f'{self.bot.user.name} has connected to Discord!')
            print(f"Using model: {Config.AI_MODEL}")
            print(f"Supervised mode: {'Enabled' if Config.SUPERVISED_MODE else 'Disabled'}")
            print(f"Response probability: {Config.RESPONSE_PROBABILITY}")
            print(f"Responding in channels: {Config.RESPONSE_CHANNELS if Config.RESPONSE_CHANNELS else 'None specified'}")
            print(f"Responding to DMs: {'Yes' if Config.DM_ENABLED else 'No'}")
        
        @self.bot.event
        async def on_message(message):
            """Called when a message is received"""
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Handle direct messages (DMs)
            is_dm = isinstance(message.channel, discord.DMChannel)
            
            # Check if we should respond based on channel settings
            should_respond_to_channel = False
            
            if is_dm and Config.DM_ENABLED:
                should_respond_to_channel = True
            elif not is_dm and Config.RESPONSE_CHANNELS and message.channel.id in Config.RESPONSE_CHANNELS:
                should_respond_to_channel = True
            elif not is_dm and not Config.RESPONSE_CHANNELS and not Config.DM_ENABLED:
                # If no channels specified and DM not enabled, respond in all channels
                should_respond_to_channel = True
                
            if not should_respond_to_channel:
                await self.bot.process_commands(message)
                return
            
            # Only respond to messages not from the user (simulating a conversation with yourself)
            if message.author.id == Config.DISCORD_USER_ID:
                await self.bot.process_commands(message)
                return
            
            # Decide whether to respond based on probability
            if random.random() > Config.RESPONSE_PROBABILITY:
                await self.bot.process_commands(message)
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
            channel_id = f"dm_{message.author.id}" if is_dm else message.channel.id
            response_text = await self.ai_service.generate_response(channel_id, context_messages)
            
            if response_text:
                if Config.SUPERVISED_MODE:
                    # Store the response for approval
                    self.pending_responses[message.id] = {
                        'channel': message.channel,
                        'response': response_text,
                        'context': context_messages
                    }
                    
                    # Send a DM to the user for approval
                    user = await self.bot.fetch_user(Config.DISCORD_USER_ID)
                    embed = discord.Embed(title="Approve Response?", color=0x00ff00)
                    embed.add_field(name="Original Message", value=message.content, inline=False)
                    embed.add_field(name="Generated Response", value=response_text, inline=False)
                    
                    if is_dm:
                        embed.add_field(name="From", value=f"DM with {message.author.name}", inline=True)
                    else:
                        embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
                        embed.add_field(name="Server", value=message.guild.name, inline=True)
                    
                    # Add approval buttons
                    view = self.ApprovalView(self, message.id)
                    await user.send(embed=embed, view=view)
                else:
                    # Send the response directly
                    await message.channel.send(response_text)
            
            await self.bot.process_commands(message)
    
    def _setup_commands(self):
        """Set up Discord commands"""
        
        @self.bot.command(name='test')
        async def test_bot(ctx):
            """Test if the bot is working."""
            await ctx.send("I'm working! I'll respond to messages in the configured channels.")
        
        @self.bot.command(name='clear')
        async def clear_history(ctx):
            """Clear the conversation history for this channel."""
            if ctx.author.id != Config.DISCORD_USER_ID:
                await ctx.send("You are not authorized to use this command.")
                return
            
            channel_id = f"dm_{ctx.author.id}" if isinstance(ctx.channel, discord.DMChannel) else ctx.channel.id
            if self.ai_service.clear_history(channel_id):
                await ctx.send("Conversation history cleared for this channel.")
            else:
                await ctx.send("No conversation history found for this channel.")
    
    # Approval view for supervised mode
    class ApprovalView(discord.ui.View):
        def __init__(self, bot_instance, message_id):
            super().__init__(timeout=300)  # 5 minute timeout
            self.bot_instance = bot_instance
            self.message_id = message_id
        
        @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
        async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.message_id in self.bot_instance.pending_responses:
                response_data = self.bot_instance.pending_responses[self.message_id]
                await response_data['channel'].send(response_data['response'])
                del self.bot_instance.pending_responses[self.message_id]
                await interaction.response.send_message("Response approved and sent!")
                self.stop()
        
        @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
        async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.message_id in self.bot_instance.pending_responses:
                del self.bot_instance.pending_responses[self.message_id]
                await interaction.response.send_message("Response rejected.")
                self.stop()
        
        @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple)
        async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.message_id in self.bot_instance.pending_responses:
                response_data = self.bot_instance.pending_responses[self.message_id]
                
                # Create a modal for editing
                modal = self.bot_instance.EditResponseModal(self.bot_instance, self.message_id, response_data['response'])
                await interaction.response.send_modal(modal)
                self.stop()
    
    # Modal for editing responses
    class EditResponseModal(discord.ui.Modal, title="Edit Response"):
        def __init__(self, bot_instance, message_id, response_text):
            super().__init__()
            self.bot_instance = bot_instance
            self.message_id = message_id
            self.response_input = discord.ui.TextInput(
                label="Edit your response",
                style=discord.TextStyle.paragraph,
                default=response_text,
                required=True
            )
            self.add_item(self.response_input)
        
        async def on_submit(self, interaction: discord.Interaction):
            if self.message_id in self.bot_instance.pending_responses:
                response_data = self.bot_instance.pending_responses[self.message_id]
                await response_data['channel'].send(self.response_input.value)
                del self.bot_instance.pending_responses[self.message_id]
                await interaction.response.send_message("Edited response sent!")
    
    async def start(self):
        """Start the Discord bot"""
        if not Config.DISCORD_TOKEN:
            print("Error: DISCORD_TOKEN is not set in .env file")
            return False
        
        try:
            await self.bot.start(Config.DISCORD_TOKEN)
            return True
        except Exception as e:
            print(f"Error starting Discord bot: {e}")
            return False
