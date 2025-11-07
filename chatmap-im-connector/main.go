package main

import (
    "context"
    "encoding/json"
    "fmt"
    "regexp"
    "strconv"
    "io"
    "log"
    "net/http"
    "path"
    "path/filepath"
    "strings"
    "os"
    "sync"
    "time"
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
    "encoding/base64"

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
    Messages []Message `json:"messages"`
}

// Message
type Message struct {
    Id string `json:"id"`
    From string `json:"from"`
    Chat string `json:"chat"`
    Text string `json:"text"`
    Location *string `json:"location"`
    Date string `json:"date"`
    Photo string `json:"photo"`
    Video string `json:"video"`
    File string `json:"file"`
}

// MediaReference
type MediaReference struct {
    MediaKey   string `json:"media_key"`
    DirectPath string `json:"direct_path"`
    FileSHA256 string `json:"file_sha256"`
    FileEncSHA256 string `json:"file_sha256"`
    FileLength uint64 `json:"file_length"`
    Mimetype   string `json:"mimetype"`
}

// Session
type SessionMeta struct {
    QRCode   string
    Connected bool
    User string
    SessionID string
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

var locationPattern = regexp.MustCompile(`[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?).*`)

// Searches for a lat/lon pair
func SearchLocation(messageText string) (string, error) {
    if messageText == "" {
        return "", nil
    }

    // Grab the full matched substring
    match := locationPattern.FindString(messageText)
    if match == "" {
        return "", nil // no coordinates
    }

    // Split on the comma
    parts := strings.SplitN(match, ",", 2)
    if len(parts) != 2 {
        return "", fmt.Errorf("unexpected match format: %q", match)
    }

    // Convert both parts to float64
    lat, err := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
    if err != nil {
        return "", fmt.Errorf("invalid latitude %q: %w", parts[0], err)
    }
    lon, err := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
    if err != nil {
        return "", fmt.Errorf("invalid longitude %q: %w", parts[1], err)
    }

    return fmt.Sprintf("%g,%g", lat, lon), nil
}

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

// Encript text (for messages)
func encrypt(plaintext []byte, key []byte) (string) {
    block, err := aes.NewCipher(key)
    if err != nil {
        fmt.Printf("Encryption error: %v\n", err)
        return "1"
    }

    aesGCM, err := cipher.NewGCM(block)
    if err != nil {
        fmt.Printf("Encryption error: %v\n", err)
        return "2"
    }

    nonce := make([]byte, aesGCM.NonceSize())
    if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
        fmt.Printf("Encryption error: %v\n", err)
        return "3"
    }

    ciphertext := aesGCM.Seal(nil, nonce, plaintext, nil)
    payload := append(nonce, ciphertext...)
    encoded := base64.StdEncoding.EncodeToString(payload)

    return encoded
}

