import Foundation
import Cocoa

// Helper function to write logs to a file
public func logToFile(_ message: String) {
    let fileManager = FileManager.default
    let logDirectory = "\(NSHomeDirectory())/Library/Application Support/alexis-ai-desktop/logs"
    let logFile = "\(logDirectory)/overlay-agent.log"
    
    // Create directory if it doesn't exist
    if !fileManager.fileExists(atPath: logDirectory) {
        do {
            try fileManager.createDirectory(atPath: logDirectory, withIntermediateDirectories: true)
        } catch {
            NSLog("Error creating log directory: \(error)")
            return
        }
    }
    
    // Format the log message with timestamp
    let dateFormatter = DateFormatter()
    dateFormatter.dateFormat = "yyyy-MM-dd HH:mm:ss.SSS"
    let timestamp = dateFormatter.string(from: Date())
    let formattedMessage = "\(timestamp) - \(message)\n"
    
    // Append to log file
    if let data = formattedMessage.data(using: .utf8) {
        if fileManager.fileExists(atPath: logFile) {
            if let fileHandle = try? FileHandle(forWritingTo: URL(fileURLWithPath: logFile)) {
                fileHandle.seekToEndOfFile()
                fileHandle.write(data)
                fileHandle.closeFile()
            }
        } else {
            try? data.write(to: URL(fileURLWithPath: logFile))
        }
    }
}

class WebSocketServer {
    private var port: UInt16
    private var pollTimer: Timer?
    private var conversationMonitorTimer: Timer?
    private let pollInterval: TimeInterval = 1.0 // Poll every second
    private let conversationCheckInterval: TimeInterval = 0.5 // Check conversation changes every 0.5 seconds
    private var lastSuggestions: [String] = [] // Store the last received suggestions
    private var lastConversationId: String = "" // Track conversation changes
    private var isGeneratingSuggestions: Bool = false // Track if suggestions are being generated
    
    init() {
        // Port must be specified via command line
        var portValue: UInt16? = nil
        
        // Check for port in command line arguments
        for argument in CommandLine.arguments {
            if argument.starts(with: "--port=") {
                let portString = argument.replacingOccurrences(of: "--port=", with: "")
                if let parsedPort = UInt16(portString) {
                    portValue = parsedPort
                    NSLog("Using port from command line: \(parsedPort)")
                }
            }
        }
        
        // Require port parameter
        guard let unwrappedPort = portValue else {
            NSLog("ERROR: Port parameter is required. Please specify --port=PORT")
            exit(1) // Exit with error code
        }
        
        self.port = unwrappedPort
        NSLog("WebSocketServer initialized with host: localhost, port: \(port)")
        logToFile("WebSocketServer initialized with host: localhost, port: \(port)")
    }
    
