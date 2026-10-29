# Status engine — draft diagram

Point status (e.g. a Point as "gate"/"step", enabled or disabled),
computed from the same message stream, as a new engine parallel to
[conversation_engine.md](./conversation_engine.md).

```mermaid
flowchart TD
    whatsapp["WhatsApp user"]
    connector["chatmap-im-connector"]
    stream[("messages:&lt;sessionID&gt;<br/>(existing stream, D-002)")]

    subgraph existing["Existing pipeline — untouched"]
        oldconsumer["stream_listener<br/>full rescan, XRANGE"]
        chatmappy["chatmap-py<br/>pairing D-008/D-009"]
        postgres[("points table")]
    end

    subgraph convengine["Conversation engine — untouched<br/>(see conversation_engine.md)"]
        devices["Device discovery<br/>poll ~2s"]
        convconsumer["Event consumer<br/>XREADGROUP / XACK<br/>own consumer group"]
    end

    subgraph new["New — Status engine"]
        statusconsumer["Status consumer<br/>XREADGROUP / XACK<br/>own consumer group<br/>(reuses RedisConsumer base?)"]
        statusdetect["StatusDetector<br/>(opaque for now)<br/>ReceivedMessage → {point_id, new_status} | None"]
        statusstore["StatusStore"]
        pointstatus[("point_statuses table<br/>FK point_id → points.id")]
    end

    whatsapp -->|text/location/media| connector
    connector -->|XADD| stream
    stream -->|reads, unaffected| oldconsumer
    oldconsumer --> chatmappy --> postgres
    stream -.->|scan for messages:* keys| devices
    devices -->|active sessionIDs| convconsumer
    stream -->|reads, independent group| convconsumer

    devices -.->|reused? open question| statusconsumer
    stream -->|reads, independent group| statusconsumer
    statusconsumer --> statusdetect
    statusdetect -->|if match| statusstore
    statusstore -->|UPSERT by point_id| pointstatus
    statusstore -->|XACK| statusconsumer
    pointstatus -.->|FK| postgres

    classDef redis fill:#FAECE7,stroke:#D85A30,color:#712B13;
    classDef consumer fill:#E1F5EE,stroke:#1D9E75,color:#0F6E56;
    classDef ext fill:#F1EFE8,stroke:#888780,color:#2C2C2A;
    classDef opaque fill:#EDEBF7,stroke:#6C5CE7,color:#3B2F82,stroke-dasharray: 5 5;
    class stream,postgres,pointstatus redis
    class statusconsumer,oldconsumer,convconsumer,devices,statusstore consumer
    class whatsapp,connector,chatmappy ext
    class statusdetect opaque
```
