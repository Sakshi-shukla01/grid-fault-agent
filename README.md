---

title: Grid Fault Localization Agent
emoji: ⚡
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
tags:
  - openenv
  - reinforcement-learning
  - power-systems
---

# ⚡ Grid Fault Localization & RCA Agent

> An OpenEnv-compatible RL environment where AI agents diagnose
> power grid faults in real time — a problem costing utilities
> $150B per year in unplanned outages.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue)]()
[![Docker](https://img.shields.io/badge/Docker-sakshishukla10-blue)](https://hub.docker.com/u/sakshishukla10)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)]()
[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![Node](https://img.shields.io/badge/Node-20-green)]()

---

## The Real-World Problem

When a fault hits a power grid, operators have **2–8 minutes**
to diagnose root cause before cascades cause blackouts.
Today this is done manually — engineers cross-referencing
SCADA screens and relay logs under extreme time pressure.

The 2003 Northeast blackout started as a single software bug,
cascaded in 8 minutes, affected 55 million people and cost $6B.

This environment trains RL agents to catch faults in seconds.

---

## Three Tasks — Three Difficulty Levels

| Task | Grid | Difficulty | Faults | Max Steps | Score Range |
|------|------|-----------|--------|-----------|-------------|
| `radial_fault` | 14-bus radial | Easy | 6 | 10 | 0.30–0.70 |
| `cascade_ring` | 20-bus ring | Medium | 10 | 14 | 0.20–0.55 |
| `storm_mesh` | 30-bus mesh | Hard | 25 | 20 | 0.10–0.40 |

---

## Architecture
React Dashboard ←→ Express (Node.js) ←→ Redis pub/sub
↓
FastAPI (Python)
RL Environment
↓
MongoDB Atlas
Microservices: env-service · inference-service · worker-service · dashboard-service
Infrastructure: Docker · Kubernetes · Redis · Prometheus · Grafana

---

## Quick Start

```bash
git clone https://github.com/sakshishukla10/grid-fault-agent
cd grid-fault-agent

# Set secrets
cp env/.env.example env/.env
# Edit env/.env with your tokens

# Run with Docker Compose
docker-compose up -d

# Run baseline agent
curl -X POST http://localhost:8001/run \
  -H "Content-Type: application/json" \
  -d '{"task_id": "radial_fault"}'
```

---

## Baseline Scores — meta-llama/Llama-3.1-8B-Instruct

| Task | Score | Recall | Precision | Faults Found |
|------|-------|--------|-----------|--------------|
| radial_fault | 0.32 | 0.17 | 1.00 | 1/6 |
| cascade_ring | 0.44 | 0.10 | 1.00 | 1/10 |
| storm_mesh | — | — | — | 0/25 |

---

## Action Space

```json
{
  "action_type": "identify_fault | query_telemetry | isolate_breaker | submit_rca",
  "component_id": "e.g. LINE_3_7 or BUS_7",
  "fault_type": "line_trip | transformer_overload | relay_maloperation | phase_imbalance | scada_loss | capacitor_failure",
  "severity": "critical | major | minor",
  "description": "detailed finding referencing SCADA values and relay IDs",
  "recommendation": "optional corrective action"
}
```

---

## Reward Design

| Action | Reward |
|--------|--------|
| Correct critical fault | +0.30 |
| Correct major fault | +0.25 |
| Correct minor fault | +0.20 |
| Partial match | +0.05 |
| Query telemetry | +0.02 |
| False positive | −0.05 |
| Duplicate finding | −0.10 |
| Submit RCA bonus | up to +0.30 |

Grading: Recall 40% · Precision 25% · Cascade depth 20% · Efficiency 15%

All grading is deterministic keyword matching — perfectly reproducible.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /reset | Start new episode |
| POST | /step | Take one action |
| GET | /state | Get current state |
| GET | /scenarios | List all tasks |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |

---

## Docker Images

```bash
docker pull sakshishukla10/grid-fault-env:latest
docker pull sakshishukla10/grid-fault-inference:latest
docker pull sakshishukla10/grid-fault-worker:latest
docker pull sakshishukla10/grid-fault-dashboard:latest
```

---

## Kubernetes

```bash
kubectl apply -f k8s/
kubectl get pods -n gridfault
```

---

## Monitoring

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin123)

---

## License

MIT — Sakshi Shukla
=======
title: Grid Fault Agent
emoji: 🏆
colorFrom: indigo
colorTo: pink
sdk: docker
pinned: false
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
