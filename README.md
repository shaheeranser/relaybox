# Relaybox

Self-hosted outbound webhook delivery service. Accepts events, fans them out
to subscriber endpoints, retries with exponential backoff, signs every request
with HMAC-SHA256, and keeps a durable audit trail of every attempt.

## Quick Start

```bash
cp .env.example .env
# Edit .env to set a secure RELAYBOX_API_TOKEN if desired
docker compose up --build
```

The stack is ready when the API responds:

```bash
curl http://localhost:8000/health
```

## Register a Subscriber

Point a subscription at the built-in sink (test receiver):

```bash
curl -s -X POST http://localhost:8000/v1/subscriptions \
  -H "Authorization: Bearer $RELAYBOX_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://sink:9000/webhook",
    "event_types": ["*"],
    "secret": "whsec_test123",
    "description": "local sink"
  }'
```

## Send an Event

```bash
curl -s -X POST http://localhost:8000/v1/events \
  -H "Authorization: Bearer $RELAYBOX_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "order.shipped",
    "payload": {"order_id": "ord_42", "tracking": "1Z999AA10"}
  }'
```

The worker picks it up, signs it, and delivers it to the sink. Check what
the sink received:

```bash
curl http://localhost:9000/webhooks
```

## Inspect Deliveries

```bash
# all deliveries
curl -H "Authorization: Bearer $RELAYBOX_API_TOKEN" \
  http://localhost:8000/v1/deliveries

# dead-letter queue
curl -H "Authorization: Bearer $RELAYBOX_API_TOKEN" \
  http://localhost:8000/v1/dead-letter

# replay a failed delivery
curl -X POST -H "Authorization: Bearer $RELAYBOX_API_TOKEN" \
  http://localhost:8000/v1/deliveries/{id}/replay
```

## Configuration

All settings via environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `RELAYBOX_API_TOKEN` | *(required)* | Bearer token for `/v1` routes |
| `RELAYBOX_DATABASE_URL` | `postgresql://relaybox:relaybox@db:5432/relaybox` | Postgres DSN |
| `RELAYBOX_WORKER_CONCURRENCY` | `8` | Concurrent deliveries per worker |
| `RELAYBOX_MAX_ATTEMPTS` | `8` | Attempts before `dead` |
| `RELAYBOX_LEASE_SECONDS` | `60` | Delivery lease duration |
| `RELAYBOX_HTTP_TIMEOUT` | `10` | Per-attempt timeout (seconds) |
| `RELAYBOX_LOG_LEVEL` | `info` | Log verbosity |
| `SINK_STATUS_CODE` | `200` | Sink response status |
| `SINK_DELAY_MS` | `0` | Sink response delay (ms) |

## Architecture

```
Producer → POST /v1/events → [api] → fan out → [db (Postgres)]
                                                      ↑
[worker] → claim lease → [db] → signed POST → [subscriber]
                                                      ↑
[sink] ─── stands in for a subscriber (dev only) ─────┘
```

- **api**: FastAPI. Validates events, manages subscriptions, serves delivery log.
- **worker**: Claims deliveries via `SELECT … FOR UPDATE SKIP LOCKED`, delivers
  with HMAC signing and exponential-backoff retries.
- **db**: PostgreSQL — persistent store and work queue.
- **sink**: Configurable test receiver for local development.

## Signing

Every outbound request carries:

```
X-Relaybox-Signature: t=<unix>,v1=<hex hmac-sha256(secret, "<t>.<body>")>
X-Relaybox-Event-Type: order.shipped
X-Relaybox-Delivery-Id: <uuid>
X-Relaybox-Attempt: 1
```

## License

Unlicensed — internal infrastructure.