// Initialize client with sessionId
func initClient(sessionID string) {

    // Encryption key
    enc_key := os.Getenv("CHATMAP_ENC_KEY")
    if enc_key == "" {
        enc_key = "0123456789ABCDEF0123456789ABCDEF"
        log.Printf("WARNING: CHATMAP_ENC_KEY environment variable not set")
    }

    log.Printf("Init session: %s \n", sessionID)

    // -- DB Storage --

    // Create new DB storage
    ctx := context.Background()
    store.DeviceProps.PlatformType = waProto.DeviceProps_DESKTOP.Enum()
    store.DeviceProps.Os = proto.String("ChatMap")

    // Sessions directory
    if err := os.MkdirAll("sessions", 0755); err != nil {
        fmt.Printf("Failed to create sessions directory: %v\n", err)
        return
    }

    // Open DB
    path := fmt.Sprintf("file:sessions/session_%s.db?_foreign_keys=on", sessionID)
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
        log.Printf("[GetQRChannel]")
        go func() {
            for evt := range qrChan {
                log.Printf("[QR Event]: %s \n", evt.Event)
                if evt.Event == "code" {
                    sessionMetaMu.Lock()
                    sessionMeta[sessionID].QRCode = evt.Code
                    sessionMetaMu.Unlock()
                    log.Printf("QR code generated sucessfully")
                } else if evt.Event == "success" {
                    // Logout existing sessions of the same user
                    existingSessionId := getExistingSessionId(client.Store.ID.User, sessionID)
                    if (existingSessionId != "") {
                        log.Printf("Logout existing SessionId %s \n", existingSessionId)
                        logout(existingSessionId)
                    }
                    // Connected client session
                    sessionMetaMu.Lock()
                    sessionMeta[sessionID].Connected = true
                    sessionMeta[sessionID].User = client.Store.ID.User
                    sessionMeta[sessionID].SessionID = sessionID
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
        sessionMeta[sessionID].SessionID = sessionID
        log.Printf("Session %s CONNECTED (2) ClientID: %s\n", sessionID,  client.Store.ID.User)
        sessionMetaMu.Unlock()
    }

    // Handle incoming messages
    client.AddEventHandler(func(evt interface{}) {
        switch v := evt.(type) {
        case *events.Message:
            go handleMessage(sessionID, v, enc_key)
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

// Get previously created sessions for the same phone number
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
        path := fmt.Sprintf("file:sessions/session_%s.db?_foreign_keys=on", sessionID)
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

// Build serialized media reference
func mediaReference(msg *waProto.ImageMessage) string {
    ref := MediaReference{
        MediaKey:   base64.StdEncoding.EncodeToString(msg.GetMediaKey()),
        DirectPath: msg.GetDirectPath(),
        FileSHA256: base64.StdEncoding.EncodeToString(msg.GetFileSHA256()),
        FileLength: msg.GetFileLength(),
        Mimetype:   msg.GetMimetype(),
    }
    data, _ := json.Marshal(ref)
    return string(data)
}

// TODO: support video
// Download and decrypt media file using reference data
func downloadMediaFromMsg(client *whatsmeow.Client, meta MediaReference) ([]byte, error) {
    // Decode metadata
    mediaKey, err := base64.StdEncoding.DecodeString(meta.MediaKey)
    if err != nil {
        return nil, fmt.Errorf("failed to decode MediaKey: %w", err)
    }
    fileSHA256, err := base64.StdEncoding.DecodeString(meta.FileSHA256)
    if err != nil {
        return nil, fmt.Errorf("failed to decode FileSHA256: %w", err)
    }
    fileEncSHA256, err := base64.StdEncoding.DecodeString(meta.FileEncSHA256)
    if err != nil {
        return nil, fmt.Errorf("failed to decode FileEncSHA256: %w", err)
    }
    // Create ImageMessage from metadata
    imgMsg := waProto.ImageMessage{
        MediaKey:   mediaKey,
        DirectPath: &meta.DirectPath,
        FileSHA256: fileSHA256,
        FileEncSHA256: fileEncSHA256,
        FileLength: &meta.FileLength,
        Mimetype:   &meta.Mimetype,
    }
    // Download & decrypt
    // FIXME: client is nil
    data, err := client.Download(context.Background(), &imgMsg)
    if err != nil {
        log.Printf("download error: %w", err)
        return nil, fmt.Errorf("download error: %w", err)
    }
    return data, nil
}

// Getr session by user
func getSessionByUser(user string) (*SessionMeta, bool) {
    sessionMetaMu.RLock()
    defer sessionMetaMu.RUnlock()

    for _, meta := range sessionMeta {
        if meta.User == user {
            return meta, true
        }
    }
    return nil, false
}

// Get a message id and a sessionID and serves a media file
func mediaHandler(w http.ResponseWriter, r *http.Request) {

    // Get the full path (e.g., "/filename.jpg" or "/filename.mp4")
    urlPath := r.URL.Path

    // Extract the file name from the path
    msgID := ""
    mediaType := ""
    if strings.HasSuffix(urlPath, ".jpg") {
        strings.ReplaceAll(path.Base(urlPath), ".jpg", "")
        mediaType = "jpg"
    } else if strings.HasSuffix(urlPath, ".mp4") {
        strings.ReplaceAll(path.Base(urlPath), ".mp4", "")
        mediaType = "mp4"
    } else {
        log.Printf("unknown media format")
        return
    }

    user := r.URL.Query().Get("user")
    session, _ := getSessionByUser(user)
    client := clients[session.SessionID]
    ctx := context.Background()

    // Get media reference data from Redis
    res, _ := redisClient.XRange(ctx, fmt.Sprintf("messages:%s", user), msgID, msgID).Result()

    if (len(res) > 0) {
        mediaJSON, _ := "",""
        if if (mediaType == "jpg") {
            mediaJSON, _ = res[0].Values["photo"].(string)
        }
        //  else {
        //     mediaJSON, _ = res[0].Values["video"].(string)
        // }

        // De-serialize media reference
        var meta MediaReference
        if err := json.Unmarshal([]byte(mediaJSON), &meta); err != nil {
            log.Printf("failed to unmarshal media message JSON: %w", err)
        }

        // Download decrypted media
        data, err := downloadMediaFromMsg(client, meta)
        if err != nil {
            log.Printf("error downloading media: %w", err)
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        if (mediaType == "jpg") {
            w.Header().Set("Content-Type", "image/jpeg")
        }
        //  else {
        //     w.Header().Set("Content-Type", "video/mp4")
        // }
        w.WriteHeader(http.StatusOK)
        _, _ = w.Write(data)
    }
}

// Handle incoming messages
func handleMessage(sessionID string, v *events.Message, enc_key string) {
    chat:= v.Info.Chat.String()
    if (chat == "status@broadcast") {
        return;
    }
    ctx := context.Background()
    msg := v.Message
    date := ConvertToJSDateFormat(v.Info.Timestamp.String())
    hasContent := false

    message := Message{
        From: v.Info.Sender.String(),
        Chat: v.Info.Chat.String(),
        Date: date,
    }

    client := clients[sessionID]

    // Message ID
    parsedTime, err := time.Parse(time.RFC3339, message.Date)
    if err != nil {
        log.Fatalf("Failed to parse time: %v", err)
    }
    streamID := fmt.Sprintf("%d-0", parsedTime.UnixMilli())

    // Text message
    if msg.GetConversation() != "" {
        message_text := msg.GetConversation()
        loc, _ := SearchLocation(message_text)
        if loc != "" {
            location := loc
            message.Location = &location
            fmt.Printf("Location: %s\n", loc)
            hasContent = true
        } else {
            enc_message_text := encrypt([]byte(message_text), []byte(enc_key))
            message.Text = enc_message_text
            hasContent = true
        }

    // Location
    } else if msg.LocationMessage != nil {
        loc := msg.GetLocationMessage()
        if loc != nil {
            location := fmt.Sprintf("%.5f,%.5f", loc.GetDegreesLatitude(), loc.GetDegreesLongitude())
            fmt.Printf("Location: %s\n", location)
            message.Location = &location
            hasContent = true
        }

    // Media (image or video)
    } else if msg.ImageMessage != nil || msg.VideoMessage != nil {
        if msg.ImageMessage != nil {
            image := msg.GetImageMessage()
            message.Photo = mediaReference(image)
            message.File = fmt.Sprintf("%s.jpg", streamID)
            hasContent = true
        }
        //  else {
        //     video := msg.GetVideoMessage()
        //     message.Video = mediaReference(video)
        //     message.File = fmt.Sprintf("%s.mp4", streamID)
        // }
    }

    // Save data into Redis queue
    if (hasContent) {
        redisClient.XAdd(ctx, &redis.XAddArgs{
            Stream: fmt.Sprintf("messages:%s", client.Store.ID.User),
            ID:     streamID,
            Values: map[string]interface{}{
                "id":      streamID,
                "user":    client.Store.ID.User,
                "from":    message.From,
                "chat":    message.Chat,
                "text":    message.Text,
                "date":    message.Date,
                "location": message.Location,
                "photo": message.Photo,
                "video": message.Video,
                "file": message.File,
            },
        })
        log.Printf("Saved received message from: %s", message.From)
    }

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
        log.Printf("QR not generated")
        http.Error(w, "QR not generated", http.StatusNotFound)
        return
    }

    png, err := qrcode.Encode(meta.QRCode, qrcode.Medium, 256)
    if err != nil {
        log.Printf("QR encode error")
        http.Error(w, "QR encode error", http.StatusInternalServerError)
        return
    }

    log.Printf("Returning QR")
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

// Get a list of messages
func messagesHandler(w http.ResponseWriter, r *http.Request) {
    user := r.URL.Query().Get("user")
    ctx := context.Background()
    // Get media reference data from Redis
     res, _ := redisClient.XRange(ctx, fmt.Sprintf("messages:%s", user), "-", "+").Result()
     var messages []Message

    for _, item := range res {
        vals := item.Values
        get := func(key string) string {
            if v, ok := vals[key]; ok {
                if s, ok := v.(string); ok {
                    return s
                }
            }
            return ""
        }
        location := get("location")
        var locationPtr *string
        if location != "" {
            locationPtr = &location
        }

        message := Message{
            Id:       get("id"),
            From:     get("from"),
            Chat:     get("chat"),
            Text:     get("text"),
            Location: locationPtr,
            Date:     get("date"),
            Photo:    get("photo"),
            Video:    get("video"),
            File:     get("file"),
        }
        messages = append(messages, message)
    }

    response := Response{Messages: messages}
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}

func main() {

    redis_host := os.Getenv("REDIS_HOST")
    if (redis_host == "") {
        redis_host = "localhost"
    }
    redis_port := os.Getenv("REDIS_PORT")
    if (redis_port == "") {
        redis_port = "6379"
    }
    fmt.Printf("Connecting to Redis %s:%s \n", redis_host, redis_port)
    redisClient = redis.NewClient(&redis.Options{
        Addr: redis_host + ":" + redis_port,
    })

    // Re-init sessions
    reInitSessions()

    // FOR DEBUGGING
    // http.HandleFunc("/sessions", sessionsHandler)
    // http.HandleFunc("/messages", messagesHandler)

    http.HandleFunc("/status", statusHandler)
    http.HandleFunc("/logout", logoutHandler)
    http.HandleFunc("/media/", mediaHandler)
    http.HandleFunc("/start-qr", startAndQRHandler)

    fmt.Println("Listening on :8001")
    log.Fatal(http.ListenAndServe(":8001", nil))
}

