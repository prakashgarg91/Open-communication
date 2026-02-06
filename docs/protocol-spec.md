# Vākya Protocol Specification v1.0
## वाक्य प्रोटोकॉल विशिष्टता

> **Vākya** (वाक्य) — *Sanskrit for "expression, sentence, speech"*
> An open, JSON-based protocol for AI-to-AI communication.

---

## 1. Overview (सारांश)

The Vākya protocol enables any AI/LLM model to communicate with any other model through a standardized, human-readable message format. It is designed to be:

- **Sarala (सरल)** — Simple: Pure JSON, no binary encoding
- **Vyāpaka (व्यापक)** — Universal: Model-agnostic, works with any LLM
- **Spashta (स्पष्ट)** — Clear: Humans can read every message
- **Vistārya (विस्तार्य)** — Extensible: Add custom fields without breaking compatibility

## 2. Core Concepts (मूल अवधारणाएँ)

| Sanskrit | Transliteration | Meaning | Protocol Role |
|----------|----------------|---------|---------------|
| वाक्य | Vākya | Expression | A single message |
| संवाद | Saṃvāda | Dialogue | A conversation thread |
| कार्य | Kārya | Task | A unit of work |
| सभा | Sabhā | Assembly | A group of collaborating AIs |
| सूत्र | Sūtra | Thread | A communication channel |
| दूत | Dūta | Messenger | An AI agent/participant |
| प्रमाण | Pramāṇa | Proof | Message integrity hash |
| प्रेषक | Preṣaka | Sender | Message sender |
| प्रापक | Prāpaka | Receiver | Message recipient |
| समय | Samaya | Time | Timestamp |
| प्रकार | Prakāra | Type | Message type |
| विषय | Viṣaya | Subject | Message topic |
| शरीर | Śarīra | Body | Message content |
| सन्दर्भ | Sandarbha | Context | References & metadata |
| इतिहास | Itihāsa | History | Message log |

## 3. Wire Format (तार प्रारूप)

Every message on the wire is wrapped in a protocol envelope:

```json
{
  "vakya": "1.0",
  "pramana": "sha256:a1b2c3d4...",
  "sandesa": {
    "id": "msg-550e8400-e29b-41d4-a716-446655440000",
    "samvada_id": "conv-123",
    "presaka": "claude-opus-1",
    "prapaka": "gpt-4o-1",
    "samaya": "2026-02-06T12:00:00Z",
    "prakara": "prasna",
    "visaya": "algorithms",
    "sarira": {
      "text": "What's your approach to the traveling salesman problem?",
      "context": "We're optimizing delivery routes"
    },
    "sandarbha": {
      "reply_to": null,
      "references": [],
      "tags": ["algorithms", "optimization"],
      "meta": {}
    }
  }
}
```

### Envelope Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vakya` | string | ✅ | Protocol version (e.g., "1.0") |
| `pramana` | string\|null | ❌ | SHA-256 integrity hash of `sandesa` |
| `sandesa` | object | ✅ | The actual message payload |

### Message Fields (sandesa)

| Field | Sanskrit | Type | Required | Description |
|-------|----------|------|----------|-------------|
| `id` | — | string | ✅ | Unique message ID |
| `samvada_id` | संवाद | string\|null | ❌ | Conversation thread ID |
| `presaka` | प्रेषक | string | ✅ | Sender ID |
| `prapaka` | प्रापक | string\|string[]\|null | ❌ | Recipient(s). null = broadcast |
| `samaya` | समय | string | ✅ | ISO-8601 timestamp |
| `prakara` | प्रकार | string | ✅ | Message type (see §4) |
| `visaya` | विषय | string\|null | ❌ | Subject/topic |
| `sarira` | शरीर | object | ✅ | Message body (see §5) |
| `sandarbha` | सन्दर्भ | object | ❌ | Context & references |

## 4. Message Types (प्रकार)

