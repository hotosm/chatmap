package main

import (
    "context"
    "encoding/json"
    "fmt"
    "io"
    "log"
    "net/http"
    "path/filepath"
    "strings"
    "os"
    "sync"
    "time"

    "google.golang.org/protobuf/proto"

    _ "github.com/mattn/go-sqlite3"
    "go.mau.fi/whatsmeow"
    "go.mau.fi/whatsmeow/store"
    "go.mau.fi/whatsmeow/store/sqlstore"
    "go.mau.fi/whatsmeow/types/events"
    "github.com/redis/go-redis/v9"
    qrcode "github.com/skip2/go-qrcode"
    waLog "go.mau.fi/whatsmeow/util/log"
    waProto "go.mau.fi/whatsmeow/binary/proto"
)

// List of messages
type Response struct {
    Messages []string `json:"messages"`
}

// Message
type Message struct {
    From string `json:"from"`
    Chat string `json:"from"`
    Text string `json:"text"`
    Location *string `json:"text"`
    Date string `json:"date"`
    Photo string `json:"photo"`
    Video string `json:"video"`
}

// Session
type SessionMeta struct {
    QRCode   string
    Connected bool
    User string
}

// Status
type Status struct {
    Status string `json:"status"`
    User string `json:"user"`
}

var (
    clients       = make(map[string]*whatsmeow.Client)
    clientsMu     sync.RWMutex
    sessionMeta   = make(map[string]*SessionMeta)
    sessionMetaMu sync.RWMutex

    response     Response
    mu           sync.Mutex
    redisClient  *redis.Client
)

// Converts a datetime string into a JavaScript compatible one
func ConvertToJSDateFormat(input string) (string) {
    if len(input) < 25 {
        return ""
    }

    // Remove timezone (" -03")
    cleaned := input[:25]
    layoutIn := "2006-01-02 15:04:05 -0700"

    t, err := time.Parse(layoutIn, cleaned)
    if err != nil {
        return ""
    }

    return t.Format(time.RFC3339)
}

// Initialize client with sessionId
func initClient(sessionID string) {

    log.Printf("Init session: %s \n", sessionID)

    // -- DB Storage --

    // Create new DB storage
    ctx := context.Background()
    store.DeviceProps.PlatformType = waProto.DeviceProps_DESKTOP.Enum()
    store.DeviceProps.Os = proto.String("ChatMap")

    var path string
    // Sessions directory
    if err := os.MkdirAll("sessions", 0755); err != nil {
        fmt.Printf("Failed to create sessions directory: %v\n", err)
        return
    }

    // Open DB
    path = fmt.Sprintf("file:sessions/session_%s.db?_foreign_keys=on", sessionID)
    container, err := sqlstore.New(ctx, "sqlite3", path, waLog.Noop)
    if err != nil {
        log.Fatalf("failed to open db: %v", err)
    }

    // -- Device Store --

    // Get device from storage
    deviceStore, err := container.GetFirstDevice(ctx)
    if err != nil {
        log.Fatalf("failed to get device: %v", err)
    }

    // Initialize new whatsmeow client
    log.Printf("Initializing client for session: %s ... \n", sessionID)
    client := whatsmeow.NewClient(deviceStore, nil)

    // Store client session in memory
    clientsMu.Lock()
    clients[sessionID] = client
    clientsMu.Unlock()
    sessionMetaMu.Lock()
    sessionMeta[sessionID] = &SessionMeta{}
    sessionMetaMu.Unlock()

    if client.Store.ID == nil {
        // If no client store, get QR
        log.Printf("No client store found for session: %s , returning QR \n", sessionID)
        qrChan, _ := client.GetQRChannel(context.Background())
        go func() {
            for evt := range qrChan {
                if evt.Event == "code" {
                    sessionMetaMu.Lock()
                    sessionMeta[sessionID].QRCode = evt.Code
                    sessionMetaMu.Unlock()
                } else if evt.Event == "success" {
                    existingSessionId := getExistingSessionId(client.Store.ID.User, sessionID)
                    if (existingSessionId != "") {
                        log.Printf("Logout existing SessionId %s \n", existingSessionId)
                        logout(existingSessionId)
                    }
                    sessionMetaMu.Lock()
                    sessionMeta[sessionID].Connected = true
                    sessionMeta[sessionID].User = client.Store.ID.User
                    log.Printf("Session %s CONNECTED (1) ClientID: %s\n", sessionID,  client.Store.ID.User)
                    sessionMetaMu.Unlock()
                    break
                }
            }
        }()
    } else {
        // Connected client session
        sessionMetaMu.Lock()
        sessionMeta[sessionID].Connected = true
        sessionMeta[sessionID].User = client.Store.ID.User
        log.Printf("Session %s CONNECTED (2) ClientID: %s\n", sessionID,  client.Store.ID.User)
        sessionMetaMu.Unlock()
    }

    // Handle incoming messages
    client.AddEventHandler(func(evt interface{}) {
        switch v := evt.(type) {
        case *events.Message:
            go handleMessage(sessionID, v)
        }
    })

    // Try to connect client
    go func() {
        err := client.Connect()
        if err != nil {
            log.Fatalf("failed to connect: %v", err)
        }
    }()
}