    func start() {
        NSLog("Starting HTTP polling for suggestions")
        logToFile("Starting HTTP polling for suggestions")
        
        // Register for suggestion selection notifications
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleSuggestionSelected(_:)),
            name: NSNotification.Name("SuggestionSelected"),
            object: nil
        )
        
        // Start polling timer
        startPolling()
        
        // Start conversation monitoring timer
        startConversationMonitoring()
    }
    
    func stop() {
        NSLog("Stopping HTTP polling")
        logToFile("Stopping HTTP polling")
        
        // Stop polling timer
        pollTimer?.invalidate()
        pollTimer = nil
        
        // Stop conversation monitoring timer
        conversationMonitorTimer?.invalidate()
        conversationMonitorTimer = nil
        
        // Remove notification observer
        NotificationCenter.default.removeObserver(self)
        
        NSLog("HTTP polling stopped")
        logToFile("HTTP polling stopped")
    }
    
    private func startPolling() {
        // Stop existing timer if any
        pollTimer?.invalidate()
        
        // Create a new timer that polls for suggestions
        pollTimer = Timer.scheduledTimer(withTimeInterval: pollInterval, repeats: true) { [weak self] _ in
            self?.pollForSuggestions()
        }
        
        // Add the timer to the main run loop
        RunLoop.main.add(pollTimer!, forMode: .common)
    }
    
    private func startConversationMonitoring() {
        // Stop existing timer if any
        conversationMonitorTimer?.invalidate()
        
        // Create a new timer that monitors conversation changes
        conversationMonitorTimer = Timer.scheduledTimer(withTimeInterval: conversationCheckInterval, repeats: true) { [weak self] _ in
            self?.checkConversationChanges()
        }
        
        // Add the timer to the main run loop
        RunLoop.main.add(conversationMonitorTimer!, forMode: .common)
        
        NSLog("Started conversation monitoring")
        logToFile("Started conversation monitoring")
    }
    
    private func pollForSuggestions() {
        NSLog("Polling for suggestions")
        logToFile("Polling for suggestions")
        
        // Create URL for the latest suggestions endpoint
        let urlString = "http://localhost:5002/api/latest-suggestions"
        guard let url = URL(string: urlString) else {
            NSLog("Error: Invalid URL for suggestions endpoint")
            logToFile("Error: Invalid URL for suggestions endpoint")
            return
        }
        
        // Log the URL we're polling
        NSLog("Polling URL: \(urlString)")
        logToFile("Polling URL: \(urlString)")
        
        // If the server isn't running, we'll get connection errors
        // The server.js needs to be started manually or by the Electron app
        
        // Create a URL request
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        // Create a task to fetch the suggestions
        let task = URLSession.shared.dataTask(with: request) { [weak self] (data, response, error) in
            // Check for errors
            if let error = error {
                NSLog("Error fetching suggestions: \(error.localizedDescription)")
                logToFile("Error fetching suggestions: \(error.localizedDescription)")
                return
            }
            
            // Check for valid HTTP response
            guard let httpResponse = response as? HTTPURLResponse else {
                NSLog("Error: Invalid HTTP response")
                logToFile("Error: Invalid HTTP response")
                return
            }
            
            // Check for successful status code
            guard httpResponse.statusCode == 200 else {
                NSLog("Error: HTTP status code \(httpResponse.statusCode)")
                logToFile("Error: HTTP status code \(httpResponse.statusCode)")
                return
            }
            
            // Check for valid data
            guard let data = data else {
                NSLog("Error: No data received")
                logToFile("Error: No data received")
                return
            }
            
            // Parse the JSON response
            do {
                if let json = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                    // Check if the response contains suggestions
                    if let success = json["success"] as? Bool, success,
                       let suggestions = json["suggestions"] as? [String] {
                        // Process the suggestions
                        NSLog("Received \(suggestions.count) suggestions from API")
                        logToFile("Received \(suggestions.count) suggestions from API")
                        
                        // Create a JSON message similar to what we'd receive from WebSocket
                        let suggestionsMessage: [String: Any] = ["type": "suggestions", "suggestions": suggestions]
                        if let jsonData = try? JSONSerialization.data(withJSONObject: suggestionsMessage),
                           let jsonString = String(data: jsonData, encoding: .utf8) {
                            // Process the suggestions as if they came from WebSocket
                            self?.processMessage(jsonString)
                        }
                    } else {
                        NSLog("Error: Invalid suggestions format in response")
                        logToFile("Error: Invalid suggestions format in response")
                    }
                }
            } catch {
                NSLog("Error parsing JSON: \(error.localizedDescription)")
                logToFile("Error parsing JSON: \(error.localizedDescription)")
            }
        }
        
        // Start the task
        task.resume()
    }
    
    @objc func handleSuggestionSelected(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let index = userInfo["index"] as? Int,
              let text = userInfo["text"] as? String,
              let inserted = userInfo["inserted"] as? Bool else {
            NSLog("Invalid suggestion selection notification")
            logToFile("Invalid suggestion selection notification")
            return
        }
        
        NSLog("User selected suggestion at index \(index): \(text) (inserted: \(inserted))")
        
        sendSuggestionSelected(index: index, text: text, inserted: inserted)
    }
    
    func sendSuggestionSelected(index: Int, text: String, inserted: Bool) {
        // Send selection to main app via HTTP
        NSLog("Sending suggestion selection to main app: index=\(index), text=\(text), inserted=\(inserted)")
        logToFile("Sending suggestion selection to main app: index=\(index), text=\(text), inserted=\(inserted)")
        
        // Create URL for the suggestion selection endpoint
        let urlString = "http://localhost:5002/api/suggestion-selected"
        guard let url = URL(string: urlString) else {
            NSLog("Error: Invalid URL for suggestion selection endpoint")
            logToFile("Error: Invalid URL for suggestion selection endpoint")
            return
        }
        
        // Create request
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Create JSON payload
        let payload: [String: Any] = [
            "index": index,
            "text": text,
            "inserted": inserted
        ]
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: payload)
            request.httpBody = jsonData
            
            // Send the request
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    NSLog("Error sending suggestion selection: \(error.localizedDescription)")
                    logToFile("Error sending suggestion selection: \(error.localizedDescription)")
                    return
                }
                
                NSLog("Suggestion selection sent successfully")
                logToFile("Suggestion selection sent successfully")
            }
            
            task.resume()
        } catch {
            NSLog("Error creating JSON payload: \(error.localizedDescription)")
            logToFile("Error creating JSON payload: \(error.localizedDescription)")
        }
    }
    
    func sendConversationContext(_ context: String) {
        // Send conversation context to main app via HTTP
        NSLog("Sending conversation context to main app")
        logToFile("Sending conversation context to main app")
        
        // Create URL for the conversation context endpoint
        let urlString = "http://localhost:5002/api/conversation-context"
        guard let url = URL(string: urlString) else {
            NSLog("Error: Invalid URL for conversation context endpoint")
            logToFile("Error: Invalid URL for conversation context endpoint")
            return
        }
        
        // Create request
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Create JSON payload
        let payload = ["context": context]
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: payload)
            request.httpBody = jsonData
            
            // Send the request
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    NSLog("Error sending conversation context: \(error.localizedDescription)")
                    logToFile("Error sending conversation context: \(error.localizedDescription)")
                    return
                }
                
                NSLog("Conversation context sent successfully")
                logToFile("Conversation context sent successfully")
            }
            
            task.resume()
        } catch {
            NSLog("Error creating JSON payload: \(error.localizedDescription)")
            logToFile("Error creating JSON payload: \(error.localizedDescription)")
        }
    }
    
    // Process a message received from the HTTP API
    func processMessage(_ message: String) {
        NSLog("Processing message: \(message)")
        logToFile("Processing message: \(message)")
        
        // Parse the message as JSON
        if let data = message.data(using: .utf8) {
            do {
                if let json = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                    // Check the message type
                    if let type = json["type"] as? String {
                        switch type {
                        case "suggestions":
                            handleSuggestions(json)
                        case "conversation_context":
                            // Handle conversation context
                            if let context = json["context"] as? String {
                                sendConversationContext(context)
                            }
                        default:
                            NSLog("Unknown message type: \(type)")
                            logToFile("Unknown message type: \(type)")
                        }
                    } else {
                        NSLog("Message missing 'type' field")
                        logToFile("Message missing 'type' field")
                    }
                }
            } catch {
                NSLog("Error parsing JSON: \(error.localizedDescription)")
                logToFile("Error parsing JSON: \(error.localizedDescription)")
            }
        }
    }
    
    private func handleSuggestions(_ json: [String: Any]) {
        NSLog("Handling suggestions with JSON: \(json)")
        logToFile("Handling suggestions with JSON: \(json)")
        
        guard let suggestions = json["suggestions"] as? [String] else {
            NSLog("Suggestions message missing 'suggestions' array or not a string array")
            logToFile("Suggestions message missing 'suggestions' array or not a string array")
            
            // Try to log what type it actually is
            if let wrongType = json["suggestions"] {
                NSLog("'suggestions' is present but has wrong type: \(type(of: wrongType))")
                NSLog("Value: \(wrongType)")
                logToFile("'suggestions' is present but has wrong type: \(type(of: wrongType))")
                logToFile("Value: \(wrongType)")
            } else {
                NSLog("'suggestions' key is not present in the JSON")
                logToFile("'suggestions' key is not present in the JSON")
            }
            return
        }
        
        NSLog("Received \(suggestions.count) suggestions: \(suggestions)")
        logToFile("Received \(suggestions.count) suggestions: \(suggestions)")
        
        // Check if these are loading suggestions (to avoid replacing real suggestions with loading state)
        let isLoadingSuggestions = suggestions.contains { suggestion in
            suggestion.contains("Generating suggestions")
        }
        
        // Don't process if these are empty suggestions and we're generating
        if suggestions.isEmpty && isGeneratingSuggestions {
            NSLog("Received empty suggestions while generating, keeping loading state")
            logToFile("Received empty suggestions while generating, keeping loading state")
            return
        }
        
        // If we receive real suggestions (non-empty and not loading text), clear the generating state
        if !suggestions.isEmpty && !isLoadingSuggestions {
            NSLog("Received real suggestions, clearing generating state")
            logToFile("Received real suggestions, clearing generating state")
            isGeneratingSuggestions = false
        }
        
        // Only update if suggestions have changed (unless transitioning from loading to real suggestions)
        if suggestions != lastSuggestions || (isGeneratingSuggestions && !isLoadingSuggestions) {
            NSLog("Suggestions have changed, updating UI")
            logToFile("Suggestions have changed, updating UI")
            
            // Store the new suggestions (only if they're not loading suggestions)
            if !isLoadingSuggestions {
                lastSuggestions = suggestions
            }
            
            // Update the overlay window with the new suggestions
            // This needs to be done on the main thread
            DispatchQueue.main.async {
                NSLog("Posting UpdateSuggestions notification with \(suggestions.count) suggestions")
                logToFile("Posting UpdateSuggestions notification with \(suggestions.count) suggestions")
                
                NotificationCenter.default.post(
                    name: NSNotification.Name("UpdateSuggestions"),
                    object: nil,
                    userInfo: ["suggestions": suggestions, "isLoading": isLoadingSuggestions]
                )
                
                NSLog("Notification posted successfully")
                logToFile("Notification posted successfully")
            }
        } else {
            NSLog("Suggestions unchanged, skipping UI update")
            logToFile("Suggestions unchanged, skipping UI update")
        }
    }
    
    private func escapeJsonString(_ text: String) -> String {
        var escaped = text.replacingOccurrences(of: "\\", with: "\\\\")
        escaped = escaped.replacingOccurrences(of: "\"", with: "\\\"")
        escaped = escaped.replacingOccurrences(of: "\n", with: "\\n")
        escaped = escaped.replacingOccurrences(of: "\r", with: "\\r")
        escaped = escaped.replacingOccurrences(of: "\t", with: "\\t")
        return escaped
    }
    
    private func checkConversationChanges() {
        // Get the current conversation ID
        let currentConversationId = getCurrentConversationId()
        
        // Check if conversation has changed
        if currentConversationId != lastConversationId && !currentConversationId.isEmpty {
            NSLog("Conversation changed from '\(lastConversationId)' to '\(currentConversationId)'")
            logToFile("Conversation changed from '\(lastConversationId)' to '\(currentConversationId)'")
            
            // Update tracking
            lastConversationId = currentConversationId
            isGeneratingSuggestions = true
            
            // Clear backend suggestions immediately when conversation changes
            clearBackendSuggestions()
            
            // Clear previous suggestions to prevent stale suggestions from showing
            lastSuggestions = []
            NSLog("Cleared lastSuggestions due to conversation change")
            logToFile("Cleared lastSuggestions due to conversation change")
            
            // Immediately show loading state in overlay
            showLoadingState()
        }
    }
    
    private func clearBackendSuggestions() {
        NSLog("Clearing backend suggestions due to conversation change")
        logToFile("Clearing backend suggestions due to conversation change")
        
        let urlString = "http://localhost:5002/api/update-suggestions"
        guard let url = URL(string: urlString) else {
            NSLog("Error: Invalid URL for clearing backend suggestions")
            logToFile("Error: Invalid URL for clearing backend suggestions")
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload = ["suggestions": []]
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: payload)
            request.httpBody = jsonData
            
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    NSLog("Error clearing backend suggestions: \(error.localizedDescription)")
                    logToFile("Error clearing backend suggestions: \(error.localizedDescription)")
                } else {
                    NSLog("Backend suggestions cleared successfully")
                    logToFile("Backend suggestions cleared successfully")
                }
            }
            task.resume()
        } catch {
            NSLog("Error creating JSON payload for clearing suggestions: \(error.localizedDescription)")
            logToFile("Error creating JSON payload for clearing suggestions: \(error.localizedDescription)")
        }
    }
    
    private func getCurrentConversationId() -> String {
        // Execute the same command used in AppDelegate to get conversation ID
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        task.arguments = ["bash", "-c", "defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier | sed 's/^[^-]*-//' 2>/dev/null || echo ''"]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe // Capture errors too
        
        do {
            try task.run()
            task.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            
            return output
        } catch {
            NSLog("Error getting conversation ID: \(error)")
            logToFile("Error getting conversation ID: \(error)")
            return ""
        }
    }
    
    private func showLoadingState() {
        NSLog("Showing loading state in overlay")
        logToFile("Showing loading state in overlay")
        
        // Create a single loading message instead of three separate buttons
        let loadingSuggestions = [
            "Generating suggestions..."
        ]
        
        // Send loading state to overlay
        DispatchQueue.main.async {
            NotificationCenter.default.post(
                name: NSNotification.Name("UpdateSuggestions"),
                object: nil,
                userInfo: ["suggestions": loadingSuggestions, "isLoading": true]
            )
        }
    }
}
