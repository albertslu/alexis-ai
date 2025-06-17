import Cocoa
import ApplicationServices
import Foundation

class AppDelegate: NSObject, NSApplicationDelegate {
    // Store references to prevent deallocation
    var statusItem: NSStatusItem?
    var overlayWindow: OverlayWindow?
    var webSocketServer: WebSocketServer?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create status item in menu bar
        setupStatusItem()
        
        // Setup workspace notifications to detect when Messages becomes active
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(applicationActivated),
            name: NSWorkspace.didActivateApplicationNotification,
            object: nil
        )
        
        // Setup WebSocket server for communication with main app
        setupWebSocketServer()
        
        // Create overlay window but keep it hidden initially
        createOverlayWindow()
        
        NSLog("Alexis AI Overlay Agent started")
    }
    
    func setupStatusItem() {
        // Create a status item with fixed width to ensure visibility
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem?.button {
            button.title = "Alexis"
        }
        
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q"))
        statusItem?.menu = menu
        
        NSLog("Status item created")
    }
    
    @objc func quitApp() {
        NSApplication.shared.terminate(nil)
    }
    

    
    func createOverlayWindow() {
        overlayWindow = OverlayWindow()
        overlayWindow?.setup()
    }
    

    
    func setupWebSocketServer() {
        webSocketServer = WebSocketServer()
        webSocketServer?.start()
    }
    
    @objc func applicationActivated(_ notification: Notification) {
        guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else {
            return
        }
        
        // Check if Messages app is active
        if app.bundleIdentifier == "com.apple.MobileSMS" {
            NSLog("Messages app activated")
            showOverlay()
            
            // Get conversation context and send to main app
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                // Wait a moment for Messages to fully activate
                Thread.sleep(forTimeInterval: 0.5)
                
                guard let self = self else { return }
                
                // Get conversation context
                let context = self.getConversationContext()
                NSLog("Got conversation context: \n\(context)")
                
                // Send context to main app via HTTP
                DispatchQueue.main.async {
                    self.webSocketServer?.processMessage("{\"type\":\"conversation_context\",\"context\":\"\(self.escapeJsonString(context))\"}")
                }
            }
        } else {
            NSLog("Other app activated: \(app.bundleIdentifier ?? "unknown")")
            hideOverlay()
        }
    }
    
    func showOverlay() {
        overlayWindow?.orderFront(nil)
        NSLog("Showing overlay window")
    }
    
    func hideOverlay() {
        overlayWindow?.orderOut(nil)
        NSLog("Hiding overlay window")
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Stop the HTTP polling
        webSocketServer?.stop()
    }
    
    // Helper function to escape JSON strings
    private func escapeJsonString(_ text: String) -> String {
        var escaped = text.replacingOccurrences(of: "\\", with: "\\\\")
        escaped = escaped.replacingOccurrences(of: "\"", with: "\\\"")
        escaped = escaped.replacingOccurrences(of: "\n", with: "\\n")
        escaped = escaped.replacingOccurrences(of: "\r", with: "\\r")
        escaped = escaped.replacingOccurrences(of: "\t", with: "\\t")
        return escaped
    }
    
    // Get the active conversation context using direct shell commands
    func getConversationContext() -> String {
        do {
            // Step 1: Get the active conversation ID using defaults command
            let task = Process()
            task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            task.arguments = ["bash", "-c", "defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier | sed 's/^[^-]*-//'"] 
            
            let pipe = Pipe()
            task.standardOutput = pipe
            try task.run()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let rawID = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), !rawID.isEmpty else {
                NSLog("Failed to get valid conversation ID")
                return "No active conversation ID found"
            }
            
            NSLog("Got active conversation ID: \(rawID)")
            
            // Extract the phone number from the conversation ID
            // The format is typically 'iMessage;-;+1234567890'
            var phoneNumber = rawID
            if rawID.contains(";") {
                let parts = rawID.components(separatedBy: ";")
                if parts.count > 2 {
                    phoneNumber = parts[2] // Get the last part
                }
            }
            NSLog("Extracted phone number: \(phoneNumber)")
            
            // Step 2: Use the extracted phone number to find the chat ID
            let chatIdTask = Process()
            chatIdTask.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            
            // Use LIKE with wildcards to be more flexible in matching
            let chatIdQuery = "sqlite3 ~/Library/Messages/chat.db \"SELECT ROWID FROM chat WHERE chat_identifier LIKE '%\(phoneNumber)%';\""
            chatIdTask.arguments = ["bash", "-c", chatIdQuery]
            
            let chatIdPipe = Pipe()
            chatIdTask.standardOutput = chatIdPipe
            try chatIdTask.run()
            
            let chatIdData = chatIdPipe.fileHandleForReading.readDataToEndOfFile()
            guard let chatId = String(data: chatIdData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), !chatId.isEmpty else {
                NSLog("Failed to get chat ID for conversation")
                return "No chat ID found for conversation"
            }
            
            NSLog("Found chat with ROWID: \(chatId)")
            
            // Step 3: Now use the chat ID to query messages
            let dbTask = Process()
            dbTask.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            
            // Create a query that gets the last 10 messages from the conversation
            let query = """
            sqlite3 ~/Library/Messages/chat.db "SELECT 
                m.text, 
                m.is_from_me, 
                datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') as date_str
            FROM 
                message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE 
                cmj.chat_id = \(chatId)
                AND m.text IS NOT NULL
            ORDER BY 
                m.date DESC
            LIMIT 10;"
            """
            
            dbTask.arguments = ["bash", "-c", query]
            
            let dbPipe = Pipe()
            dbTask.standardOutput = dbPipe
            try dbTask.run()
            
            let dbData = dbPipe.fileHandleForReading.readDataToEndOfFile()
            guard let messagesData = String(data: dbData, encoding: .utf8) else {
                return "No messages found for conversation"
            }
            
            // Step 4: Format the messages into a conversation context
            var formattedContext = "Conversation with \(rawID):\n\n"
            
            // Split the messages by line
            let messages = messagesData.components(separatedBy: "\n")
            
            // Process each message line and reverse the order (since we queried DESC)
            let messageLines = messages.filter { !$0.isEmpty }
            let reversedMessages = messageLines.reversed()
            
            for message in reversedMessages {
                let parts = message.components(separatedBy: "|") 
                if parts.count >= 2 {
                    let text = parts[0].trimmingCharacters(in: .whitespacesAndNewlines)
                    let isFromMe = parts[1].trimmingCharacters(in: .whitespacesAndNewlines) == "1"
                    
                    let sender = isFromMe ? "Me" : "Other"
                    formattedContext += "\(sender): \(text)\n"
                }
            }
            
            // If no messages were found, add a note
            if formattedContext == "Conversation with \(rawID):\n\n" {
                formattedContext += "[No message history found]\n"
            }
            
            return formattedContext
            
        } catch {
            NSLog("Error executing shell command: \(error)")
            return "Error retrieving conversation: \(error.localizedDescription)"
        }
    }
}
