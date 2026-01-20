// Package main implements a lightweight WhatsApp server that
// forwards encrypted chats and media to a Redis stream.
//
// The server exposes a small REST API:
//
//   /status      – returns the connection status for a session
//   /logout      – logs out a specific session
//   /media/…     – streams an image or video referenced by a message ID
//   /start-qr?session=<id>    – starts a session and streams the QR code that the
//                               user must scan to authenticate
//
// Redis is used as a message store.  Each user has its own stream
// (``messages:<userID>``) where every message is stored as a
// Redis Stream entry.
//
// Each session is stored as a file, the server automatically cleans up empty
// session files on startup.

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
    "crypto/sha256"
    "encoding/hex"

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


const (
    // DefaultRedisPort is the port used when ``REDIS_PORT`` is not set.
    DefaultRedisPort = "6379"

    // DefaultRedisHost is the host used when ``REDIS_HOST`` is not set.
    DefaultRedisHost = "localhost"

    // QRCodeExpiry is the maximum duration the client will wait for a
    // QR code to be generated before giving up.
    QRCodeExpiry = 10 * time.Second
)

// List of messages
type Response struct {
    Messages []Message `json:"messages"`
}

// Message represents an incoming chat message.  All fields
// that may be missing for a particular message type are represented by
// a zero value or a ``nil`` pointer (for optional values).
type Message struct {
    // Id is the Redis stream identifier of the message.
    Id string

    // From is the encrypted JID of the sender.
    From string

    // Chat is the encrypted JID of the chat (group or private).
    Chat string

    // Text holds the encrypted conversation or an empty string for
    // non‑text messages.
    Text string

    // Location is a pointer to a latitude,longitude string.  It is
    // ``nil`` if the message does not contain location data.
    Location *string

    // Date is the ISO‑8601 UTC timestamp of the message.
    Date string

    // Photo is a JSON‑encoded media reference to an image.
    Photo string

    // Video is a JSON‑encoded media reference to a video (not yet used).
    Video string

    // Audio is a JSON‑encoded media reference to an audio (not yet used).
    Audio string

    // File is the local file name for the downloaded media.
    File string
}

// MediaReference describes the metadata needed to re‑download and
// decrypt a media file.  The fields are base64 encoded because they
// come directly from the WhatsApp protocol buffer.
type MediaReference struct {
    // MediaKey is the base64 encoding of the 32‑byte media key.
    MediaKey string

    // DirectPath is the relative download URL for the media.
    DirectPath string

    // FileSHA256 is the base64 encoding of the file’s SHA‑256 hash.
    FileSHA256 string

    // FileEncSHA256 is the base64 encoding of the encrypted file’s
    // SHA‑256 hash.
    FileEncSHA256 string

    // FileLength is the length of the file in bytes.
    FileLength uint64

    // Mimetype is the media MIME type (e.g. “image/jpeg”).
    Mimetype string
}

// SessionMeta contains the runtime state of a WhatsApp session.
type SessionMeta struct {
    // QRCode is the raw QR string that the user scans to log in.
    QRCode string

    // Connected indicates whether the session is fully authenticated
    // and a JID is available.
    Connected bool

    // User is the SHA‑256 hash of the authenticated WhatsApp JID.
    User string

    // SessionID is the unique identifier for the session file.
    SessionID string
}

// Status
type Status struct {
    Status string `json:"status"`
    User string `json:"user"`
}

// Package‑level variables
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



// SearchLocation looks for a pair of decimal coordinates in the
// supplied string.  It returns the coordinates as a string
// (``latitude,longitude``) or an empty string if no match is found.
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

// ConvertToJSDateFormat converts a Go ``time.Time`` string to an
// ISO‑8601 UTC timestamp suitable for JavaScript.
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

// encrypt encrypts the supplied message using AES‑256 in GCM mode
// with the provided key.  The key must be exactly 32 bytes.
func encrypt(plaintext []byte, key []byte) (string) {
    block, err := aes.NewCipher(key)
    if err != nil {
        log.Printf("Encryption error: %v\n", err)
        return "1"
    }

    aesGCM, err := cipher.NewGCM(block)
    if err != nil {
        log.Printf("Encryption error: %v\n", err)
        return "2"
    }

    nonce := make([]byte, aesGCM.NonceSize())
    if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
        log.Printf("Encryption error: %v\n", err)
        return "3"
    }

    ciphertext := aesGCM.Seal(nil, nonce, plaintext, nil)
    payload := append(nonce, ciphertext...)
    encoded := base64.StdEncoding.EncodeToString(payload)

    return encoded
}