| Type | Sanskrit | Meaning | Use Case |
|------|----------|---------|----------|
| `vakya` | वाक्य | Statement | General message |
| `prasna` | प्रश्न | Question | Requesting information |
| `uttara` | उत्तर | Answer | Responding to a question |
| `karya` | कार्य | Task | Assigning work |
| `prativedana` | प्रतिवेदन | Report | Status/progress update |
| `svikriti` | स्वीकृति | Acceptance | Acknowledging a message |
| `nirnaya` | निर्णय | Decision | Making/announcing a decision |
| `vivada` | विवाद | Disagreement | Counter-proposal or objection |
| `abhivadana` | अभिवादन | Greeting | Handshake/connection |
| `visarjana` | विसर्जन | Farewell | Disconnection |

## 5. Body Schemas (शरीर)

The `sarira` (body) field's schema depends on the `prakara` (message type):

### General Message (`vakya`)
```json
{"text": "Free-form message text", "language": "en"}
```

### Question (`prasna`)
```json
{"text": "The question text", "context": "Optional background"}
```

### Answer (`uttara`)
```json
{"text": "The answer text", "confidence": 0.95}
```

### Task (`karya`)
```json
{
  "title": "Task title",
  "description": "Detailed description",
  "priority": "ucca",
  "skills": ["python", "analysis"],
  "deadline": "2026-02-10T00:00:00Z"
}
```

Priority levels: `atyavashyaka` (critical) > `ucca` (high) > `madhyama` (medium) > `nimna` (low)

### Progress Report (`prativedana`)
```json
{
  "karya_id": "task-123",
  "sthiti": "sakriya",
  "pravrtti": 0.75,
  "vivarana": "Three of four subtasks complete"
}
```

Status values (`sthiti`): `pratiksha` (pending), `sakriya` (active), `sampurna` (complete), `viphala` (failed)

### Acknowledgment (`svikriti`)
```json
{"accepted": true, "text": "Optional comment"}
```

### Decision (`nirnaya`)
```json
{"decision": "The decision text", "reasoning": "Why this was decided"}
```

## 6. Identity (दूत)

Each AI agent is a **Dūta** (दूत = messenger) with this identity schema:

```json
{
  "id": "claude-opus-1",
  "name": "Claude",
  "model": "claude-opus-4.6",
  "provider": "anthropic",
  "role": "kartr",
  "skills": ["code-generation", "analysis", "writing"],
  "bhasha": ["en", "fr", "sa"]
}
```

### Roles

| Role | Sanskrit | Meaning |
|------|----------|---------|
| `neta` | नेता | Leader/Coordinator |
| `kartr` | कर्तृ | Worker/Executor |
| `samikshaka` | समीक्षक | Reviewer |
| `pariksaka` | परीक्षक | Tester |
| `mantri` | मन्त्री | Advisor |
| `srotri` | श्रोतृ | Observer |
| `madhyastha` | मध्यस्थ | Mediator |

## 7. Channels (सूत्र)

Communication happens through **Sūtras** (channels):

| Type | Description |
|------|-------------|
| `direct` | One-to-one between two Dūtas |
| `sabha` | Group channel (assembly) |
| `broadcast` | One-to-all |
| `visaya` | Topic-based subscription |

## 8. Integrity (प्रमाण)

Messages can be signed with a SHA-256 hash:

1. Serialize `sandesa` to JSON with sorted keys
2. Compute SHA-256 hash
3. Set `pramana` to `"sha256:<hex_digest>"`

Receivers verify by recomputing the hash and comparing.

## 9. Transport

The Vākya protocol is transport-agnostic. Reference implementations:

- **WebSocket** — Real-time relay server
- **HTTP/REST** — Request-response API
- **Stdio** — Pipe-based for local processes

## 10. Extensibility

Custom fields can be added to `sarira` and `sandarbha.meta` without breaking compatibility. Receivers MUST ignore unknown fields.

---

*ॐ — May all AIs communicate in harmony.*
