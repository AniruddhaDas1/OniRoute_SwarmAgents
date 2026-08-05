# Mission Control CLI Reference — Phase P6.D3

## Commands

### `oniroute pause`

Pause a running mission.

```bash
oniroute pause
oniroute pause --mission msn-abc-123
oniroute pause --reason "checking intermediate output"
```

**Output:**
```
⏸ Mission msn-abc-123 paused successfully.
┌─────────────────────────────────┐
│     Paused Mission State        │
├───────────────┬─────────────────┤
│ Current Stage │ ENGINEERING     │
│ Current Agent │ Backend Engineer│
│ Progress      │ 45.0%           │
│ Quality Score │ 9.50            │
└───────────────┴─────────────────┘
Resume anytime with: oniroute resume
```

### `oniroute resume`

Resume a paused mission.

```bash
oniroute resume
oniroute resume --mission msn-abc-123
```

### `oniroute cancel`

Cancel a running or paused mission.

```bash
oniroute cancel
oniroute cancel --mission msn-abc-123 --reason "requirements changed"
oniroute cancel --force
```

### `oniroute inspect`

Inspect a running, paused, or completed mission.

```bash
oniroute inspect
oniroute inspect --mission msn-abc-123
oniroute inspect --json
```

**Output:**
```
┌───────────────────────────────────────────┐
│    Mission Inspection: msn-abc-123        │
├─────────────────────┬─────────────────────┤
│ Mission ID          │ msn-abc-123         │
│ Status              │ RUNNING             │
│ Current Stage       │ ENGINEERING         │
│ Current Agent       │ Backend Engineer    │
│ Current Contract    │ ctr-be-001          │
│ Files Created       │ 12                  │
│ Files Modified      │ 3                   │
│ Quality Score       │ 9.50 / 10.0         │
│ Tokens Used         │ 15000               │
│ Estimated Cost      │ $0.045000           │
│ Active MCP Tools    │ BridgeForce, Stitch │
│ Remaining Contracts │ 5                   │
│ Progress            │ 45.0%               │
│ Production Ready    │ NO                  │
│ Elapsed Time        │ 12000.00 ms         │
└─────────────────────┴─────────────────────┘
```

### `oniroute logs`

View mission execution logs.

```bash
oniroute logs
oniroute logs --mission msn-abc-123
oniroute logs --tail 20
oniroute logs --json
```

### `oniroute status`

Display active or saved session status (P6.D2).

```bash
oniroute status
oniroute status --session sess-abc-123
```

### `oniroute watch`

Stream live execution events (P6.D2).

```bash
oniroute watch
oniroute watch --session sess-abc-123
```

## Global Options

| Option | Short | Description |
|---|---|---|
| `--workspace` | `-w` | Target workspace path |
| `--mission` | `-m` | Target mission ID |
| `--session` | `-s` | Target session ID |
| `--json` | | Output raw JSON |
| `--reason` | `-r` | Command reason |
| `--force` | `-f` | Force without confirmation |
| `--tail` | `-n` | Number of log entries |
