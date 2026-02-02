"""
CTM 100-Cycle Idle Loop Test
=============================

Tests manifold stability by running a simple braid through 100 idle cycles.

The idle loop applies identity operations (X·X) to maintain the manifold
without changing the logical state. This tests:
    1. Topological stability over extended time
    2. Decoherence resilience
    3. Error accumulation

Setup:
    - Single disk at FISHER pole (θ=0.196)
    - Apply 100 identity cycles (X·X per cycle)
    - Measure final state

Target: FISHER pole should maintain >80% fidelity after 100 cycles.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder
from src.needle import NeedleDriver
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def build_idle_loop_circuit(n_cycles: int = 100, complexity: int = 6) -> QuantumCircuit:
    """
    Build a circuit with n_cycles of idle (identity) operations.
    
    Uses X·X identity to maintain coherence without logical change.
    """
    # 1 disk = 2 qubits
    qreg = QuantumRegister(2, 'q')
    creg = ClassicalRegister(1, 'meas')
    qc = QuantumCircuit(qreg, creg, name=f"Idle_{n_cycles}")
    
    theta = 0.196  # FISHER pole
    
    # === OPEN PORTAL ===
    qc.h(qreg)
    
    # === BRAID (standard complexity) ===
    for _ in range(complexity):
        qc.cz(qreg[0], qreg[1])
        qc.rx(theta, qreg[0])
        qc.rz(theta * 2, qreg[1])
        qc.barrier()
    
    # === IDLE LOOP ===
    # Apply n_cycles of X·X identity on data bit
    for _ in range(n_cycles):
        qc.x(qreg[1])  # Flip
        qc.x(qreg[1])  # Flip back (= identity)
    
    # === SEAL ===
    qc.h(qreg)
    
    # === MEASURE data bit ===
    qc.measure(qreg[1], creg[0])
    
    return qc


def test_idle_loop(n_cycles: int = 100):
    print("=" * 70)
    print(f"    CTM IDLE LOOP TEST ({n_cycles} cycles)")
    print("    Manifold Stability Verification")
    print("=" * 70)
    
    print(f"\n⚙️ Configuration:")
    print(f"   Disk: θ=0.196 (FISHER)")
    print(f"   Idle cycles: {n_cycles}")
    print(f"   Operation: X·X (identity)")
    
    # Build circuit
    qc = build_idle_loop_circuit(n_cycles)
    print(f"\n🔨 Circuit depth: {qc.depth()}")
    print(f"   Gate count: {qc.size()}")
    
    # Run on QPU
    print("\n🚀 Submitting to IBM Quantum...")
    needle = NeedleDriver()
    result = needle.read_circuit(qc)
    
    # Analyze
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_0 = counts.get("0", 0) / total
    p_1 = counts.get("1", 0) / total
    
    print("\n📊 Results:")
    print(f"   Data=0: {p_0:.1%}")
    print(f"   Data=1: {p_1:.1%}")
    
    # FISHER pole should read as 1
    success = p_1 > 0.80
    
    print(f"\n🎯 Stability Metrics:")
    print(f"   Expected: Data=1 (FISHER)")
    print(f"   Observed: {p_1:.1%}")
    print(f"   Degradation: {100 - p_1*100:.1f}%")
    
    if success:
        print(f"\n✅ MANIFOLD STABLE after {n_cycles} idle cycles!")
        print(f"   {p_1:.1%} fidelity maintained")
    elif p_1 > 0.60:
        print(f"\n⚠️ PARTIAL STABILITY")
        print(f"   Some degradation ({p_1:.1%}), but manifold intact")
    else:
        print(f"\n❌ MANIFOLD COLLAPSED")
        print(f"   Too much decoherence over {n_cycles} cycles")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_idle_loop_{n_cycles}c_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "test": "idle_loop",
            "n_cycles": n_cycles,
            "config": {
                "theta": 0.196,
                "expected_value": 1
            },
            "results": {
                "p_0": p_0,
                "p_1": p_1,
                "fidelity": p_1,
                "degradation": 1 - p_1
            },
            "counts": counts,
            "success": success
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return success


if __name__ == "__main__":
    test_idle_loop(100)
