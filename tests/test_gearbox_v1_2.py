"""
CTM v1.2 Gearbox Test
=====================

Tests the Internal Gearing strategy: LINK before close-portal.

Hypothesis:
    Moving CX before the final H gates allows the target disk
    to be flipped while still "spinning" (not locked to ground).

Success Criteria:
    - |11⟩ probability: > 20% (was 1.5% in v1.1)
    - Bell fidelity: > 65% (was ~57%)
    - |01⟩ leakage: < 30% (was ~40%)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder, create_memory
from src.needle import NeedleDriver


def test_internal_gearing():
    """
    Test v1.2 internal gearing.
    
    Setup:
        - Disk A: θ=0.1 (superposition/edge)
        - Disk B: θ=0.0 (ground)
        - LINK(A, B) before seal
    
    Expected: Bell state |00⟩ + |11⟩ with >65% fidelity
    """
    print("=" * 70)
    print("    CTM v1.2 INTERNAL GEARING TEST")
    print("    LINK before close-portal")
    print("=" * 70)
    
    # Build memory
    mem = Cylinder(2)
    mem.disks[0].theta = 0.1  # Superposition
    mem.disks[1].theta = 0.0  # Ground
    mem.link(0, 1)
    
    print("\n📦 Configuration:")
    print(f"   Disk 0: θ={mem.disks[0].theta} (superposition)")
    print(f"   Disk 1: θ={mem.disks[1].theta} (ground)")
    print(f"   LINK(0, 1) applied BEFORE close-portal (v1.2)")
    
    # Run on QPU
    print("\n🚀 Submitting to IBM Quantum...")
    needle = NeedleDriver()
    result = needle.read(mem, [0, 1])
    
    # Analyze
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_00 = counts.get("00", 0) / total
    p_01 = counts.get("01", 0) / total
    p_10 = counts.get("10", 0) / total
    p_11 = counts.get("11", 0) / total
    
    bell_prob = p_00 + p_11
    leakage = p_01
    
    print("\n" + "=" * 70)
    print("    RESULTS")
    print("=" * 70)
    
    print(f"\n📊 State Distribution:")
    print(f"   |00⟩: {p_00:.1%}")
    print(f"   |01⟩: {p_01:.1%} (leakage)")
    print(f"   |10⟩: {p_10:.1%}")
    print(f"   |11⟩: {p_11:.1%}")
    
    print(f"\n🎯 Metrics:")
    print(f"   Bell Fidelity: {bell_prob:.1%}")
    print(f"   |11⟩ Probability: {p_11:.1%}")
    print(f"   |01⟩ Leakage: {leakage:.1%}")
    
    print(f"\n📈 Comparison to v1.1:")
    print(f"   v1.1 |11⟩: ~1.5%  → v1.2: {p_11:.1%}")
    print(f"   v1.1 Bell: ~57%   → v1.2: {bell_prob:.1%}")
    print(f"   v1.1 |01⟩: ~40%   → v1.2: {leakage:.1%}")
    
    # Verdict
    print("\n" + "=" * 70)
    success = p_11 > 0.20 and bell_prob > 0.65 and leakage < 0.30
    
    if success:
        print("✅ v1.2 INTERNAL GEARING VERIFIED!")
        print("   LINK before close-portal fixes the leakage issue.")
    elif p_11 > 0.10:
        print("⚠️ PARTIAL IMPROVEMENT")
        print(f"   |11⟩ improved ({p_11:.1%} > 1.5%), but not to target >20%")
    else:
        print("❌ v1.2 DID NOT IMPROVE")
        print("   Need to investigate further.")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_v1_2_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": needle.backend.name if needle.backend else "unknown",
            "version": "1.2",
            "config": {
                "disk_0_theta": 0.1,
                "disk_1_theta": 0.0,
                "link_before_seal": True
            },
            "results": {
                "p_00": p_00,
                "p_01": p_01,
                "p_10": p_10,
                "p_11": p_11,
                "bell_probability": bell_prob,
                "leakage": leakage
            },
            "counts": counts,
            "success": success
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return success


if __name__ == "__main__":
    test_internal_gearing()
