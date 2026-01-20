

CONSTANTS

const (
	// DefaultRedisPort is the port used when ``REDIS_PORT`` is not set.
	DefaultRedisPort = "6379"

	// DefaultRedisHost is the host used when ``REDIS_HOST`` is not set.
	DefaultRedisHost = "localhost"

	// QRCodeExpiry is the maximum duration the client will wait for a
	// QR code to be generated before giving up.
	QRCodeExpiry = 10 * time.Second
)

FUNCTIONS

func ConvertToJSDateFormat(input string) string
    ConvertToJSDateFormat converts a Go “time.Time“ string to an ISO‑8601 UTC
    timestamp suitable for JavaScript.

func SearchLocation(messageText string) (string, error)
    SearchLocation looks for a pair of decimal coordinates in the supplied
    string. It returns the coordinates as a string (“latitude,longitude“) or an
    empty string if no match is found.


TYPES

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
    MediaReference describes the metadata needed to re‑download and decrypt a
    media file. The fields are base64 encoded because they come directly from
    the WhatsApp protocol buffer.

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
    Message represents an incoming chat message. All fields that may be missing
    for a particular message type are represented by a zero value or a “nil“
    pointer (for optional values).

type Response struct {
	Messages []Message `json:"messages"`
}
    List of messages

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
    SessionMeta contains the runtime state of a WhatsApp session.

type Status struct {
	Status string `json:"status"`
	User   string `json:"user"`
}
    Status

