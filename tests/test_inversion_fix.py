"""
CTM v3.2 Kickback Buffer Test
==============================

Tests the Anchor Sequence: Harden control BEFORE linking.

Sequence:
    1. OPEN: H gates on all
    2. HARDEN: Braid control disk only (locks to pole)
    3. GEAR: CX from hardened control to fluid target
    4. SOFTEN: Braid target disk
    5. SEAL: H gates
    6. READ: Measure data bits

Also tests INVERTED CX direction in case hardware orientation differs.

Target:
    - |11⟩ Probability > 40%
    - Bell Fidelity > 60%
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder
from src.needle import NeedleDriver


def run_anchor_test(inverted: bool = False):
    """Run Anchor sequence test."""
    
    mode = "INVERTED" if inverted else "NORMAL"
    print(f"\n{'=' * 60}")
    print(f"TEST: Anchor Sequence ({mode} CX)")
    print(f"{'=' * 60}")
    
    mem = Cylinder(2)
    
    # Build circuit using Anchor method
    if inverted:
        qc = mem.to_circuit_anchor_inverted(
            control_addr=0, control_value=1,  # FISHER
            target_addr=1, target_value=0,    # ROBUST
            measurements=[0, 1]
        )
    else:
        qc = mem.to_circuit_anchor(
            control_addr=0, control_value=1,  # FISHER
            target_addr=1, target_value=0,    # ROBUST
            measurements=[0, 1]
        )
    
    print(f"\n⚙️ Anchor Sequence:")
    print(f"   1. OPEN: H gates")
    print(f"   2. HARDEN: Braid Disk 0 (θ=0.196)")
    print(f"   3. GEAR: CX({'1→0' if inverted else '0→1'})")
    print(f"   4. SOFTEN: Braid Disk 1 (θ=0.0)")
    print(f"   5. SEAL: H gates")
    
    # Run on QPU
    print("\n🚀 Submitting to IBM Quantum...")
    needle = NeedleDriver()
    result = needle.read_circuit(qc)
    
    # Analyze
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_00 = counts.get("00", 0) / total
    p_01 = counts.get("01", 0) / total
    p_10 = counts.get("10", 0) / total
    p_11 = counts.get("11", 0) / total
    
    bell_prob = p_00 + p_11
    
    print(f"\n📊 Results ({mode}):")
    print(f"   |00⟩: {p_00:.1%}")
    print(f"   |01⟩: {p_01:.1%}")
    print(f"   |10⟩: {p_10:.1%}")
    print(f"   |11⟩: {p_11:.1%}")
    print(f"   Bell: {bell_prob:.1%}")
    
    return {
        "mode": mode,
        "inverted": inverted,
        "p_00": p_00,
        "p_01": p_01,
        "p_10": p_10,
        "p_11": p_11,
        "bell_probability": bell_prob,
        "counts": counts,
        "success": p_11 > 0.20 or bell_prob > 0.50
    }


def test_v3_2():
    print("=" * 70)
    print("    CTM v3.2 KICKBACK BUFFER TEST")
    print("    Anchor Sequence: Harden → Link → Soften")
    print("=" * 70)
    
    results = []
    
    # Test 1: Normal CX direction
    results.append(run_anchor_test(inverted=False))
    
    # Test 2: Inverted CX direction
    results.append(run_anchor_test(inverted=True))
    
    # Summary
    print("\n" + "=" * 70)
    print("    COMPARISON SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Mode':<15} {'|11⟩':>10} {'Bell':>10} {'|01⟩ Leak':>12}")
    print("-" * 50)
    for r in results:
        print(f"{r['mode']:<15} {r['p_11']:>10.1%} {r['bell_probability']:>10.1%} {r['p_01']:>12.1%}")
    
    # Find winner
    best = max(results, key=lambda x: x["bell_probability"])
    
    print(f"\n🏆 Best mode: {best['mode']}")
    print(f"   |11⟩: {best['p_11']:.1%}")
    print(f"   Bell: {best['bell_probability']:.1%}")
    
    if best['bell_probability'] > 0.60:
        print("\n🎉 v3.2 ANCHOR SEQUENCE VERIFIED!")
    elif best['bell_probability'] > 0.40:
        print("\n⚠️ SIGNIFICANT IMPROVEMENT - getting closer!")
    elif best['p_11'] > 0.10:
        print("\n📈 Some improvement in |11⟩ probability")
    else:
        print("\n❌ Need to investigate further")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_v3_2_anchor_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "version": "3.2",
            "method": "anchor_sequence",
            "tests": results,
            "best_mode": best["mode"],
            "best_bell": best["bell_probability"]
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    test_v3_2()
