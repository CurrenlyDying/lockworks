"""
LockWorks v6.5: Phase-Locked Loop Test
========================================

Tests if the Braid can heal phase errors introduced before hardening.

Hypothesis:
    MID_Z (pre-braid): Should be HEALED by the braid → Low syndrome
    LATE_Z (post-braid): Should remain VISIBLE → High syndrome

Target: SVR_X > 5 (ideally >10)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness_v6_5 import WitnessV65
from src.needle import NeedleDriver


def calculate_x_syndrome(counts: dict) -> dict:
    """Calculate X-basis parity syndrome."""
    total = sum(counts.values())
    
    syndrome_1 = 0
    syndrome_0 = 0
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])
        b = int(bits[1])
        a = int(bits[2])
        
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


def run_pll_test():
    print("=" * 70)
    print("    LOCKWORKS v6.5: PHASE-LOCKED LOOP (PLL)")
    print("    Testing Self-Healing Property")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV65(complexity=6)
    
    val_a, val_b = 0, 0  # ROBUST poles
    
    results = []
    tests = [
        ("NONE", "Baseline (No Fault)"),
        ("MID_Z", "MID-Z (Pre-Braid, Should Be HEALED)"),
        ("LATE_Z", "LATE-Z (Post-Braid, Should Be VISIBLE)"),
    ]
    
    for mode, desc in tests:
        print(f"\n📍 {desc}")
        qc = witness.build_pll_circuit(val_a, val_b, fault_mode=mode)
        res = needle.read_circuit(qc)
        analysis = calculate_x_syndrome(res.raw_counts)
        results.append({"mode": mode, "desc": desc, **analysis, "counts": res.raw_counts})
        print(f"   Top State: |{analysis['top_state']}⟩")
        print(f"   Syndrome=1: {analysis['syndrome_1']:.1%}")
        print(f"   Syndrome=0: {analysis['syndrome_0']:.1%}")
    
    # Calculate SVR_X
    syndrome_none = results[0]['syndrome_1']
    syndrome_mid_z = results[1]['syndrome_1']
    syndrome_late_z = results[2]['syndrome_1']
    
    if syndrome_mid_z > 0:
        svr_x = syndrome_late_z / syndrome_mid_z
    else:
        svr_x = float('inf')
    
    print("\n" + "=" * 70)
    print("    PLL ANALYSIS")
    print("=" * 70)
    
    print(f"\n   Syndrome (NONE):   {syndrome_none:.1%}")
    print(f"   Syndrome (MID_Z):  {syndrome_mid_z:.1%}")
    print(f"   Syndrome (LATE_Z): {syndrome_late_z:.1%}")
    
    print(f"\n   SVR_X (LATE_Z / MID_Z) = {svr_x:.1f}")
    
    # Delta from baseline
    delta_mid = syndrome_mid_z - syndrome_none
    delta_late = syndrome_late_z - syndrome_none
    
    print(f"\n   Delta from Baseline:")
    print(f"   - MID_Z:  {delta_mid:+.1%} (should be LOW if healed)")
    print(f"   - LATE_Z: {delta_late:+.1%} (should be HIGH if visible)")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if svr_x > 10:
        print("🏆 SELF-HEALING CONFIRMED!")
        print(f"   SVR_X = {svr_x:.1f} > 10")
        print("   The Braid heals pre-existing phase errors!")
        print("   LockWorks is now a CORRECTING system, not just PREVENTING.")
    elif svr_x > 5:
        print("✅ PARTIAL SELF-HEALING")
        print(f"   SVR_X = {svr_x:.1f} > 5")
        print("   The Braid shows healing capability.")
    elif svr_x > 2:
        print("📈 SOME HEALING OBSERVED")
        print(f"   SVR_X = {svr_x:.1f}")
    else:
        print("📊 PLL ANALYSIS COMPLETE")
        print(f"   SVR_X = {svr_x:.1f}")
        
        if syndrome_mid_z < 0.15:
            print(f"\n✅ MID_Z syndrome at {syndrome_mid_z:.1%} - braid IS healing!")
        elif syndrome_mid_z < syndrome_late_z:
            print(f"\n📈 MID_Z < LATE_Z: Some healing observed.")
    
    # Absorption metrics
    if syndrome_late_z > 0.80:
        print(f"\n✅ LATE_Z detection at {syndrome_late_z:.1%} - witness IS sensitive!")
    
    healing_ratio = 1 - (syndrome_mid_z / syndrome_late_z) if syndrome_late_z > 0 else 0
    print(f"\n   Healing Ratio: {healing_ratio:.1%}")
    print(f"   (100% = perfect healing, 0% = no healing)")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_5_pll_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "pll",
            "version": "6.5",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "metrics": {
                "svr_x": svr_x if svr_x != float('inf') else "inf",
                "syndrome_none": syndrome_none,
                "syndrome_mid_z": syndrome_mid_z,
                "syndrome_late_z": syndrome_late_z,
                "delta_mid": delta_mid,
                "delta_late": delta_late,
                "healing_ratio": healing_ratio
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results, svr_x


if __name__ == "__main__":
    run_pll_test()