// hash returns the SHA‑256 digest of the supplied string as a
// hexadecimal representation.
func hash(plaintext string) (string) {
    hash := sha256.Sum256([]byte(plaintext))
    return hex.EncodeToString(hash[:])
}

// initClient creates or restores a WhatsApp session from the SQLite
// database identified by ``sessionID``.  The function configures the
// client, logs in, handles QR code generation and stores the
// session in the global maps.  It runs in a separate goroutine.
func initClient(sessionID string) {

    // Encryption key (32 bytes for AES-256)
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
        log.Printf("Failed to create sessions directory: %v\n", err)
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
                    userID := hash(client.Store.ID.User)
                    // Logout existing sessions of the same user
                    existingSessionId := getExistingSessionId(userID, sessionID)
                    if (existingSessionId != "") {
                        log.Printf("Logging out existing SessionId %s \n", existingSessionId)
                        logout(existingSessionId)
                    }
                    // Connected client session
                    sessionMetaMu.Lock()
                    sessionMeta[sessionID].Connected = true
                    sessionMeta[sessionID].User = userID
                    sessionMeta[sessionID].SessionID = sessionID
                    log.Printf("Session %s CONNECTED (1) ClientID: %s\n", sessionID,  userID)
                    sessionMetaMu.Unlock()
                    break
                }
            }
        }()
    } else {
        // Connected client session
        sessionMetaMu.Lock()
        userID := hash(client.Store.ID.User)
        sessionMeta[sessionID].Connected = true
        sessionMeta[sessionID].User = userID
        sessionMeta[sessionID].SessionID = sessionID
        log.Printf("Session %s CONNECTED (2) ClientID: %s\n", sessionID,  userID)
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

// getExistingSessionId scans all session files for the same
// authenticated user and returns the ID of a session that is not
// the current one.  It returns an empty string if no match is found.
func getExistingSessionId(userId string, currentSessionId string) (string) {
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
        log.Printf("Initializing new whatsmeow client (sessionID: %s)", sessionID)
        client := whatsmeow.NewClient(deviceStore, nil)

        // If same userId, return sessionID
        if (client.Store.ID != nil && hash(client.Store.ID.User) == userId && sessionID != currentSessionId) {
            return sessionID
        }
    }
    return ""

}

// cleanEmptySessions removes all session databases that have no
// authenticated user (i.e. the client’s Store.ID is ``nil``).
func cleanEmptySessions() {
    files, err := filepath.Glob("sessions/session_*.db")
    if err != nil {
        log.Printf("Failed to list DB files: %v", err)
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

        // Logout empty sessions
        if client.Store.ID == nil {
            log.Printf("Removing session: %s", sessionID)
            logout(sessionID);
        }
    }

}

// mediaReference serialises the given ImageMessage into a JSON‑encoded
// ``MediaReference`` string.  It is used when storing media URLs in
// Redis.
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

// decryptAndDownloadMedia downloads an encrypted media file and
// decrypts it using the supplied ``MediaReference``.  It returns the
// raw file bytes or an error if the download or decryption fails.
func decryptAndDownloadMedia(client *whatsmeow.Client, meta MediaReference) ([]byte, error) {
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
    data, err := client.Download(context.Background(), &imgMsg)
    if err != nil {
        log.Printf("download error: %v", err)
        return nil, fmt.Errorf("download error: %w", err)
    }
    return data, nil
}


/***
    HTTP handlers
***/

