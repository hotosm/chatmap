# ChatMap IM connector Dockerfile

FROM golang:1.23.4 AS builder

WORKDIR /app

COPY go.mod go.sum ./

RUN go mod download

COPY main.go ./main.go

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o chatmap-wa-connector .

FROM gcr.io/distroless/static:nonroot 

WORKDIR /app

COPY --from=builder /app/chatmap-wa-connector .

EXPOSE 8001

CMD ["/app/chatmap-wa-connector"]

