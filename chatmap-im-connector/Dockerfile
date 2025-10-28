# ChatMap IM connector Dockerfile

FROM golang:1.25.3 AS builder

WORKDIR /app

COPY go.mod go.sum ./

RUN go mod download

COPY main.go ./main.go

RUN go build -o chatmap-im-connector .

FROM golang:1.23.4

WORKDIR /app

COPY --from=builder /app/chatmap-im-connector .

EXPOSE 8001

CMD ["/app/chatmap-im-connector"]

