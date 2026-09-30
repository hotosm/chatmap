package main

import (
    "testing"
    "time"

    "go.mau.fi/whatsmeow/types"
    "go.mau.fi/whatsmeow/types/events"
)

// A phone's reply to an unavailable-message request can be dispatched as an
// events.Message with Info but no Message content. handleMessage must not panic.
func TestHandleMessageNilContent(t *testing.T) {
    defer func() {
        if r := recover(); r != nil {
            t.Fatalf("handleMessage panicked on nil Message: %v", r)
        }
    }()

    jid := types.NewJID("5491100000000", types.DefaultUserServer)
    v := &events.Message{
        Info: types.MessageInfo{
            MessageSource: types.MessageSource{
                Chat:   jid,
                Sender: jid,
            },
            Timestamp: time.Date(2026, 9, 29, 20, 10, 9, 0, time.UTC),
        },
        Message: nil,
    }

    handleMessage("test", v, "0123456789abcdef0123456789abcdef")
}
