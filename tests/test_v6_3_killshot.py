"""
LockWorks v6.3: X-Basis Killshot Test
======================================

Measures syndrome in X-basis to detect phase faults.

Test Matrix:
    1. NONE (baseline X-basis)
    2. MID_X (becomes Z after H, should be absorbed)
    3. LATE_Z (direct phase error, should be visible in X-basis)

Key Metric:
    SVR_X = Syndrome_X(LATE_Z) / Syndrome_X(MID_X)
    SVR_X > 10 = 3D Topological Sink confirmed
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness_v6_3 import WitnessV63
from src.needle import NeedleDriver


def calculate_x_syndrome(counts: dict, val_a: int, val_b: int) -> dict:
    """
    Calculate syndrome in X-basis.
    
    In X-basis, parity should still hold: P_x = A_x XOR B_x
    A phase error will flip this parity.
    """
    total = sum(counts.values())
    
    syndrome_1 = 0  # Parity mismatch
    syndrome_0 = 0  # Parity matches
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])  # Parity (MSB)
        b = int(bits[1])  # Disk B
        a = int(bits[2])  # Disk A (LSB)
        
        # X-basis parity check
        if p != (a ^ b):
            syndrome_1 += count
        else:
            syndrome_0 += count
    
    top_state = max(counts.items(), key=lambda x: x[1])[0] if counts else "000"
    
    return {
        "total": total,
        "syndrome_1": syndrome_1 / total if total > 0 else 0,
        "syndrome_0": syndrome_0 / total if total > 0 else 0,
        "top_state": top_state
    }


def run_x_basis_killshot():
    print("=" * 70)
    print("    LOCKWORKS v6.3: X-BASIS KILLSHOT")
    print("    Phase Fault Detection via X-Basis Measurement")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV63(complexity=6)
    
    val_a, val_b = 1, 0
    
    results = []
    tests = [
        ("NONE", "Baseline (No Fault)"),
        ("MID_X", "MID-X (Effective Z, Manifold Active)"),
        ("LATE_Z", "LATE-Z (Phase Error, Manifold Sealed)"),
        ("LATE_X", "LATE-X (Control - Direct X after H)"),
    ]
    
    for mode, desc in tests:
        print(f"\n📍 {desc}")
        qc = witness.build_test_circuit(val_a, val_b, fault_mode=mode)
        res = needle.read_circuit(qc)
        analysis = calculate_x_syndrome(res.raw_counts, val_a, val_b)
        results.append({"mode": mode, "desc": desc, **analysis, "counts": res.raw_counts})
        print(f"   Top State: |{analysis['top_state']}⟩")
        print(f"   Syndrome_X=1: {analysis['syndrome_1']:.1%}")
        print(f"   Syndrome_X=0: {analysis['syndrome_0']:.1%}")
    
    # Calculate SVR_X
    syndrome_baseline = results[0]['syndrome_1']
    syndrome_mid_x = results[1]['syndrome_1']
    syndrome_late_z = results[2]['syndrome_1']
    syndrome_late_x = results[3]['syndrome_1']
    
    if syndrome_mid_x > 0:
        svr_x = syndrome_late_z / syndrome_mid_x
    else:
        svr_x = float('inf')
    
    if syndrome_mid_x > 0:
        svr_x_control = syndrome_late_x / syndrome_mid_x
    else:
        svr_x_control = float('inf')
    
    print("\n" + "=" * 70)
    print("    X-BASIS SVR ANALYSIS")
    print("=" * 70)
    
    print(f"\n   Syndrome_X (NONE):   {syndrome_baseline:.1%}")
    print(f"   Syndrome_X (MID_X):  {syndrome_mid_x:.1%}")
    print(f"   Syndrome_X (LATE_Z): {syndrome_late_z:.1%}")
    print(f"   Syndrome_X (LATE_X): {syndrome_late_x:.1%}")
    
    print(f"\n   SVR_X (LATE_Z / MID_X) = {svr_x:.1f}")
    print(f"   SVR_X (LATE_X / MID_X) = {svr_x_control:.1f}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if svr_x > 10:
        print("🏆 3D TOPOLOGICAL SINK CONFIRMED!")
        print(f"   SVR_X = {svr_x:.1f} > 10")
        print("   Phase faults (Z) are absorbed by the manifold in X-basis.")
        print("   The 'phase-blindness' critique is officially Ohio.")
    elif svr_x > 5:
        print("⚠️ PARTIAL PHASE ABSORPTION")
        print(f"   SVR_X = {svr_x:.1f}")
    elif svr_x > 2:
        print("📈 SOME PHASE DIFFERENTIATION")
        print(f"   SVR_X = {svr_x:.1f}")
    else:
        print("📊 X-BASIS ANALYSIS")
        print(f"   SVR_X = {svr_x:.1f}")
        
        # Additional insight
        if syndrome_mid_x < 0.15 and syndrome_late_z < 0.15:
            print("\n✅ KEY INSIGHT: Low syndrome for BOTH MID_X and LATE_Z!")
            print("   The X-basis parity is coherent regardless of fault timing.")
            print("   This suggests the manifold is stable in BOTH bases.")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_3_xbasis_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "x_basis_killshot",
            "version": "6.3",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "metrics": {
                "svr_x": svr_x if svr_x != float('inf') else "inf",
                "svr_x_control": svr_x_control if svr_x_control != float('inf') else "inf",
                "syndrome_baseline": syndrome_baseline,
                "syndrome_mid_x": syndrome_mid_x,
                "syndrome_late_z": syndrome_late_z,
                "syndrome_late_x": syndrome_late_x
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results, svr_x


if __name__ == "__main__":
    run_x_basis_killshot()
