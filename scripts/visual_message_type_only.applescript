-- Visual Message Typer for AI Clone
-- This script visually types messages in the Messages app without sending them
-- with realistic typing simulation

on run argv
    set phoneNumber to item 1 of argv
    set messageText to item 2 of argv
    
    -- Check if we have a chat ID (3rd argument)
    set chatID to missing value
    if (count of argv) ≥ 3 then
        set chatID to item 3 of argv
    end if
    
    -- Activate Messages app
    tell application "Messages"
        activate
        delay 1.0
    end tell
    
    -- Use UI scripting to create a new message with the recipient
    tell application "System Events"
        tell process "Messages"
            -- Click the compose button to start a new message
            keystroke "n" using {command down}
            delay 0.5
            
            -- Type the phone number in the "To:" field
            keystroke phoneNumber
            delay 0.5
            
            -- Press Tab to move to the message field
            keystroke tab
            delay 0.3
        end tell
    end tell
    
    -- Wait for the Messages app to be ready
    delay 1.0
    
    -- Focus on the text input field
    tell application "System Events"
        tell process "Messages"
            -- Wait a moment to ensure the UI is ready
            delay 0.5
            
            -- Try to focus on the text field using different methods
            -- Method 1: Tab navigation
            try
                keystroke tab
                delay 0.3
            on error
                -- Method 2: Try clicking in the text area
                try
                    -- Try to find and click the text input area
                    click text area 1 of window 1
                    delay 0.3
                on error
                    -- Method 3: Try using key combination to focus
                    keystroke "t" using {command down, shift down}
                    delay 0.3
                end try
            end try
            
            -- Clear any existing text in the field
            keystroke "a" using {command down}
            keystroke (ASCII character 8) -- delete key
            delay 0.2
            
            -- Simulate thinking time before typing
            delay random number from 0.5 to 1.2
            
            -- Type the message character by character with realistic timing
            set messageLength to length of messageText
            repeat with i from 1 to messageLength
                -- Get the current character
                set currentChar to character i of messageText
                
                -- Type the character
                keystroke currentChar
                
                -- Add realistic typing delays
                if currentChar is in " .,!?" then
                    -- Longer pause after punctuation and spaces
                    delay random number from 0.08 to 0.2
                else
                    -- Normal typing speed with slight variations
                    delay random number from 0.02 to 0.08
                end if
                
                -- Occasionally add a longer pause to simulate thinking
                if (i mod 15) is 0 then
                    if (random number from 1 to 10) is 1 then
                        delay random number from 0.2 to 0.5
                    end if
                end if
            end repeat
            
            -- Pause briefly after typing (but don't press return)
            delay random number from 0.3 to 0.7
        end tell
    end tell
    
    -- Return success
    return "SUCCESS: Message typed but not sent to " & phoneNumber
end run
