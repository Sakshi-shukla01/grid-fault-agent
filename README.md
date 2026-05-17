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

> An OpenEnv-compatible RL environment where AI agents diagnose power grid faults in real time — a problem costing utilities **$150B per year** in unplanned outages.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue)]()
[![Docker](https://img.shields.io/badge/Docker-sakshishukla10-blue)](https://hub.docker.com/u/sakshishukla10)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Space-orange)](https://huggingface.co/spaces/sakshi898/grid-fault-agent1)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)]()
[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![Node](https://img.shields.io/badge/Node-20-green)]()

---

## The Real-World Problem

When a fault hits a power grid, operators have **2–8 minutes** to diagnose root cause before cascades cause blackouts. Today this is done manually — engineers cross-referencing SCADA screens and relay logs under extreme time pressure.

The **2003 Northeast blackout** started as a single software bug, cascaded in 8 minutes, affected 55 million people and cost **$6B**.

This environment trains RL agents to catch faults in seconds.

---

## Three Tasks — Three Difficulty Levels

| Task | Grid | Difficulty | Faults | Max Steps | Score Range |
|------|------|-----------|--------|-----------|-------------|
| `radial_fault` | 14-bus radial | Easy | 6 | 10 | 0.30–0.70 |
| `cascade_ring` | 20-bus ring | Medium | 10 | 14 | 0.20–0.55 |
| `storm_mesh` | 30-bus mesh | Hard | 25 | 20 | 0.10–0.40 |

---

## Baseline Scores — meta-llama/Llama-3.1-8B-Instruct

| Task | Difficulty | Score | Recall | Precision | Faults Found |
|------|-----------|-------|--------|-----------|--------------|
| radial_fault | Easy | 0.4317 | 0.1667 | 1.00 | 1/6 |
| cascade_ring | Medium | 0.4529 | 0.30 | 1.00 | 3/10 |
| storm_mesh | Hard | 0.1425 | 0.00 | 0.00 | 0/25 |

---

## Architecture
React Dashboard ←→ Express (Node.js) ←→ Redis pub/sub
↓
FastAPI (Python) — RL Environment
↓
MongoDB Atlas
Microservices: env-service · inference-service · worker-service · dashboard-service
Infrastructure: Docker · Kubernetes · Redis · Prometheus · Grafana

---

## Quick Start

```bash
git clone https://github.com/Sakshi-shukla01/grid-fault-agent
cd grid-fault-agent

# Set secrets
cp env/.env.example env/.env
# Edit env/.env with your HF token and MongoDB URI

# Run with Docker Compose
docker-compose up -d

# Run baseline agent
curl -X POST http://localhost:8001/run \
  -H "Content-Type: application/json" \
  -d '{"task_id": "radial_fault"}'
```

---

## Live API — HuggingFace Spaces

| Endpoint | URL |
|----------|-----|
| Health | https://sakshi898-grid-fault-agent1.hf.space/health |
| API Docs | https://sakshi898-grid-fault-agent1.hf.space/docs |
| Scenarios | https://sakshi898-grid-fault-agent1.hf.space/scenarios |

```bash
# Test reset
curl -X POST https://sakshi898-grid-fault-agent1.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "radial_fault"}'

# Test step
curl -X POST https://sakshi898-grid-fault-agent1.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action_type":"identify_fault","component_id":"LINE_3_7","fault_type":"line_trip","severity":"critical","description":"LINE_3_7 overcurrent trip zone_3 RELAY_37 BUS_7 blackout tripped"}'
```

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

**Grading:** Recall 40% · Precision 25% · Cascade depth 20% · Efficiency 15%

All grading is **deterministic keyword matching** — perfectly reproducible, no LLM in grading loop.

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

## Infrastructure

| Service | Port | Status |
|---------|------|--------|
| FastAPI env service | 7860 | ✅ Running |
| Inference service | 8001 | ✅ Running |
| Express dashboard | 5000 | ✅ Running |
| Redis | 6379 | ✅ Running |
| MongoDB Atlas | cloud | ✅ Connected |
| Prometheus | 9090 | ✅ Running |
| Grafana | 3001 | ✅ Running |
| HuggingFace Space | cloud | ✅ Live |

---

## Monitoring

### Prometheus Targets — All UP
- env-service: **UP** — scraping `/metrics` on port 7860
- inference-service: **UP** — scraping `/metrics` on port 8001
- worker-service: **UP** — scraping on port 9101
- redis: **UP**

### Grafana Dashboard
Live metrics at `http://localhost:3001` (admin/admin):
- Total steps taken across all episodes: **129**
- Total episodes run: **18**
- Inference steps by LLM agent: **61**
- Inference episodes completed: **9**
- Rewards over time (timeseries)

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
kubectl get hpa -n gridfault
```

---

## Project Links

| Resource | URL |
|----------|-----|
| GitHub | https://github.com/Sakshi-shukla01/grid-fault-agent |
| HuggingFace Space | https://huggingface.co/spaces/sakshi898/grid-fault-agent1 |
| Live API Docs | https://sakshi898-grid-fault-agent1.hf.space/docs |
| DockerHub | https://hub.docker.com/u/sakshishukla10 |

---

## License

MIT — Sakshi Shukla
