"""
LockWorks v6.4: Phase Stabilizer Audit
=======================================

Tests phase absorption using H-conjugated X-parity encoding.

Test Matrix:
    1. NONE (baseline) - Expected: ~6% syndrome (noise floor)
    2. MID_Z (in-manifold) - Expected: ~6% (phase absorbed)
    3. LATE_Z (post-lock) - Expected: ~95% (phase visible)

Key Metric:
    SVR_X = Syndrome_X(LATE_Z) / Syndrome_X(MID_Z)
    SVR_X > 10 = 3D Phase Absorption confirmed
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness_v6_4 import WitnessV64
from src.needle import NeedleDriver


def calculate_x_syndrome(counts: dict) -> dict:
    """
    Calculate X-basis parity syndrome.
    
    For X-parity encoding: P_x = A_x ⊕ B_x
    Syndrome = 1 if parity doesn't match.
    """
    total = sum(counts.values())
    
    syndrome_1 = 0  # Parity mismatch
    syndrome_0 = 0  # Parity matches
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])  # Parity (MSB)
        b = int(bits[1])  # Disk B
        a = int(bits[2])  # Disk A (LSB)
        
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


def run_phase_stabilizer_audit():
    print("=" * 70)
    print("    LOCKWORKS v6.4: PHASE STABILIZER AUDIT")
    print("    Proving 3D Manifold Absorption")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV64(complexity=6)
    
    # Use ROBUST poles (val=0) for maximum symmetry
    val_a, val_b = 0, 0
    
    results = []
    tests = [
        ("NONE", "Baseline (No Fault)"),
        ("MID_Z", "MID-Z (Phase Fault in Manifold)"),
        ("LATE_Z", "LATE-Z (Phase Fault after Lock)"),
    ]
    
    for mode, desc in tests:
        print(f"\n📍 {desc}")
        qc = witness.build_phase_protected_circuit(val_a, val_b, fault_mode=mode)
        res = needle.read_circuit(qc)
        analysis = calculate_x_syndrome(res.raw_counts)
        results.append({"mode": mode, "desc": desc, **analysis, "counts": res.raw_counts})
        print(f"   Top State: |{analysis['top_state']}⟩")
        print(f"   Syndrome_X=1: {analysis['syndrome_1']:.1%}")
        print(f"   Syndrome_X=0: {analysis['syndrome_0']:.1%}")
    
    # Calculate SVR_X
    syndrome_none = results[0]['syndrome_1']
    syndrome_mid_z = results[1]['syndrome_1']
    syndrome_late_z = results[2]['syndrome_1']
    
    if syndrome_mid_z > 0:
        svr_x = syndrome_late_z / syndrome_mid_z
    else:
        svr_x = float('inf')
    
    print("\n" + "=" * 70)
    print("    PHASE ABSORPTION ANALYSIS")
    print("=" * 70)
    
    print(f"\n   Syndrome_X (NONE):   {syndrome_none:.1%}")
    print(f"   Syndrome_X (MID_Z):  {syndrome_mid_z:.1%}")
    print(f"   Syndrome_X (LATE_Z): {syndrome_late_z:.1%}")
    
    print(f"\n   SVR_X (LATE_Z / MID_Z) = {svr_x:.1f}")
    
    # Delta from baseline
    delta_mid = syndrome_mid_z - syndrome_none
    delta_late = syndrome_late_z - syndrome_none
    
    print(f"\n   Delta from Baseline:")
    print(f"   - MID_Z:  {delta_mid:+.1%}")
    print(f"   - LATE_Z: {delta_late:+.1%}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if svr_x > 10:
        print("🏆 3D PHASE ABSORPTION CONFIRMED!")
        print(f"   SVR_X = {svr_x:.1f} > 10")
        print("   Phase faults (Z) are absorbed in-manifold (MID) but visible after (LATE).")
        print("   The 'phase-blindness' critique is officially Ohio.")
    elif svr_x > 5:
        print("⚠️ PARTIAL PHASE ABSORPTION")
        print(f"   SVR_X = {svr_x:.1f}")
    elif svr_x > 2:
        print("📈 SOME PHASE DIFFERENTIATION")
        print(f"   SVR_X = {svr_x:.1f}")
    else:
        print("📊 ANALYSIS COMPLETE")
        print(f"   SVR_X = {svr_x:.1f}")
        
        if syndrome_late_z > 0.80:
            print("\n✅ LATE_Z detection at {:.1%} - witness IS sensitive to phase!".format(syndrome_late_z))
        if syndrome_mid_z < 0.15:
            print("✅ MID_Z absorbed at {:.1%} - manifold IS protecting!".format(syndrome_mid_z))
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_4_phase_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "phase_stabilizer",
            "version": "6.4",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "metrics": {
                "svr_x": svr_x if svr_x != float('inf') else "inf",
                "syndrome_none": syndrome_none,
                "syndrome_mid_z": syndrome_mid_z,
                "syndrome_late_z": syndrome_late_z,
                "delta_mid": delta_mid,
                "delta_late": delta_late
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results, svr_x


if __name__ == "__main__":
    run_phase_stabilizer_audit()
