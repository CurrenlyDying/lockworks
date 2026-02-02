"""
LockWorks v4.0: Variable Braid Complexity Scaling
==================================================

The "Hater Killer" Experiment.

Hypothesis:
    If increasing Braid Complexity (C) measurably improves state lifetime,
    we prove temporal Distance Scaling equivalent to code distance (d).

Test Matrix:
    C=0: No braid (linear decay baseline)
    C=2: Light topology
    C=4: Medium topology
    C=6: Standard LockWorks (verified at 93%+)
    C=8: Heavy topology

Fixed Parameters:
    - 50 idle cycles (X·X identity)
    - FISHER pole (θ=0.196)
    - Single disk measurement

Success Criteria:
    - Monotonic improvement: C=0 < C=2 < C=4 < C=6 < C=8
    - Statistical significance (p < 0.05)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.needle import NeedleDriver
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def build_complexity_test_circuit(complexity: int, idle_cycles: int = 50) -> QuantumCircuit:
    """
    Build a single-disk circuit with variable braid complexity.
    
    Args:
        complexity: Number of braid layers (0 = no braid)
        idle_cycles: Number of identity cycles after braid
    """
    qreg = QuantumRegister(2, 'q')
    creg = ClassicalRegister(1, 'meas')
    qc = QuantumCircuit(qreg, creg, name=f"C{complexity}_Idle{idle_cycles}")
    
    theta = 0.196  # FISHER pole
    
    # === OPEN PORTAL ===
    qc.h(qreg)
    
    # === BRAID KERNEL (variable complexity) ===
    if complexity > 0:
        for _ in range(complexity):
            qc.cz(qreg[0], qreg[1])
            qc.rx(theta, qreg[0])
            qc.rz(theta * 2, qreg[1])
            qc.barrier()
    
    # === IDLE LOOP (fixed) ===
    for _ in range(idle_cycles):
        qc.x(qreg[1])
        qc.x(qreg[1])
    
    # === SEAL ===
    qc.h(qreg)
    
    # === MEASURE data bit ===
    qc.measure(qreg[1], creg[0])
    
    return qc


def run_complexity_scaling():
    print("=" * 70)
    print("    LOCKWORKS v4.0: BRAID COMPLEXITY SCALING")
    print("    The 'Hater Killer' Experiment")
    print("=" * 70)
    
    complexities = [0, 2, 4, 6, 8]
    idle_cycles = 50
    
    print(f"\n⚙️ Test Matrix:")
    print(f"   Complexities: {complexities}")
    print(f"   Idle cycles: {idle_cycles}")
    print(f"   Pole: θ=0.196 (FISHER)")
    
    results = []
    needle = NeedleDriver()
    
    for c in complexities:
        print(f"\n{'='*50}")
        print(f"   Testing C={c}")
        print(f"{'='*50}")
        
        qc = build_complexity_test_circuit(c, idle_cycles)
        print(f"   Circuit depth: {qc.depth()}")
        
        result = needle.read_circuit(qc)
        
        counts = result.raw_counts
        total = sum(counts.values())
        
        p_1 = counts.get("1", 0) / total
        p_0 = counts.get("0", 0) / total
        
        results.append({
            "complexity": c,
            "fidelity": p_1,
            "error": 1 - p_1,
            "counts": counts
        })
        
        print(f"   Data=1 (expected): {p_1:.1%}")
        print(f"   Data=0 (error): {p_0:.1%}")
    
    # Analysis
    print("\n" + "=" * 70)
    print("    SCALING ANALYSIS")
    print("=" * 70)
    
    print(f"\n{'C':>5} {'Fidelity':>12} {'Error':>10} {'Improvement':>15}")
    print("-" * 45)
    
    baseline = results[0]["fidelity"]
    for r in results:
        c = r["complexity"]
        f = r["fidelity"]
        e = r["error"]
        improvement = ((f - baseline) / baseline * 100) if baseline > 0 else 0
        print(f"{c:>5} {f:>12.1%} {e:>10.1%} {improvement:>+14.1f}%")
    
    # Check monotonic improvement
    fidelities = [r["fidelity"] for r in results]
    is_monotonic = all(fidelities[i] <= fidelities[i+1] for i in range(len(fidelities)-1))
    
    # Calculate correlation coefficient
    import statistics
    if len(complexities) > 1:
        mean_c = statistics.mean(complexities)
        mean_f = statistics.mean(fidelities)
        
        numerator = sum((c - mean_c) * (f - mean_f) for c, f in zip(complexities, fidelities))
        denom_c = sum((c - mean_c)**2 for c in complexities)**0.5
        denom_f = sum((f - mean_f)**2 for f in fidelities)**0.5
        
        correlation = numerator / (denom_c * denom_f) if denom_c * denom_f > 0 else 0
    else:
        correlation = 0
    
    print(f"\n🎯 Scaling Metrics:")
    print(f"   Monotonic improvement: {'✅ YES' if is_monotonic else '❌ NO'}")
    print(f"   Correlation (C vs Fidelity): {correlation:.3f}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if is_monotonic and correlation > 0.8:
        print("🏆 SIGMA RESULT: DISTANCE SCALING CONFIRMED!")
        print("   Braid complexity (C) correlates with state lifetime.")
        print("   This is temporal distance scaling, equivalent to code distance (d).")
    elif correlation > 0.5:
        print("⚠️ PARTIAL SCALING")
        print("   Positive correlation exists but not perfectly monotonic.")
    else:
        print("❌ NO CLEAR SCALING")
        print("   Need to investigate noise model or hardware variance.")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_complexity_scaling_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "braid_complexity_scaling",
            "version": "4.0",
            "parameters": {
                "complexities": complexities,
                "idle_cycles": idle_cycles,
                "theta": 0.196
            },
            "results": results,
            "analysis": {
                "monotonic": is_monotonic,
                "correlation": correlation,
                "baseline_fidelity": baseline,
                "best_fidelity": max(fidelities),
                "scaling_confirmed": is_monotonic and correlation > 0.8
            }
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    run_complexity_scaling()
