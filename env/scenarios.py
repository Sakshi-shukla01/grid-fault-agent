SCENARIOS: dict = {

    "radial_fault": {
        "grid_id":        "GRID-001",
        "name":           "Radial distribution fault",
        "difficulty":     "easy",
        "max_steps":      10,
        "task_description": (
            "A fault has occurred on a 14-bus radial distribution grid. "
            "BUS_7 has gone dark. Analyse SCADA readings and relay logs "
            "to identify all faults and their root causes."
        ),
        "goal": "Identify all 6 planted faults and submit RCA within 10 steps.",
        "buses": [
            {"id": "BUS_1",  "voltage_kv": 132, "load_mw": 0,  "status": "energised"},
            {"id": "BUS_2",  "voltage_kv": 132, "load_mw": 20, "status": "energised"},
            {"id": "BUS_3",  "voltage_kv": 33,  "load_mw": 30, "status": "energised"},
            {"id": "BUS_4",  "voltage_kv": 33,  "load_mw": 25, "status": "energised"},
            {"id": "BUS_5",  "voltage_kv": 33,  "load_mw": 15, "status": "energised"},
            {"id": "BUS_6",  "voltage_kv": 11,  "load_mw": 10, "status": "energised"},
            {"id": "BUS_7",  "voltage_kv": 11,  "load_mw": 45, "status": "DE-ENERGISED"},
            {"id": "BUS_8",  "voltage_kv": 11,  "load_mw": 22, "status": "energised"},
            {"id": "BUS_9",  "voltage_kv": 11,  "load_mw": 18, "status": "energised"},
            {"id": "BUS_10", "voltage_kv": 11,  "load_mw": 12, "status": "energised"},
            {"id": "BUS_11", "voltage_kv": 11,  "load_mw": 8,  "status": "energised"},
            {"id": "BUS_12", "voltage_kv": 33,  "load_mw": 35, "status": "energised"},
            {"id": "BUS_13", "voltage_kv": 33,  "load_mw": 28, "status": "energised"},
            {"id": "BUS_14", "voltage_kv": 11,  "load_mw": 14, "status": "energised"},
        ],
        "lines": [
            {"id": "LINE_1_2",  "from": "BUS_1",  "to": "BUS_2",  "status": "closed",   "current_a": 312},
            {"id": "LINE_2_3",  "from": "BUS_2",  "to": "BUS_3",  "status": "closed",   "current_a": 280},
            {"id": "LINE_3_4",  "from": "BUS_3",  "to": "BUS_4",  "status": "closed",   "current_a": 195},
            {"id": "LINE_3_7",  "from": "BUS_3",  "to": "BUS_7",  "status": "TRIPPED",  "current_a": 0},
            {"id": "LINE_4_5",  "from": "BUS_4",  "to": "BUS_5",  "status": "closed",   "current_a": 142},
            {"id": "LINE_5_6",  "from": "BUS_5",  "to": "BUS_6",  "status": "closed",   "current_a": 98},
            {"id": "LINE_6_11", "from": "BUS_6",  "to": "BUS_11", "status": "closed",   "current_a": 76},
            {"id": "LINE_7_8",  "from": "BUS_7",  "to": "BUS_8",  "status": "open",     "current_a": 0},
            {"id": "LINE_8_9",  "from": "BUS_8",  "to": "BUS_9",  "status": "closed",   "current_a": 110},
            {"id": "LINE_9_10", "from": "BUS_9",  "to": "BUS_10", "status": "closed",   "current_a": 88},
            {"id": "LINE_12_13","from": "BUS_12", "to": "BUS_13", "status": "closed",   "current_a": 220},
            {"id": "LINE_13_14","from": "BUS_13", "to": "BUS_14", "status": "closed",   "current_a": 180},
        ],
        "scada_readings": {
            "BUS_7":     {"voltage_pu": 0.0,  "active_power_mw": 0,    "status": "BLACKOUT"},
            "BUS_8":     {"voltage_pu": 0.0,  "active_power_mw": 0,    "status": "BLACKOUT"},
            "LINE_3_7":  {"current_a": 0,     "power_flow_mw": 0,      "status": "TRIPPED"},
            "RELAY_37":  {"status": "OPERATED","trip_time_ms": 82,     "zone": "zone_3"},
            "BUS_3":     {"voltage_pu": 0.97, "active_power_mw": 30,   "status": "normal"},
            "TX_3_7":    {"temp_celsius": 94, "loading_pct": 112,      "status": "OVERLOADED"},
        },
        "relay_log": [
            {"time": "14:32:07.082", "relay": "RELAY_37",  "event": "overcurrent trip",    "zone": "zone_3", "current_a": 1840},
            {"time": "14:32:07.095", "relay": "RELAY_37B", "event": "backup trip operated","zone": "zone_3", "note": "primary RELAY_37 slow to reset"},
            {"time": "14:32:08.210", "relay": "RELAY_78",  "event": "loss of voltage trip","zone": "zone_1", "bus": "BUS_7"},
            {"time": "14:32:09.000", "relay": "RELAY_38",  "event": "reverse power alarm", "note": "possible relay maloperation on LINE_3_8"},
        ],
        "ground_truth_faults": [
            {
                "component_id": "LINE_3_7",
                "fault_type":   "line_trip",
                "severity":     "critical",
                "keywords":     ["LINE_3_7", "overcurrent", "zone_3", "RELAY_37", "tripped", "BUS_7"],
                "description":  "Phase-to-ground fault on LINE_3_7 caused overcurrent trip by RELAY_37 in zone_3, de-energising BUS_7."
            },
            {
                "component_id": "BUS_7",
                "fault_type":   "line_trip",
                "severity":     "critical",
                "keywords":     ["BUS_7", "blackout", "de-energised", "voltage", "zero"],
                "description":  "BUS_7 completely de-energised — voltage at 0 pu following LINE_3_7 trip."
            },
            {
                "component_id": "TX_3_7",
                "fault_type":   "transformer_overload",
                "severity":     "major",
                "keywords":     ["TX_3_7", "overloaded", "112", "temperature", "94"],
                "description":  "Transformer TX_3_7 was running at 112% loading (94°C) contributing to line fault."
            },
            {
                "component_id": "RELAY_37B",
                "fault_type":   "relay_maloperation",
                "severity":     "major",
                "keywords":     ["RELAY_37B", "backup", "slow", "reset", "primary"],
                "description":  "Backup relay RELAY_37B operated unnecessarily due to primary RELAY_37 slow reset."
            },
            {
                "component_id": "BUS_8",
                "fault_type":   "line_trip",
                "severity":     "major",
                "keywords":     ["BUS_8", "blackout", "loss of voltage", "BUS_7", "downstream"],
                "description":  "BUS_8 lost supply as downstream load of BUS_7 — cascading blackout."
            },
            {
                "component_id": "RELAY_38",
                "fault_type":   "relay_maloperation",
                "severity":     "minor",
                "keywords":     ["RELAY_38", "reverse power", "maloperation", "alarm"],
                "description":  "RELAY_38 issued spurious reverse power alarm — possible maloperation during voltage collapse."
            },
        ]
    },

    "cascade_ring": {
        "grid_id":        "GRID-002",
        "name":           "Ring grid cascade",
        "difficulty":     "medium",
        "max_steps":      14,
        "task_description": (
            "A protection relay maloperation on a 20-bus ring grid has caused "
            "a cascade trip of three healthy lines. Trace the cascade chain "
            "and identify all 10 faults."
        ),
        "goal": "Trace full cascade chain and identify all 10 faults within 14 steps.",
        "buses":  [{"id": f"BUS_{i}", "voltage_kv": 33, "load_mw": 20+i, "status": "energised" if i not in [9,10,11] else "DE-ENERGISED"} for i in range(1, 21)],
        "lines":  [
            {"id": "LINE_8_9",   "from": "BUS_8",  "to": "BUS_9",  "status": "TRIPPED",  "current_a": 0},
            {"id": "LINE_9_10",  "from": "BUS_9",  "to": "BUS_10", "status": "TRIPPED",  "current_a": 0},
            {"id": "LINE_10_11", "from": "BUS_10", "to": "BUS_11", "status": "TRIPPED",  "current_a": 0},
            {"id": "LINE_1_2",   "from": "BUS_1",  "to": "BUS_2",  "status": "closed",   "current_a": 310},
        ],
        "scada_readings": {
            "BUS_9":      {"voltage_pu": 0.0, "status": "BLACKOUT"},
            "BUS_10":     {"voltage_pu": 0.0, "status": "BLACKOUT"},
            "BUS_11":     {"voltage_pu": 0.0, "status": "BLACKOUT"},
            "RELAY_89":   {"status": "OPERATED", "trip_time_ms": 45, "zone": "zone_1", "note": "maloperation — current within limits"},
            "TX_8_9":     {"temp_celsius": 78, "loading_pct": 88,   "status": "normal"},
        },
        "relay_log": [
            {"time": "09:14:22.045", "relay": "RELAY_89",  "event": "distance trip zone_1", "note": "MALOPERATION — impedance measurement error"},
            {"time": "09:14:22.310", "relay": "RELAY_910", "event": "loss of voltage trip",  "zone": "zone_1"},
            {"time": "09:14:23.100", "relay": "RELAY_1011","event": "overcurrent trip",       "zone": "zone_2"},
        ],
        "ground_truth_faults": [
            {"component_id": "RELAY_89",   "fault_type": "relay_maloperation",   "severity": "critical", "keywords": ["RELAY_89","maloperation","impedance","distance","zone_1"]},
            {"component_id": "LINE_8_9",   "fault_type": "line_trip",            "severity": "critical", "keywords": ["LINE_8_9","tripped","RELAY_89","healthy"]},
            {"component_id": "LINE_9_10",  "fault_type": "line_trip",            "severity": "critical", "keywords": ["LINE_9_10","cascade","loss of voltage","BUS_9"]},
            {"component_id": "LINE_10_11", "fault_type": "line_trip",            "severity": "major",    "keywords": ["LINE_10_11","cascade","overcurrent","zone_2"]},
            {"component_id": "BUS_9",      "fault_type": "line_trip",            "severity": "critical", "keywords": ["BUS_9","blackout","de-energised"]},
            {"component_id": "BUS_10",     "fault_type": "line_trip",            "severity": "critical", "keywords": ["BUS_10","blackout","downstream"]},
            {"component_id": "BUS_11",     "fault_type": "line_trip",            "severity": "major",    "keywords": ["BUS_11","blackout","cascade"]},
            {"component_id": "RELAY_910",  "fault_type": "relay_maloperation",   "severity": "major",    "keywords": ["RELAY_910","loss of voltage","upstream","cascade"]},
            {"component_id": "RELAY_1011", "fault_type": "relay_maloperation",   "severity": "minor",    "keywords": ["RELAY_1011","overcurrent","downstream","cascade"]},
            {"component_id": "TX_8_9",     "fault_type": "transformer_overload", "severity": "minor",    "keywords": ["TX_8_9","loading","temperature","contributing"]},
        ]
    },

    "storm_mesh": {
        "grid_id":        "GRID-003",
        "name":           "Storm event mesh grid",
        "difficulty":     "hard",
        "max_steps":      20,
        "task_description": (
            "A severe storm has hit a 30-bus mesh transmission grid. "
            "Multiple simultaneous faults, a SCADA communications blackout "
            "on zone C, and a capacitor bank failure are causing system instability. "
            "Identify all 25 faults and trace every cascade chain."
        ),
        "goal": "Identify all 25 faults across 3 simultaneous fault zones within 20 steps.",
        "buses":  [{"id": f"BUS_{i}", "voltage_kv": 132 if i <= 10 else 33, "load_mw": 30+i*2, "status": "energised" if i not in [5,6,7,15,16,22,23] else "DE-ENERGISED"} for i in range(1, 31)],
        "lines":  [
            {"id": "LINE_5_6",   "from": "BUS_5",  "to": "BUS_6",  "status": "TRIPPED", "current_a": 0},
            {"id": "LINE_15_16", "from": "BUS_15", "to": "BUS_16", "status": "TRIPPED", "current_a": 0},
            {"id": "LINE_22_23", "from": "BUS_22", "to": "BUS_23", "status": "TRIPPED", "current_a": 0},
        ],
        "scada_readings": {
            "ZONE_C":     {"status": "COMMS_LOSS", "buses_affected": ["BUS_20","BUS_21","BUS_22","BUS_23"], "note": "SCADA fibre cut by storm"},
            "BUS_5":      {"voltage_pu": 0.0,  "status": "BLACKOUT"},
            "BUS_6":      {"voltage_pu": 0.0,  "status": "BLACKOUT"},
            "BUS_7":      {"voltage_pu": 0.71, "status": "LOW_VOLTAGE"},
            "CAP_BANK_2": {"status": "FAILED", "var_output": 0, "note": "storm wind damage"},
            "BUS_15":     {"voltage_pu": 0.0,  "status": "BLACKOUT"},
        },
        "relay_log": [
            {"time": "22:05:11.033", "relay": "RELAY_56",    "event": "lightning strike trip",   "zone": "zone_1"},
            {"time": "22:05:12.100", "relay": "RELAY_1516",  "event": "wind-induced galloping trip","zone": "zone_2"},
            {"time": "22:05:14.500", "relay": "RELAY_2223",  "event": "overcurrent trip",         "zone": "zone_3", "note": "SCADA blind zone"},
            {"time": "22:05:15.000", "relay": "CAP_PROT_2",  "event": "capacitor bank isolation", "note": "internal fault"},
            {"time": "22:05:18.200", "relay": "RELAY_78",    "event": "low voltage alarm",        "bus": "BUS_7"},
        ],
        "ground_truth_faults": [
            {"component_id": "LINE_5_6",   "fault_type": "line_trip",          "severity": "critical", "keywords": ["LINE_5_6","lightning","RELAY_56","zone_1","storm"]},
            {"component_id": "LINE_15_16", "fault_type": "line_trip",          "severity": "critical", "keywords": ["LINE_15_16","wind","galloping","RELAY_1516","zone_2"]},
            {"component_id": "LINE_22_23", "fault_type": "line_trip",          "severity": "critical", "keywords": ["LINE_22_23","RELAY_2223","overcurrent","SCADA","blind"]},
            {"component_id": "CAP_BANK_2", "fault_type": "capacitor_failure",  "severity": "major",    "keywords": ["CAP_BANK_2","capacitor","failed","var","reactive"]},
            {"component_id": "ZONE_C",     "fault_type": "scada_loss",         "severity": "major",    "keywords": ["ZONE_C","SCADA","comms","fibre","blind","loss"]},
            {"component_id": "BUS_5",      "fault_type": "line_trip",          "severity": "critical", "keywords": ["BUS_5","blackout","de-energised","downstream"]},
            {"component_id": "BUS_6",      "fault_type": "line_trip",          "severity": "critical", "keywords": ["BUS_6","blackout","de-energised"]},
            {"component_id": "BUS_7",      "fault_type": "phase_imbalance",    "severity": "major",    "keywords": ["BUS_7","low voltage","0.71","instability"]},
            {"component_id": "BUS_15",     "fault_type": "line_trip",          "severity": "critical", "keywords": ["BUS_15","blackout","wind","cascade"]},
            {"component_id": "BUS_16",     "fault_type": "line_trip",          "severity": "critical", "keywords": ["BUS_16","blackout","downstream","LINE_15_16"]},
        ] + [
            {"component_id": f"BUS_{i}", "fault_type": "line_trip", "severity": "minor",
             "keywords": [f"BUS_{i}", "cascade", "downstream", "affected"],
             "description": f"BUS_{i} affected by cascade from primary fault zones."}
            for i in [22, 23, 17, 18, 19, 8, 9, 10, 24, 25, 26, 27, 28, 29, 30]
        ]
    }
}