func getExistingSessionId(phoneNumber string, currentSessionId string) (string) {
    files, err := filepath.Glob("sessions/session_*.db")
    if err != nil {
        log.Printf("Failed to list DB files: %v", err)
        return ""
    }
    for _, file := range files {
        sessionID := strings.TrimSuffix(strings.TrimPrefix(file, "sessions/session_"), ".db")

        // Create new DB storage
        ctx := context.Background()

        // Open DB
        var path string
        path = fmt.Sprintf("file:sessions/session_%s.db?_foreign_keys=on", sessionID)
        container, err := sqlstore.New(ctx, "sqlite3", path, waLog.Noop)
        if err != nil {
            log.Fatalf("failed to open db: %v", err)
        }

        // Get device from storage
        deviceStore, err := container.GetFirstDevice(ctx)
        if err != nil {
            log.Fatalf("failed to get device: %v", err)
        }

        // Initialize whatsmeow client
        client := whatsmeow.NewClient(deviceStore, nil)

        // If same phone number, return sessionID
        if (client.Store.ID != nil && client.Store.ID.User == phoneNumber && sessionID != currentSessionId) {
            return sessionID
        }
    }
    return ""

}

// Handle incoming messages
func handleMessage(sessionID string, v *events.Message) {
    ctx := context.Background()
    msg := v.Message
    date := ConvertToJSDateFormat(v.Info.Timestamp.String())

    log.Printf("Message received from: %s", v.Info.Sender.String())

    message := Message{
        From: v.Info.Sender.String(),
        Chat: v.Info.Chat.String(),
        Date: date,
    }

    client := clients[sessionID]

    // Text message
    if msg.GetConversation() != "" {
        message.Text = msg.GetConversation()

    // Location
    } else if msg.LocationMessage != nil {
        loc := msg.GetLocationMessage()
        if loc != nil {
            location := fmt.Sprintf("%.5f,%.5f", loc.GetDegreesLatitude(), loc.GetDegreesLongitude())
            message.Location = &location
        }

    // FIXME: media disabled, encryption and file management is needed

    // Media (image or video)
    // } else if msg.ImageMessage != nil || msg.VideoMessage != nil {

    //     var media whatsmeow.DownloadableMessage
    //     var fileName string

    //     // Create "media" directory if it doesn't exist
    //     if err := os.MkdirAll("media", 0755); err != nil {
    //         fmt.Printf("Failed to create media directory: %v\n", err)
    //         return
    //     }

    //     if msg.ImageMessage != nil {
    //         media = msg.GetImageMessage()
    //         fileName = fmt.Sprintf("%s.jpg", v.Info.ID)
    //         message.Photo = fileName
    //     } else {
    //         media = msg.GetVideoMessage()
    //         fileName = fmt.Sprintf("%s.mp4", v.Info.ID)
    //         message.Video = fileName
    //     }

    //     // Download & decrypt
    //     data, err := client.Download(context.Background(), media)
    //     if err != nil {
    //         fmt.Printf("Failed to download media: %v\n", err)
    //         return
    //     }

    //     // Save media to a file
    //     filePath := "media/" + fileName
    //     if err := os.WriteFile(filePath, data, 0644); err != nil {
    //         fmt.Printf("Failed to save media: %v\n", err)
    //         return
    //     }
    }

    // Save data into Redis queue
    parsedTime, err := time.Parse(time.RFC3339, message.Date)
    if err != nil {
        log.Fatalf("Failed to parse time: %v", err)
    }
    streamID := fmt.Sprintf("%d-0", parsedTime.UnixMilli())

    redisClient.XAdd(ctx, &redis.XAddArgs{
        Stream: fmt.Sprintf("wa-messages:%s", sessionID),
        ID:     streamID,
        Values: map[string]interface{}{
            "user":    client.Store.ID.User,
            "from":    message.From,
            "chat":    message.Chat,
            "text":    message.Text,
            "date":    message.Date,
            "location": message.Location,
            "photo": message.Photo,
            "video": message.Video,
        },
    })

}

