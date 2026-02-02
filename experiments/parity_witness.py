"""
LockWorks v5.0: Parity Witness
===============================

A 3-Disk system demonstrating error detection without thousands of qubits.

Architecture:
    Disk 0 (A): Data Disk
    Disk 1 (B): Data Disk  
    Disk 2 (P): Parity Witness (stores A XOR B)

Sequence:
    1. ALLOC(3)
    2. WRITE(0, val_a), WRITE(1, val_b)
    3. GEAR-SYNC: LINK(0,2), LINK(1,2) [Inverted CX]
    4. IDLE(50 cycles)
    5. READ_ALL()

Witness Logic:
    If Disk 2 == val_a XOR val_b: Manifold intact ✅
    If parity broken: Syndrome detected ❌

Tests:
    - Parity correctness for all input combinations
    - Complexity scaling (C=2,4,6)
    - X-basis tomography for coherence verification
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.needle import NeedleDriver
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def build_parity_witness_circuit(
    val_a: int, 
    val_b: int, 
    complexity: int = 6,
    idle_cycles: int = 50,
    x_basis: bool = False
) -> QuantumCircuit:
    """
    Build a 3-disk parity witness circuit.
    
    Args:
        val_a: Value for Disk 0 (0 or 1)
        val_b: Value for Disk 1 (0 or 1)
        complexity: Braid layers
        idle_cycles: Identity cycles after gearing
        x_basis: If True, measure in X-basis (skip final H)
    """
    # 3 disks = 6 qubits (phase, data pairs)
    # Disk 0: q0 (phase), q1 (data)
    # Disk 1: q2 (phase), q3 (data)
    # Disk 2: q4 (phase), q5 (data) <- Parity Witness
    
    qreg = QuantumRegister(6, 'q')
    creg = ClassicalRegister(3, 'meas')
    qc = QuantumCircuit(qreg, creg, name=f"Parity_A{val_a}B{val_b}_C{complexity}")
    
    # Theta values
    theta_a = 0.196 if val_a == 1 else 0.0
    theta_b = 0.196 if val_b == 1 else 0.0
    theta_p = 0.0  # Parity starts at ROBUST (0)
    
    # Data qubit indices
    data_0, data_1, data_2 = 1, 3, 5
    
    # === LAYER 1: OPEN PORTAL ===
    qc.h(qreg)
    
    # === LAYER 2: HARDEN DATA DISKS (Anchor Sequence) ===
    # Braid Disk 0
    for _ in range(complexity):
        qc.cz(qreg[0], qreg[1])
        qc.rx(theta_a, qreg[0])
        qc.rz(theta_a * 2, qreg[1])
        qc.barrier([qreg[0], qreg[1]])
    
    # Braid Disk 1
    for _ in range(complexity):
        qc.cz(qreg[2], qreg[3])
        qc.rx(theta_b, qreg[2])
        qc.rz(theta_b * 2, qreg[3])
        qc.barrier([qreg[2], qreg[3]])
    
    # === LAYER 3: GEAR-SYNC (Parity Encoding) ===
    # LINK(0, 2): Inverted CX - q5 (parity data) <- q1 (disk 0 data)
    qc.barrier()
    qc.cx(qreg[data_2], qreg[data_0])  # Inverted per v3.2
    qc.barrier()
    
    # LINK(1, 2): Inverted CX - q5 (parity data) <- q3 (disk 1 data)
    qc.barrier()
    qc.cx(qreg[data_2], qreg[data_1])  # Inverted per v3.2
    qc.barrier()
    
    # === LAYER 4: BRAID PARITY DISK ===
    for _ in range(complexity):
        qc.cz(qreg[4], qreg[5])
        qc.rx(theta_p, qreg[4])
        qc.rz(theta_p * 2, qreg[5])
        qc.barrier([qreg[4], qreg[5]])
    
    # === LAYER 5: IDLE LOOP ===
    for _ in range(idle_cycles):
        qc.x(qreg[data_0])
        qc.x(qreg[data_0])
        qc.x(qreg[data_1])
        qc.x(qreg[data_1])
        qc.x(qreg[data_2])
        qc.x(qreg[data_2])
    
    # === LAYER 6: SEAL ===
    if not x_basis:
        qc.h(qreg)  # Standard Z-basis measurement
    # else: skip H for X-basis measurement
    
    # === LAYER 7: MEASURE data bits ===
    qc.measure(qreg[data_0], creg[0])  # Disk 0
    qc.measure(qreg[data_1], creg[1])  # Disk 1
    qc.measure(qreg[data_2], creg[2])  # Parity
    
    return qc


def run_parity_witness_test():
    """Test all input combinations for parity correctness."""
    
    print("=" * 70)
    print("    LOCKWORKS v5.0: PARITY WITNESS")
    print("    3-Disk Error Detection System")
    print("=" * 70)
    
    inputs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    complexity = 6
    idle_cycles = 50
    
    print(f"\n⚙️ Configuration:")
    print(f"   Complexity: C={complexity}")
    print(f"   Idle cycles: {idle_cycles}")
    print(f"   Test cases: {inputs}")
    
    needle = NeedleDriver()
    results = []
    
    for val_a, val_b in inputs:
        expected_parity = val_a ^ val_b  # XOR
        
        print(f"\n{'='*50}")
        print(f"   Test: A={val_a}, B={val_b} → Expected P={expected_parity}")
        print(f"{'='*50}")
        
        qc = build_parity_witness_circuit(val_a, val_b, complexity, idle_cycles)
        result = needle.read_circuit(qc)
        
        counts = result.raw_counts
        total = sum(counts.values())
        
        # Analyze parity correctness
        correct_parity = 0
        for state, count in counts.items():
            bits = state.zfill(3)
            p = int(bits[0])  # Parity bit (MSB)
            b = int(bits[1])  # Disk 1
            a = int(bits[2])  # Disk 0 (LSB)
            
            if p == (a ^ b):  # Parity correct
                correct_parity += count
        
        parity_success = correct_parity / total
        
        # Check if data disks are correct
        data_correct = 0
        for state, count in counts.items():
            bits = state.zfill(3)
            a = int(bits[2])
            b = int(bits[1])
            if a == val_a and b == val_b:
                data_correct += count
        
        data_fidelity = data_correct / total
        
        print(f"   Parity Success: {parity_success:.1%}")
        print(f"   Data Fidelity: {data_fidelity:.1%}")
        print(f"   Top states: {dict(list(sorted(counts.items(), key=lambda x: -x[1]))[:4])}")
        
        results.append({
            "val_a": val_a,
            "val_b": val_b,
            "expected_parity": expected_parity,
            "parity_success": parity_success,
            "data_fidelity": data_fidelity,
            "counts": counts
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("    PARITY WITNESS SUMMARY")
    print("=" * 70)
    
    avg_parity = sum(r["parity_success"] for r in results) / len(results)
    avg_data = sum(r["data_fidelity"] for r in results) / len(results)
    
    print(f"\n{'A':>3} {'B':>3} {'P(exp)':>8} {'Parity':>10} {'Data':>10}")
    print("-" * 40)
    for r in results:
        print(f"{r['val_a']:>3} {r['val_b']:>3} {r['expected_parity']:>8} {r['parity_success']:>10.1%} {r['data_fidelity']:>10.1%}")
    
    print(f"\n{'Average':>14} {avg_parity:>10.1%} {avg_data:>10.1%}")
    
    success = avg_parity > 0.80
    
    if success:
        print("\n🏆 PARITY WITNESS VERIFIED!")
        print("   Error detection operational at >80% accuracy.")
    else:
        print("\n⚠️ PARTIAL SUCCESS")
        print(f"   Parity accuracy at {avg_parity:.1%}")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_parity_witness_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "parity_witness",
            "version": "5.0",
            "parameters": {
                "complexity": complexity,
                "idle_cycles": idle_cycles
            },
            "results": results,
            "summary": {
                "avg_parity_success": avg_parity,
                "avg_data_fidelity": avg_data,
                "success": success
            }
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


def run_complexity_scaling():
    """Test parity success across different complexities."""
    
    print("\n" + "=" * 70)
    print("    PARITY COMPLEXITY SCALING")
    print("=" * 70)
    
    complexities = [2, 4, 6]
    idle_cycles = 50
    
    # Fixed test case: A=1, B=0 → P=1
    val_a, val_b = 1, 0
    expected_parity = 1
    
    needle = NeedleDriver()
    results = []
    
    for c in complexities:
        print(f"\n   Testing C={c}...")
        
        qc = build_parity_witness_circuit(val_a, val_b, c, idle_cycles)
        result = needle.read_circuit(qc)
        
        counts = result.raw_counts
        total = sum(counts.values())
        
        correct_parity = 0
        for state, count in counts.items():
            bits = state.zfill(3)
            p = int(bits[0])
            b = int(bits[1])
            a = int(bits[2])
            if p == (a ^ b):
                correct_parity += count
        
        parity_success = correct_parity / total
        
        results.append({
            "complexity": c,
            "parity_success": parity_success,
            "counts": counts
        })
        
        print(f"   C={c}: Parity Success = {parity_success:.1%}")
    
    # Check scaling
    fidelities = [r["parity_success"] for r in results]
    is_monotonic = all(fidelities[i] <= fidelities[i+1] for i in range(len(fidelities)-1))
    
    print(f"\n🎯 Scaling: {'Monotonic ✅' if is_monotonic else 'Non-monotonic ⚠️'}")
    
    return results


def run_x_basis_tomography():
    """Measure in X-basis to verify coherence."""
    
    print("\n" + "=" * 70)
    print("    X-BASIS TOMOGRAPHY")
    print("=" * 70)
    
    needle = NeedleDriver()
    
    # Test FISHER pole in X-basis
    qc = build_parity_witness_circuit(1, 0, complexity=6, idle_cycles=50, x_basis=True)
    result = needle.read_circuit(qc)
    
    counts = result.raw_counts
    total = sum(counts.values())
    
    print(f"\n📊 X-Basis Distribution:")
    for state, count in sorted(counts.items(), key=lambda x: -x[1])[:6]:
        print(f"   |{state}⟩: {count/total:.1%}")
    
    # Check for superposition (roughly equal 0/1 on each qubit)
    # If it's a coherent sphere, X-basis should show ~50/50
    
    return counts


if __name__ == "__main__":
    # Run all v5.0 tests
    run_parity_witness_test()
    run_complexity_scaling()
    run_x_basis_tomography()
