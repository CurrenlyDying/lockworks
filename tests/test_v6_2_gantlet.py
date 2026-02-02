"""
LockWorks v6.2: The Geometric Gantlet Test
===========================================

Frame-Matched Fault Injection to prove manifold absorption.

Test Matrix:
    1. NONE (baseline)
    2. MID_X (effective Z after H)
    3. LATE_Z (direct Z - frame-matched to MID_X)
    4. LATE_X (control - should show highest syndrome)

Key Metric:
    SVR_matched = Syndrome(LATE_Z) / Syndrome(MID_X)
    SVR_matched > 10 = Manifold absorbs regardless of basis
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness_v6_2 import WitnessV62
from src.needle import NeedleDriver


def calculate_syndrome(counts: dict) -> dict:
    """Calculate syndrome and state metrics."""
    total = sum(counts.values())
    
    syndrome_1 = 0
    syndrome_0 = 0
    state_101 = 0
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])
        b = int(bits[1])
        a = int(bits[2])
        
        if p != (a ^ b):
            syndrome_1 += count
        else:
            syndrome_0 += count
        
        if state == "101":
            state_101 = count
    
    top_state = max(counts.items(), key=lambda x: x[1])[0] if counts else "000"
    
    return {
        "total": total,
        "syndrome_1": syndrome_1 / total if total > 0 else 0,
        "syndrome_0": syndrome_0 / total if total > 0 else 0,
        "state_101_fidelity": state_101 / total if total > 0 else 0,
        "top_state": top_state
    }


def run_gantlet():
    print("=" * 70)
    print("    LOCKWORKS v6.2: THE GEOMETRIC GANTLET")
    print("    Frame-Matched Fault Injection")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV62(complexity=6)
    
    val_a, val_b = 1, 0
    
    results = []
    tests = [
        ("NONE", "Baseline (No Fault)"),
        ("MID_X", "MID-X (Effective Z after H)"),
        ("LATE_Z", "LATE-Z (Frame-matched to MID-X)"),
        ("LATE_X", "LATE-X (Control - Direct X)"),
    ]
    
    for mode, desc in tests:
        print(f"\n📍 {desc}")
        qc = witness.build_test_circuit(val_a, val_b, fault_mode=mode)
        res = needle.read_circuit(qc)
        analysis = calculate_syndrome(res.raw_counts)
        results.append({"mode": mode, "desc": desc, **analysis, "counts": res.raw_counts})
        print(f"   Top State: |{analysis['top_state']}⟩")
        print(f"   |101⟩ Fidelity: {analysis['state_101_fidelity']:.1%}")
        print(f"   Syndrome=1: {analysis['syndrome_1']:.1%}")
    
    # Calculate SVR_matched
    syndrome_mid_x = results[1]['syndrome_1']
    syndrome_late_z = results[2]['syndrome_1']
    syndrome_late_x = results[3]['syndrome_1']
    
    if syndrome_mid_x > 0:
        svr_matched = syndrome_late_z / syndrome_mid_x
    else:
        svr_matched = float('inf')
    
    # Also calculate SVR for LATE_X vs MID_X
    if syndrome_mid_x > 0:
        svr_x = syndrome_late_x / syndrome_mid_x
    else:
        svr_x = float('inf')
    
    print("\n" + "=" * 70)
    print("    FRAME-MATCHED SVR ANALYSIS")
    print("=" * 70)
    
    print(f"\n   Syndrome (MID_X):  {syndrome_mid_x:.1%}  (effective Z)")
    print(f"   Syndrome (LATE_Z): {syndrome_late_z:.1%}  (frame-matched)")
    print(f"   Syndrome (LATE_X): {syndrome_late_x:.1%}  (control)")
    
    print(f"\n   SVR_matched (LATE_Z / MID_X) = {svr_matched:.1f}")
    print(f"   SVR_control (LATE_X / MID_X) = {svr_x:.1f}")
    
    # Fidelity comparison
    print(f"\n   |101⟩ Fidelity Comparison:")
    print(f"   - Baseline:  {results[0]['state_101_fidelity']:.1%}")
    print(f"   - MID_X:     {results[1]['state_101_fidelity']:.1%}")
    print(f"   - LATE_Z:    {results[2]['state_101_fidelity']:.1%}")
    print(f"   - LATE_X:    {results[3]['state_101_fidelity']:.1%}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if svr_matched > 10:
        print("🏆 FRAME-MATCHED ABSORPTION CONFIRMED!")
        print(f"   SVR_matched = {svr_matched:.1f} > 10")
        print("   The manifold absorbs MID-X even though it's frame-equivalent to LATE-Z.")
        print("   The 'HXH=Z' critique is officially Ohio.")
    elif svr_matched > 5:
        print("⚠️ PARTIAL FRAME-MATCHED ABSORPTION")
        print(f"   SVR_matched = {svr_matched:.1f}")
    elif svr_matched > 2:
        print("📈 SOME DIFFERENTIATION")
        print(f"   SVR_matched = {svr_matched:.1f}")
        print("   Manifold shows preference but not complete absorption.")
    else:
        print("❌ NO FRAME-MATCHED ABSORPTION")
        print("   The HXH=Z conjugation may explain the MID vs LATE difference.")
    
    # Additional insight
    if results[1]['state_101_fidelity'] > 0.80:
        print(f"\n✅ KEY INSIGHT: MID_X still achieves {results[1]['state_101_fidelity']:.1%} fidelity!")
        print("   If HXH=Z were the only story, we'd expect significant phase errors.")
        print("   The manifold is absorbing the effective Z-error too.")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_2_gantlet_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "geometric_gantlet",
            "version": "6.2",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "metrics": {
                "svr_matched": svr_matched if svr_matched != float('inf') else "inf",
                "svr_control": svr_x if svr_x != float('inf') else "inf",
                "syndrome_mid_x": syndrome_mid_x,
                "syndrome_late_z": syndrome_late_z,
                "syndrome_late_x": syndrome_late_x
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results, svr_matched


if __name__ == "__main__":
    run_gantlet()
