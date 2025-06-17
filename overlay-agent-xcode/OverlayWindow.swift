import Cocoa
import ApplicationServices

// Using logToFile from WebSocketServer.swift
class OverlayWindow: NSPanel {
    private var closeButton: NSButton?
    private var suggestionButtons: [NSButton] = []
    
    override init(
        contentRect: NSRect,
        styleMask style: NSWindow.StyleMask,
        backing backingStoreType: NSWindow.BackingStoreType,
        defer flag: Bool
    ) {
        // Initialize with an empty content rect, we'll position it later
        super.init(
            contentRect: NSRect(x: 100, y: 100, width: 300, height: 150),
            styleMask: [.nonactivatingPanel, .titled, .closable, .resizable],
            backing: .buffered,
            defer: true
        )
    }
    
    convenience init() {
        self.init(
            contentRect: NSRect(x: 100, y: 100, width: 300, height: 150),
            styleMask: [.nonactivatingPanel, .titled, .closable, .resizable],
            backing: .buffered,
            defer: true
        )
    }
    
    func setup() {
        // Configure window properties
        self.title = "Alexis AI Suggestions"
        self.level = .floating
        self.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        self.isMovableByWindowBackground = true
        self.backgroundColor = NSColor.windowBackgroundColor
        self.hasShadow = true
        
        // Create content view
        let contentView = NSView(frame: NSRect(x: 0, y: 0, width: 300, height: 140))
        self.contentView = contentView
        
        // Add suggestion buttons
        setupSuggestionButtons()
        
        // Register for suggestion updates
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleSuggestionUpdate(_:)),
            name: NSNotification.Name("UpdateSuggestions"),
            object: nil
        )
        
        NSLog("Overlay window setup complete")
    }
    
    private func setupSuggestionButtons() {
        guard let contentView = self.contentView else { return }
        
        // Clear existing buttons
        for button in suggestionButtons {
            button.removeFromSuperview()
        }
        suggestionButtons.removeAll()
        
        // Create new suggestion buttons
        let buttonHeight = 30.0
        let buttonWidth = 280.0
        let padding = 10.0
        
        // iMessage blue color
        let imessageBlueColor = NSColor(calibratedRed: 0.0, green: 0.52, blue: 1.0, alpha: 1.0)
        
        for i in 0..<3 {
            let y = padding + CGFloat(i) * (buttonHeight + padding)
            let button = NSButton(frame: NSRect(x: padding, y: y, width: buttonWidth, height: buttonHeight))
            button.title = "Suggestion \(i + 1)"
            
            // Style the button to look like iMessage
            button.bezelStyle = .rounded
            button.isBordered = false
            
            // Set the background color to iMessage blue
            button.wantsLayer = true
            button.layer?.backgroundColor = imessageBlueColor.cgColor
            button.layer?.cornerRadius = 15.0 // Rounded corners
            
            // Set text color to white
            let attributes: [NSAttributedString.Key: Any] = [
                .foregroundColor: NSColor.white,
                .font: NSFont.systemFont(ofSize: 13, weight: .medium)
            ]
            let attributedTitle = NSAttributedString(string: button.title, attributes: attributes)
            button.attributedTitle = attributedTitle
            
            button.target = self
            button.action = #selector(suggestionClicked(_:))
            button.tag = i
            
            contentView.addSubview(button)
            suggestionButtons.append(button)
        }
    }
    
    @objc func suggestionClicked(_ sender: NSButton) {
        NSLog("Suggestion button \(sender.tag + 1) clicked")
        
        // Get the suggestion text from the button
        let suggestionText = sender.title
        
        // Simple variable to track if insertion was successful
        var inserted = false
        
        // Use the simple approach for text insertion with a small delay to ensure the app is ready
        let script = "tell application \"Messages\" to activate\ndelay 0.1\ntell application \"System Events\" to keystroke \"" + suggestionText.replacingOccurrences(of: "\"", with: "\\\"") + "\""
        
        let appleScript = NSAppleScript(source: script)
        var errorDict: NSDictionary?
        appleScript?.executeAndReturnError(&errorDict)
        
        if errorDict == nil {
            inserted = true
            NSLog("Successfully inserted text: \(suggestionText)")
        } else {
            NSLog("Error executing AppleScript: \(String(describing: errorDict))")
        }
        
        // Notify the main app that a suggestion was selected
        NotificationCenter.default.post(
            name: NSNotification.Name("SuggestionSelected"),
            object: nil,
            userInfo: [
                "index": sender.tag,
                "text": suggestionText,
                "inserted": inserted
            ]
        )
        
        // Hide the overlay window after selection
        self.orderOut(nil)
    }
    
    func updateSuggestions(_ suggestions: [String], isLoading: Bool = false) {
        NSLog("DEBUG: updateSuggestions called with \(suggestions.count) suggestions, isLoading: \(isLoading)")
        logToFile("updateSuggestions called with \(suggestions.count) suggestions, isLoading: \(isLoading)")
        logToFile("Suggestions: \(suggestions)")
        
        // iMessage blue color and loading gray color
        let imessageBlueColor = NSColor(calibratedRed: 0.0, green: 0.52, blue: 1.0, alpha: 1.0)
        let loadingGrayColor = NSColor(calibratedRed: 0.6, green: 0.6, blue: 0.6, alpha: 1.0)
        
        // Choose colors based on loading state
        let backgroundColor = isLoading ? loadingGrayColor : imessageBlueColor
        let textColor = NSColor.white
        
        // If this is a single loading message, handle it differently
        if isLoading && suggestions.count == 1 {
            // Show only the first button with the loading message, hide the others
            let loadingMessage = suggestions[0]
            
            // Update first button with loading message
            if !suggestionButtons.isEmpty {
                let button = suggestionButtons[0]
                button.title = loadingMessage
                
                let attributes: [NSAttributedString.Key: Any] = [
                    .foregroundColor: textColor,
                    .font: NSFont.systemFont(ofSize: 13, weight: .medium)
                ]
                let attributedTitle = NSAttributedString(string: loadingMessage, attributes: attributes)
                button.attributedTitle = attributedTitle
                
                button.wantsLayer = true
                button.layer?.backgroundColor = backgroundColor.cgColor
                button.layer?.cornerRadius = 15.0
                button.isEnabled = false // Disable during loading
                button.isHidden = false
            }
            
            // Hide the other buttons during loading
            for i in 1..<suggestionButtons.count {
                suggestionButtons[i].isHidden = true
            }
            
            // Adjust window size for single loading message
            let newHeight: CGFloat = 70.0 // Smaller height for single loading message
            var frame = self.frame
            frame.size.height = newHeight
            self.setFrame(frame, display: true)
            
            NSLog("DEBUG: Showing single loading message: '\(loadingMessage)'")
            logToFile("Showing single loading message: '\(loadingMessage)'")
            
        } else {
            // Normal case: show all suggestions or regular loading state
            
            // Adjust window size back to normal for multiple suggestions
            let normalHeight: CGFloat = 150.0 // Increased from 130.0 to 150.0 for better spacing
            var frame = self.frame
            frame.size.height = normalHeight
            self.setFrame(frame, display: true)
            
            // Update each button with a suggestion and show only the ones we have suggestions for
            for (index, suggestion) in suggestions.enumerated() {
                if index < suggestionButtons.count {
                    let button = suggestionButtons[index]
                    button.title = suggestion
                    
                    let attributes: [NSAttributedString.Key: Any] = [
                        .foregroundColor: textColor,
                        .font: NSFont.systemFont(ofSize: 13, weight: .medium)
                    ]
                    let attributedTitle = NSAttributedString(string: suggestion, attributes: attributes)
                    button.attributedTitle = attributedTitle
                    
                    button.wantsLayer = true
                    button.layer?.backgroundColor = backgroundColor.cgColor
                    button.layer?.cornerRadius = 15.0
                    button.isEnabled = !isLoading
                    button.isHidden = false // Show this button
                    
                    NSLog("DEBUG: Button \(index + 1) updated with suggestion: '\(suggestion)', isLoading: \(isLoading)")
                    logToFile("Button \(index + 1) updated with suggestion: '\(suggestion)', isLoading: \(isLoading)")
                }
            }
            
            // Hide buttons that don't have corresponding suggestions
            for index in suggestions.count..<suggestionButtons.count {
                suggestionButtons[index].isHidden = true
                NSLog("DEBUG: Button \(index + 1) hidden (no suggestion)")
                logToFile("Button \(index + 1) hidden (no suggestion)")
            }
        }
        
        NSLog("DEBUG: Finished updating suggestions")
        logToFile("Finished updating suggestions")
    }
    
    @objc func handleSuggestionUpdate(_ notification: Notification) {
        NSLog("DEBUG: handleSuggestionUpdate called with notification: \(notification)")
        logToFile("handleSuggestionUpdate called with notification: \(notification)")
        
        guard let userInfo = notification.userInfo else {
            NSLog("DEBUG: Notification userInfo is nil")
            logToFile("Notification userInfo is nil")
            return
        }
        
        NSLog("DEBUG: Notification userInfo: \(userInfo)")
        logToFile("Notification userInfo: \(userInfo)")
        
        guard let suggestions = userInfo["suggestions"] as? [String] else {
            NSLog("DEBUG: Failed to extract suggestions from userInfo")
            logToFile("Failed to extract suggestions from userInfo")
            
            if let wrongType = userInfo["suggestions"] {
                NSLog("DEBUG: 'suggestions' is present but has wrong type: \(type(of: wrongType))")
                NSLog("DEBUG: Value: \(wrongType)")
                logToFile("'suggestions' is present but has wrong type: \(type(of: wrongType))")
                logToFile("Value: \(wrongType)")
            } else {
                NSLog("DEBUG: 'suggestions' key is not present in userInfo")
                logToFile("'suggestions' key is not present in userInfo")
            }
            return
        }
        
        // Extract loading state (defaults to false if not present)
        let isLoading = userInfo["isLoading"] as? Bool ?? false
        
        NSLog("DEBUG: Extracted \(suggestions.count) suggestions: \(suggestions), isLoading: \(isLoading)")
        logToFile("Extracted \(suggestions.count) suggestions: \(suggestions), isLoading: \(isLoading)")
        
        NSLog("DEBUG: Updating overlay with suggestions")
        logToFile("Updating overlay with suggestions")
        updateSuggestions(suggestions, isLoading: isLoading)
        
        // Check if the window is already visible
        let wasVisible = self.isVisible
        
        // Make sure the window is visible when suggestions are received
        NSLog("DEBUG: Making overlay window visible")
        logToFile("Making overlay window visible")
        self.orderFront(nil)
        
        // Only position the window if it wasn't already visible
        // This prevents the window from jumping back when the user has moved it
        if !wasVisible {
            NSLog("DEBUG: Positioning window (window was not visible before)")
            logToFile("Positioning window (window was not visible before)")
            positionWindowForMessages()
        } else {
            NSLog("DEBUG: Skipping window positioning (window was already visible)")
            logToFile("Skipping window positioning (window was already visible)")
        }
        
        NSLog("DEBUG: Suggestion update complete")
        logToFile("Suggestion update complete")
    }
    
    private func positionWindowForMessages() {
        // Try to position the window near the Messages app text input field
        // This is a simple positioning that places it in the lower right corner of the screen
        if let screen = NSScreen.main {
            let screenFrame = screen.visibleFrame
            let windowFrame = self.frame
            
            // Position in the lower right corner with some padding
            let padding: CGFloat = 20.0
            let newOrigin = NSPoint(
                x: screenFrame.maxX - windowFrame.width - padding,
                y: screenFrame.minY + padding
            )
            
            NSLog("Positioning overlay window at \(newOrigin.x), \(newOrigin.y)")
            self.setFrameOrigin(newOrigin)
        }
    }
}
