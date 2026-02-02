"""
LockWorks v6.1: Attractor Audit
================================

Calculative audit of the Fault-Absorbing Manifold.

Tests:
    1. NO FAULT (baseline)
    2. MID Injection (in-manifold) → Expected: absorbed, |101⟩ dominates
    3. LATE Injection (post-manifold) → Expected: visible syndrome

Key Metric:
    SVR = Syndrome_Late / Syndrome_Mid
    SVR > 10 = Fault-Absorbing Manifold confirmed
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness_v6_1 import WitnessV6
from src.needle import NeedleDriver


def calculate_syndrome(counts: dict, val_a: int, val_b: int) -> dict:
    """
    Calculate syndrome metrics.
    
    Syndrome = 1 if P ≠ A⊕B (parity mismatch detected)
    """
    total = sum(counts.values())
    
    original_parity = val_a ^ val_b
    
    syndrome_1 = 0  # Parity mismatch (error detected)
    syndrome_0 = 0  # Parity matches (no error visible)
    
    state_101 = 0  # The "correct" attractor for A=1, B=0
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])  # Parity (MSB)
        b = int(bits[1])  # Disk B
        a = int(bits[2])  # Disk A (LSB)
        
        current_parity_check = a ^ b
        
        if p != current_parity_check:
            syndrome_1 += count  # Mismatch detected
        else:
            syndrome_0 += count  # Parity matches
        
        if state == "101":
            state_101 = count
    
    return {
        "total": total,
        "syndrome_1": syndrome_1 / total,  # Error detected
        "syndrome_0": syndrome_0 / total,  # No visible error
        "state_101_fidelity": state_101 / total,
        "top_state": max(counts.items(), key=lambda x: x[1])[0]
    }


def run_attractor_audit():
    print("=" * 70)
    print("    LOCKWORKS v6.1: ATTRACTOR AUDIT")
    print("    Fault-Absorbing Manifold Verification")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV6(complexity=6)
    
    val_a, val_b = 1, 0  # Expected parity = 1, attractor = |101⟩
    
    results = []
    
    # === TEST 1: NO FAULT (Baseline) ===
    print("\n📍 Test 1: No Fault (Baseline)")
    qc = witness.build_test_circuit(val_a, val_b, fault_mode='NONE')
    res = needle.read_circuit(qc)
    analysis = calculate_syndrome(res.raw_counts, val_a, val_b)
    results.append({"mode": "NONE", **analysis, "counts": res.raw_counts})
    print(f"   Top State: |{analysis['top_state']}⟩")
    print(f"   |101⟩ Fidelity: {analysis['state_101_fidelity']:.1%}")
    print(f"   Syndrome=1: {analysis['syndrome_1']:.1%}")
    
    # === TEST 2: MID Injection (In-Manifold) ===
    print("\n📍 Test 2: MID Injection (In-Manifold)")
    print("   Fault injected AFTER braid, BEFORE seal")
    qc = witness.build_test_circuit(val_a, val_b, fault_mode='MID')
    res = needle.read_circuit(qc)
    analysis = calculate_syndrome(res.raw_counts, val_a, val_b)
    results.append({"mode": "MID", **analysis, "counts": res.raw_counts})
    print(f"   Top State: |{analysis['top_state']}⟩")
    print(f"   |101⟩ Fidelity: {analysis['state_101_fidelity']:.1%}")
    print(f"   Syndrome=1: {analysis['syndrome_1']:.1%}")
    
    syndrome_mid = analysis['syndrome_1']
    
    # === TEST 3: LATE Injection (Post-Manifold) ===
    print("\n📍 Test 3: LATE Injection (Post-Manifold)")
    print("   Fault injected AFTER seal, BEFORE measure")
    qc = witness.build_test_circuit(val_a, val_b, fault_mode='LATE')
    res = needle.read_circuit(qc)
    analysis = calculate_syndrome(res.raw_counts, val_a, val_b)
    results.append({"mode": "LATE", **analysis, "counts": res.raw_counts})
    print(f"   Top State: |{analysis['top_state']}⟩")
    print(f"   |101⟩ Fidelity: {analysis['state_101_fidelity']:.1%}")
    print(f"   Syndrome=1: {analysis['syndrome_1']:.1%}")
    
    syndrome_late = analysis['syndrome_1']
    
    # === SYNDROME VISIBILITY RATIO ===
    print("\n" + "=" * 70)
    print("    SVR CALCULATION")
    print("=" * 70)
    
    if syndrome_mid > 0:
        svr = syndrome_late / syndrome_mid
    else:
        svr = float('inf')
    
    print(f"\n   Syndrome (MID):  {syndrome_mid:.1%}")
    print(f"   Syndrome (LATE): {syndrome_late:.1%}")
    print(f"\n   SVR = {svr:.1f}")
    
    # === POST-SELECTION LIFT ===
    baseline_fidelity = results[0]['state_101_fidelity']
    mid_fidelity = results[1]['state_101_fidelity']
    
    # Post-select on syndrome=0 for MID injection
    ps_lift = 0
    if results[1]['syndrome_0'] > 0:
        # Calculate fidelity when we post-select on syndrome=0
        counts = results[1]['counts']
        total = results[1]['total']
        
        syndrome_0_counts = {}
        for state, count in counts.items():
            bits = state.zfill(3)
            p, b, a = int(bits[0]), int(bits[1]), int(bits[2])
            if p == (a ^ b):  # Syndrome = 0
                syndrome_0_counts[state] = count
        
        s0_total = sum(syndrome_0_counts.values())
        s0_101 = syndrome_0_counts.get("101", 0)
        ps_fidelity = s0_101 / s0_total if s0_total > 0 else 0
        ps_lift = (ps_fidelity - mid_fidelity) / mid_fidelity * 100 if mid_fidelity > 0 else 0
        
        print(f"\n   Post-Selection (s=0) Fidelity: {ps_fidelity:.1%}")
        print(f"   Raw Fidelity: {mid_fidelity:.1%}")
        print(f"   Lift: {ps_lift:+.1f}%")
    
    # === VERDICT ===
    print("\n" + "=" * 70)
    
    if svr > 10:
        print("🏆 FAULT-ABSORBING MANIFOLD CONFIRMED!")
        print(f"   SVR = {svr:.1f} > 10")
        print("   MID faults are absorbed, LATE faults are visible.")
        print("   The manifold has a Topological Return-to-Home function.")
    elif svr > 5:
        print("⚠️ PARTIAL ABSORPTION")
        print(f"   SVR = {svr:.1f}")
        print("   Manifold shows absorption but not complete.")
    elif svr > 2:
        print("📈 SOME DIFFERENTIATION")
        print(f"   SVR = {svr:.1f}")
    else:
        print("❌ NO CLEAR ABSORPTION")
        print("   Need to investigate timing/topology.")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_1_attractor_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "attractor_audit",
            "version": "6.1",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "metrics": {
                "svr": svr if svr != float('inf') else "inf",
                "syndrome_mid": syndrome_mid,
                "syndrome_late": syndrome_late,
                "post_selection_lift": ps_lift
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results, svr


if __name__ == "__main__":
    run_attractor_audit()