// Re-init sessions
func reInitSessions() {
    files, err := filepath.Glob("sessions/session_*.db")
    if err != nil {
        log.Printf("Failed to list DB files: %v", err)
        return
    }
    for _, file := range files {
        sessionId := strings.TrimSuffix(strings.TrimPrefix(file, "sessions/session_"), ".db")
        go initClient(sessionId)
    }
}

// Handler for QR endpoint
func qrHandler(w http.ResponseWriter, r *http.Request) {
    sessionID := r.URL.Query().Get("session")
    if sessionID == "" {
        log.Printf("Missing session Id: %s \n", sessionID)
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }

    sessionMetaMu.RLock()
    meta, ok := sessionMeta[sessionID]
    sessionMetaMu.RUnlock()

    if !ok || meta.QRCode == "" {
        http.Error(w, "QR not generated", http.StatusNotFound)
        return
    }

    png, err := qrcode.Encode(meta.QRCode, qrcode.Medium, 256)
    if err != nil {
        http.Error(w, "QR encode error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "image/png")
    w.Write(png)
}

// Handler for start session endpoint
func startHandler(w http.ResponseWriter, r *http.Request) {
    sessionID := r.URL.Query().Get("session")
    if sessionID == "" {
        log.Printf("Missing session Id: %s \n", sessionID)
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }

    clientsMu.RLock()
    _, exists := clients[sessionID]
    clientsMu.RUnlock()

    if exists {
        fmt.Fprintf(w, "Session %s already initialized\n", sessionID)
        return
    }

    go initClient(sessionID)
    fmt.Fprintf(w, "Initializing session %s\n", sessionID)
}

// Handler for start session and QR endpoint
func startAndQRHandler(w http.ResponseWriter, r *http.Request) {
    sessionID := r.URL.Query().Get("session")
    if sessionID == "" {
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }

    clientsMu.RLock()
    _, exists := clients[sessionID]
    clientsMu.RUnlock()

    if !exists {
        go initClient(sessionID)
    }

    timeout := time.After(10 * time.Second)
    ticker := time.NewTicker(100 * time.Millisecond)
    defer ticker.Stop()

    for {
        select {
        case <-timeout:
            http.Error(w, "QR not generated in time", http.StatusNotFound)
            return
        case <-ticker.C:
            sessionMetaMu.RLock()
            meta, ok := sessionMeta[sessionID]
            sessionMetaMu.RUnlock()
            if ok && meta.QRCode != "" {
                png, err := qrcode.Encode(meta.QRCode, qrcode.Medium, 256)
                if err != nil {
                    http.Error(w, "QR encode error", http.StatusInternalServerError)
                    return
                }
                w.Header().Set("Content-Type", "image/png")
                w.Write(png)
                return
            }
        }
    }
}

// Handler for session status endpoint
func statusHandler(w http.ResponseWriter, r *http.Request) {
    sessionID := r.URL.Query().Get("session")
    if sessionID == "" {
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }

    sessionMetaMu.RLock()
    meta, ok := sessionMeta[sessionID]
    sessionMetaMu.RUnlock()

    w.Header().Set("Content-Type", "application/json")

    status := Status{}

    if !ok {
        status.Status = "not_found"
    } else if meta.Connected {
        status.Status = "connected"
        status.User = meta.User
    } else {
        status.Status = "waiting"
    }
    json.NewEncoder(w).Encode(status)
}

// Handler for list of sessions endpoint
func sessionsHandler(w http.ResponseWriter, r *http.Request) {
    sessionMetaMu.RLock()
    defer sessionMetaMu.RUnlock()

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(sessionMeta)
}

// Logout session
func logout(sessionID string) {
    ctx := context.Background()
    container, _ := sqlstore.New(ctx, "sqlite3", fmt.Sprintf("file:sessions/session_%s.db?_foreign_keys=on", sessionID), waLog.Noop)
    deviceStore, _ := container.GetFirstDevice(ctx)
    client := whatsmeow.NewClient(deviceStore, nil)
    err := client.Connect()
    if err == nil {
        client.Logout(ctx)
        log.Printf("Logged out old session %s sessionID", sessionID)
    }

    path := fmt.Sprintf("./sessions/session_%s.db", sessionID)
    e := os.Remove(path)
    if e != nil {
        log.Printf("Error removing %s", path)
    }

    clientsMu.Lock()
    client, exists := clients[sessionID]
    if exists {
        client.Disconnect()
        client.Logout(ctx)
        delete(clients, sessionID)
    }
    clientsMu.Unlock()

}

// Handler for logout session endpoint
func logoutHandler(w http.ResponseWriter, r *http.Request) {
   sessionID := r.URL.Query().Get("session")
   if sessionID == "" {
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }
    logout(sessionID)
}

// Handler for media file serving endpoint
func mediaHandler(w http.ResponseWriter, r *http.Request) {
    filename := r.URL.Query().Get("file")

    if filename == "" {
        http.Error(w, "Missing 'file' query parameter", http.StatusBadRequest)
        return
    }

    // Prevent directory traversal
    cleanFilename := filepath.Clean(filename)
    fullPath := filepath.Join("media", cleanFilename)

    file, err := os.Open(fullPath)
    if err != nil {
        http.Error(w, "File not found", http.StatusNotFound)
        return
    }
    defer file.Close()

    ext := strings.ToLower(filepath.Ext(cleanFilename))
    switch ext {
    case ".jpg", ".jpeg":
        w.Header().Set("Content-Type", "image/jpeg")
    case ".mp4":
        w.Header().Set("Content-Type", "video/mp4")
    default:
        http.Error(w, "Unsupported file type", http.StatusUnsupportedMediaType)
        return
    }

    io.Copy(w, file)
}

func main() {
    redisClient = redis.NewClient(&redis.Options{
        Addr: "localhost:6379",
    })

    // Re-init sessions
    reInitSessions()

    http.HandleFunc("/sessions", sessionsHandler)
    http.HandleFunc("/status", statusHandler)
    http.HandleFunc("/logout", logoutHandler)
    http.HandleFunc("/media", mediaHandler)
    http.HandleFunc("/start-qr", startAndQRHandler)

    fmt.Println("Listening on :8001")
    log.Fatal(http.ListenAndServe(":8001", nil))
}