// mediaHandler serves an image, video or audio that belongs to a message.
// It looks up the media reference in Redis, re‑downloads the file
// from WhatsApp and streams the decrypted bytes to the client.
func mediaHandler(w http.ResponseWriter, r *http.Request) {

    log.Printf("mediaHandler: %s", r.URL.Path)

    // Get the full path (e.g., "/filename.jpg" or "/filename.mp4")
    urlPath := r.URL.Path

    // Extract the file name from the path
    msgID := ""
    mediaType := ""
    if strings.HasSuffix(urlPath, ".jpg") {
        msgID = strings.ReplaceAll(path.Base(urlPath), ".jpg", "")
        mediaType = "jpg"
    } else if strings.HasSuffix(urlPath, ".mp4") {
        msgID = strings.ReplaceAll(path.Base(urlPath), ".mp4", "")
        mediaType = "mp4"
    } else {
        log.Printf("unknown media format")
        return
    }

    user := r.URL.Query().Get("user")
    client := clients[user]
    ctx := context.Background()

    // Get media reference data from Redis
    res, _ := redisClient.XRange(ctx, fmt.Sprintf("messages:%s", user), msgID, msgID).Result()

    if (len(res) > 0) {
        mediaJSON, _ := "",""
        if (mediaType == "jpg") {
            mediaJSON, _ = res[0].Values["photo"].(string)
        }
        //  else {
        //     mediaJSON, _ = res[0].Values["video"].(string)
        // }

        // De-serialize media reference
        var meta MediaReference
        if err := json.Unmarshal([]byte(mediaJSON), &meta); err != nil {
            log.Printf("failed to unmarshal media message JSON: %v", err)
        }

        // Download decrypted media
        data, err := decryptAndDownloadMedia(client, meta)
        if err != nil {
            log.Printf("error downloading media: %v", err)
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
    } else {
        log.Printf("WARNING: no media reference")
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
            log.Printf("Location: %s\n", loc)
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
            log.Printf("Location: %s\n", location)
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
        userId := hash(client.Store.ID.User)
        redisClient.XAdd(ctx, &redis.XAddArgs{
            Stream: fmt.Sprintf("messages:%s", sessionID),
            ID:     streamID,
            Values: map[string]interface{}{
                "id":      streamID,
                "user":    userId,
                "from":    hash(message.From),
                "chat":    hash(message.Chat),
                "text":    message.Text,
                "date":    message.Date,
                "location": message.Location,
                "photo": message.Photo,
                "video": message.Video,
                "file": message.File,
            },
        })
        log.Printf("Saved received message")
    }

}

// reInitSessions scans the *sessions* directory for existing SQLite
// files and re‑initialises a WhatsApp client for each one in its
// own goroutine.  It is normally invoked from `main()` on startup
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

// qrHandler returns the QR code image for a given session.
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

// startHandler initiates a new WhatsApp session with the supplied
// ``session`` query parameter.  The response is a plain text
// acknowledgement.
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

// startAndQRHandler starts a session if necessary and streams the
// QR code image once it has been generated.  The QR is returned
// after at most 10 seconds, polling every 100 ms.
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

    timeout := time.After(QRCodeExpiry)
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

// statusHandler returns a JSON object describing the state of a
// session (``connected``, ``waiting`` or ``not_found``).
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

// logout terminates the WhatsApp session identified by ``sessionID``
// and deletes its database file.  It also removes the session from
// the global maps.
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

// logoutHandler receives a ``session`` query parameter and calls
// ``logout``.
func logoutHandler(w http.ResponseWriter, r *http.Request) {
   sessionID := r.URL.Query().Get("session")
   if sessionID == "" {
        http.Error(w, "Missing session ID", http.StatusBadRequest)
        return
    }
    logout(sessionID)
}

func main() {

    redis_host := os.Getenv("REDIS_HOST")
    if (redis_host == "") {
        redis_host = DefaultRedisHost
    }
    redis_port := os.Getenv("REDIS_PORT")
    if (redis_port == "") {
        redis_port = DefaultRedisPort
    }
    log.Printf("Connecting to Redis %s:%s \n", redis_host, redis_port)
    redisClient = redis.NewClient(&redis.Options{
        Addr: redis_host + ":" + redis_port,
    })

    // Re-init sessions
    cleanEmptySessions()
    reInitSessions()

    http.HandleFunc("/status", statusHandler)
    http.HandleFunc("/logout", logoutHandler)
    http.HandleFunc("/media/", mediaHandler)
    http.HandleFunc("/start-qr", startAndQRHandler)

    fmt.Println("Listening on :8001")
    log.Fatal(http.ListenAndServe(":8001", nil))
}

