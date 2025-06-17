import Foundation
import SQLite3

class MessageExtractor {
    // Path to the ChatDB
    private let chatDBPath = "~/Library/Messages/chat.db"
    
    // Get the active conversation ID using AppleScript and defaults command
    func getActiveConversationID() -> String? {
        let script = "do shell script \"defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier | sed \\\"s/^[^-]*-//\\\"\""
        
        let appleScript = NSAppleScript(source: script)
        var errorDict: NSDictionary?
        let result = appleScript?.executeAndReturnError(&errorDict)
        
        if let errorDict = errorDict {
            NSLog("Error getting active conversation ID: \(errorDict)")
            return nil
        }
        
        guard let rawID = result?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines), !rawID.isEmpty else {
            NSLog("Failed to get valid conversation ID")
            return nil
        }
        
        NSLog("Got active conversation ID: \(rawID)")
        return rawID
    }
    
    // Get recent messages from the active conversation
    func getRecentMessages(limit: Int = 10) -> [String: Any]? {
        guard let chatID = getActiveConversationID() else {
            NSLog("No active conversation ID found")
            return nil
        }
        
        // Expand the tilde in the path
        let expandedPath = NSString(string: chatDBPath).expandingTildeInPath
        
        // Create a copy of the database to avoid locking issues
        let tempDBPath = NSTemporaryDirectory() + "temp_chat_\(UUID().uuidString).db"
        
        do {
            // Copy the database
            try FileManager.default.copyItem(atPath: expandedPath, toPath: tempDBPath)
            
            // Open the database
            var db: OpaquePointer?
            guard sqlite3_open(tempDBPath, &db) == SQLITE_OK else {
                NSLog("Error opening database")
                return nil
            }
            defer {
                sqlite3_close(db)
                try? FileManager.default.removeItem(atPath: tempDBPath)
            }
            
            // Get chat information and messages
            let chatInfo = getChatInfo(db: db, chatID: chatID)
            let messages = getMessages(db: db, chatID: chatID, limit: limit)
            
            return [
                "chat_id": chatID,
                "chat_info": chatInfo ?? [:],
                "messages": messages
            ]
        } catch {
            NSLog("Error accessing chat database: \(error)")
            return nil
        }
    }
    
    // Get chat information (name, participants)
    private func getChatInfo(db: OpaquePointer?, chatID: String) -> [String: Any]? {
        let query = """
            SELECT c.display_name, h.id
            FROM chat c
            JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
            JOIN handle h ON chj.handle_id = h.ROWID
            WHERE c.chat_identifier = ?
        """
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            NSLog("Error preparing chat info query")
            return nil
        }
        defer {
            sqlite3_finalize(statement)
        }
        
        sqlite3_bind_text(statement, 1, chatID, -1, nil)
        
        var chatName: String?
        var participants: [String] = []
        
        while sqlite3_step(statement) == SQLITE_ROW {
            // Get chat name if available
            if let namePtr = sqlite3_column_text(statement, 0) {
                chatName = String(cString: namePtr)
            }
            
            // Get participant ID
            if let idPtr = sqlite3_column_text(statement, 1) {
                let participantID = String(cString: idPtr)
                participants.append(participantID)
            }
        }
        
        return [
            "name": chatName ?? "Unknown",
            "participants": participants
        ]
    }
    
    // Get recent messages from the chat
    private func getMessages(db: OpaquePointer?, chatID: String, limit: Int) -> [[String: Any]] {
        let query = """
            SELECT m.ROWID, m.text, m.is_from_me, m.date, h.id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat c ON cmj.chat_id = c.ROWID
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE c.chat_identifier = ?
            ORDER BY m.date DESC
            LIMIT ?
        """
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            NSLog("Error preparing messages query")
            return []
        }
        defer {
            sqlite3_finalize(statement)
        }
        
        sqlite3_bind_text(statement, 1, chatID, -1, nil)
        sqlite3_bind_int(statement, 2, Int32(limit))
        
        var messages: [[String: Any]] = []
        
        while sqlite3_step(statement) == SQLITE_ROW {
            var message: [String: Any] = [:]
            
            // Message ID
            message["id"] = sqlite3_column_int64(statement, 0)
            
            // Message text
            if let textPtr = sqlite3_column_text(statement, 1) {
                message["text"] = String(cString: textPtr)
            } else {
                message["text"] = ""
            }
            
            // Is from me
            message["is_from_me"] = sqlite3_column_int(statement, 2) == 1
            
            // Date (convert from Mac absolute time to Unix timestamp)
            let macTime = sqlite3_column_int64(statement, 3)
            // Mac absolute time starts at Jan 1, 2001, while Unix time starts at Jan 1, 1970
            // The difference is 978307200 seconds
            let unixTime = Double(macTime) / 1_000_000_000 + 978307200
            message["date"] = unixTime
            
            // Sender ID
            if let senderPtr = sqlite3_column_text(statement, 4) {
                message["sender_id"] = String(cString: senderPtr)
            } else {
                message["sender_id"] = "me"
            }
            
            messages.append(message)
        }
        
        // Reverse to get chronological order
        return messages.reversed()
    }
    
    // Format messages into a conversation context string
    func getConversationContext() -> String {
        guard let data = getRecentMessages(limit: 10) else {
            return "No conversation found"
        }
        
        let messages = data["messages"] as? [[String: Any]] ?? []
        let chatInfo = data["chat_info"] as? [String: Any] ?? [:]
        let chatName = chatInfo["name"] as? String ?? "Unknown"
        
        var context = "Conversation with \(chatName):\n\n"
        
        for message in messages {
            let isFromMe = message["is_from_me"] as? Bool ?? false
            let text = message["text"] as? String ?? ""
            let sender = isFromMe ? "Me" : chatName
            
            context += "\(sender): \(text)\n"
        }
        
        return context
    }
}
