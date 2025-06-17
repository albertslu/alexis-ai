"""
Collect and organize Discord conversations for training.

This script helps you organize Discord conversations for training your AI clone.
It provides a simple interface for adding conversations and saving them in the
correct format.
"""

import os
import json
import argparse
from datetime import datetime

def create_conversation_file(output_file, your_name):
    """Create a new conversation file."""
    print(f"\n=== Creating new conversation file: {output_file} ===")
    print(f"Your name in the conversation: {your_name}")
    print("\nInstructions:")
    print("1. Enter each message in the format: 'Name: Message'")
    print("2. Press Enter twice (empty line) to finish a conversation")
    print("3. Type 'exit' to save and quit")
    print("\nExample:")
    print("friend: Hey, how's it going?")
    print(f"{your_name}: not much, just working on this ai project")
    print("friend: That sounds cool! What does it do?")
    print(f"{your_name}: it's a discord bot that learns to talk like me")
    print("")
    
    conversations = []
    
    while True:
        print("\n--- New Conversation ---")
        conversation = []
        
        while True:
            line = input("> ")
            
            if not line:
                # Empty line, check if we should end this conversation
                if conversation:
                    confirm = input("End this conversation? (y/n): ")
                    if confirm.lower() in ['y', 'yes']:
                        break
                continue
            
            if line.lower() == 'exit':
                # Save and exit
                if conversation:
                    conversations.append(conversation)
                return conversations
            
            # Add the line to the current conversation
            conversation.append(line)
        
        # Add the completed conversation to our list
        if conversation:
            conversations.append(conversation)
            print(f"Conversation added ({len(conversation)} messages)")
        
        # Check if we want to add another conversation
        another = input("\nAdd another conversation? (y/n): ")
        if another.lower() not in ['y', 'yes']:
            break
    
    return conversations

def save_conversations(conversations, output_file, your_name):
    """Save conversations to a file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for conversation in conversations:
            for message in conversation:
                f.write(message + '\n')
            f.write('\n')  # Empty line between conversations
    
    print(f"\nSaved {len(conversations)} conversations to {output_file}")
    
    # Also create a metadata file
    metadata_file = output_file + '.meta.json'
    metadata = {
        'created_at': datetime.now().isoformat(),
        'your_name': your_name,
        'num_conversations': len(conversations),
        'total_messages': sum(len(c) for c in conversations),
        'your_messages': sum(1 for c in conversations for m in c if m.lower().startswith(your_name.lower() + ':')),
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata to {metadata_file}")
    print(f"Total messages: {metadata['total_messages']}")
    print(f"Your messages: {metadata['your_messages']}")

def main():
    parser = argparse.ArgumentParser(description="Collect Discord conversations for training")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--your-name", default="You", help="Your name in the conversations")
    
    args = parser.parse_args()
    
    # Set default output file if not provided
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f"data/conversations_{timestamp}.txt"
    
    # Create and save conversations
    conversations = create_conversation_file(args.output, args.your_name)
    save_conversations(conversations, args.output, args.your_name)
    
    print("\n=== Next Steps ===")
    print("1. Convert to training format:")
    print(f"   python convert_discord_chat.py {args.output} models/shaco_conversations --your-name {args.your_name}")
    print("2. Fine-tune your model:")
    print("   python finetune_discord_clone.py models/shaco_conversations_train.jsonl --validation-file models/shaco_conversations_val.jsonl")

if __name__ == "__main__":
    main()
