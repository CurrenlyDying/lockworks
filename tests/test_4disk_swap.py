"""
CTM 4-Disk Swap Test
====================

Tests inter-core routing by creating 2 core pairs and swapping values.

Setup:
    Core A: Disk 0 (value=1) ↔ Disk 1 (value=0)
    Core B: Disk 2 (value=0) ↔ Disk 3 (value=1)

Operation:
    1. Initialize all disks with their values
    2. LINK Disk 1 to Disk 2 (inter-core routing)
    3. Verify propagation across cores

Expected:
    After LINK(1,2): Disk 2 should flip if Disk 1 = 1
    
Target: Inter-core fidelity > 80%
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder
from src.needle import NeedleDriver
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def build_4disk_swap_circuit(complexity: int = 6) -> QuantumCircuit:
    """
    Build a 4-disk circuit with inter-core LINK.
    
    Uses v3.2 Anchor Sequence with inverted CX.
    """
    # 4 disks = 8 qubits (2 per disk)
    qreg = QuantumRegister(8, 'q')
    creg = ClassicalRegister(4, 'meas')
    qc = QuantumCircuit(qreg, creg, name="4Disk_Swap")
    
    # Disk indices (phase, data)
    disks = [
        (0, 1),  # Disk 0
        (2, 3),  # Disk 1
        (4, 5),  # Disk 2
        (6, 7),  # Disk 3
    ]
    
    # Values: Disk 0=1, Disk 1=0, Disk 2=0, Disk 3=1
    thetas = [0.196, 0.0, 0.0, 0.196]
    
    # === LAYER 1: OPEN PORTAL ===
    qc.h(qreg)
    
    # === LAYER 2: HARDEN Disk 1 (the inter-core source) ===
    p, d = disks[1]
    theta = thetas[1]
    for _ in range(complexity):
        qc.cz(qreg[p], qreg[d])
        qc.rx(theta, qreg[p])
        qc.rz(theta * 2, qreg[d])
        qc.barrier([qreg[p], qreg[d]])
    
    # === LAYER 3: INTER-CORE LINK (1 → 2) with inverted CX ===
    qc.barrier()
    # Inverted: CX(target, control) based on v3.2 findings
    qc.cx(qreg[disks[2][1]], qreg[disks[1][1]])  # CX(Disk2.data, Disk1.data)
    qc.barrier()
    
    # === LAYER 4: BRAID remaining disks ===
    for i in [0, 2, 3]:  # Skip Disk 1 (already braided)
        p, d = disks[i]
        theta = thetas[i]
        for _ in range(complexity):
            qc.cz(qreg[p], qreg[d])
            qc.rx(theta, qreg[p])
            qc.rz(theta * 2, qreg[d])
            qc.barrier([qreg[p], qreg[d]])
    
    # === LAYER 5: SEAL ===
    qc.h(qreg)
    
    # === LAYER 6: MEASURE data bits ===
    for i, (_, d) in enumerate(disks):
        qc.measure(qreg[d], creg[i])
    
    return qc


def test_4disk_swap():
    print("=" * 70)
    print("    CTM 4-DISK SWAP TEST")
    print("    Inter-Core Routing Verification")
    print("=" * 70)
    
    print("\n📦 Configuration:")
    print("   Core A: Disk 0=1, Disk 1=0")
    print("   Core B: Disk 2=0, Disk 3=1")
    print("   LINK: Disk 1 → Disk 2 (inter-core)")
    
    # Build circuit
    qc = build_4disk_swap_circuit()
    print(f"\n🔨 Circuit depth: {qc.depth()}")
    
    # Run on QPU
    print("\n🚀 Submitting to IBM Quantum...")
    needle = NeedleDriver()
    result = needle.read_circuit(qc)
    
    # Analyze
    counts = result.raw_counts
    total = sum(counts.values())
    
    print("\n📊 Top Results:")
    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])[:8]
    for state, count in sorted_counts:
        pct = count / total * 100
        print(f"   |{state}⟩: {pct:.1f}%")
    
    # Check inter-core correlation
    # Expected: Disk 1 and Disk 2 should correlate
    d1_d2_corr = 0
    for state, count in counts.items():
        bits = state.zfill(4)
        d1 = int(bits[-2])  # Disk 1 (2nd from right)
        d2 = int(bits[-3])  # Disk 2 (3rd from right)
        if d1 == d2:  # Correlated
            d1_d2_corr += count
    
    corr_pct = d1_d2_corr / total
    
    print(f"\n🎯 Inter-Core Metrics:")
    print(f"   Disk 1 ↔ Disk 2 Correlation: {corr_pct:.1%}")
    
    success = corr_pct > 0.80
    
    if success:
        print("\n✅ 4-DISK SWAP VERIFIED!")
        print("   Inter-core routing works at >80% fidelity.")
    elif corr_pct > 0.60:
        print("\n⚠️ PARTIAL SUCCESS")
        print(f"   Correlation {corr_pct:.1%} is decent but below 80% target")
    else:
        print("\n❌ INTER-CORE ROUTING FAILED")
        print("   Need to investigate crosstalk or mapping")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_4disk_swap_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "test": "4disk_swap",
            "config": {
                "disk_values": [1, 0, 0, 1],
                "link": "1→2 (inverted CX)"
            },
            "results": {
                "intercore_correlation": corr_pct,
                "top_states": dict(sorted_counts)
            },
            "counts": counts,
            "success": success
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return success


if __name__ == "__main__":
    test_4disk_swap()
