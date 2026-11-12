package main

import (
    "context"
    "errors"
    "net/http"
    "net/http/httptest"
    "reflect"
    "strings"
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

// The groups of a session go out with the hash of their chat and their
// name, never their JID; the parent group of a community is left out.
func TestGroupsOf(t *testing.T) {
    group := types.NewJID("120363000000000001", types.GroupServer)
    community := types.NewJID("120363000000000002", types.GroupServer)
    joined := func(ctx context.Context) ([]*types.GroupInfo, error) {
        return []*types.GroupInfo{
            {JID: group, GroupName: types.GroupName{Name: "Test group"}},
            {JID: community, GroupName: types.GroupName{Name: "Test community"}, GroupParent: types.GroupParent{IsParent: true}},
        }, nil
    }

    groups, err := groupsOf(context.Background(), joined)
    if err != nil {
        t.Fatalf("groupsOf failed: %v", err)
    }
    want := []Group{{Chat: hash(group.String()), Name: "Test group"}}
    if !reflect.DeepEqual(groups, want) {
        t.Fatalf("groupsOf = %+v, want %+v", groups, want)
    }
}

func TestGroupsOfError(t *testing.T) {
    joined := func(ctx context.Context) ([]*types.GroupInfo, error) {
        return nil, errors.New("not connected")
    }

    if _, err := groupsOf(context.Background(), joined); err == nil {
        t.Fatal("groupsOf did not return the error of the client")
    }
}

func TestGroupsHandler(t *testing.T) {
    missing := httptest.NewRecorder()
    groupsHandler(missing, httptest.NewRequest("GET", "/groups", nil))
    if missing.Code != http.StatusBadRequest {
        t.Fatalf("without session: status %d, want %d", missing.Code, http.StatusBadRequest)
    }

    unknown := httptest.NewRecorder()
    groupsHandler(unknown, httptest.NewRequest("GET", "/groups?session=unknown", nil))
    if unknown.Code != http.StatusOK || strings.TrimSpace(unknown.Body.String()) != "[]" {
        t.Fatalf("unknown session: status %d, body %q, want 200 and []", unknown.Code, unknown.Body.String())
    }
}
