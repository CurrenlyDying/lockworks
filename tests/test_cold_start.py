"""
CTM v3.1 Cold-Start Gearing Test
=================================

Tests the Cold-Start sequence: LINK before BRAID (not after).

OSU Pattern v3.1:
    1. OPEN: ALLOC (H-gates on all)
    2. GEAR: LINK (CX on stationary disks) ← NEW POSITION
    3. SPIN: ROTATE (Apply braids to both)
    4. SEAL: SEAL (H-gates to close portal)
    5. READ: READ_NEEDLE

Target:
    - |11⟩ Probability > 40%
    - Bell Fidelity > 65%
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder
from src.needle import NeedleDriver


def test_cold_start():
    """
    Test v3.1 Cold-Start Gearing.
    
    Sequence:
        1. Alloc 2 disks
        2. Link(0, 1) - CX during Open Portal (Cold-Start!)
        3. Rotate(0, 1) -> θ=0.196 (FISHER)
        4. Rotate(1, 0) -> θ=0.0 (ROBUST)
        5. Measure
    
    Expected: |11⟩ correlation due to Cold-Start entanglement
    """
    print("=" * 70)
    print("    CTM v3.1 COLD-START GEARING TEST")
    print("    LINK → BRAID (not BRAID → LINK)")
    print("=" * 70)
    
    # Build memory with Cold-Start
    mem = Cylinder(2)
    
    # LINK FIRST (before setting theta)
    mem.link(0, 1)
    
    # Then set the rotation angles (these are used during braid)
    mem.disks[0].theta = 0.196  # Control = FISHER (1)
    mem.disks[1].theta = 0.0    # Target = ROBUST (0)
    
    print("\n⚙️ Cold-Start Sequence:")
    print("   1. OPEN: H gates on all")
    print("   2. GEAR: CX(0,1) on stationary disks")
    print("   3. SPIN: Braid with θ₀=0.196, θ₁=0.0")
    print("   4. SEAL: H gates")
    print("   5. READ: Measure data bits")
    
    print("\n📦 Configuration:")
    print(f"   Disk 0: θ=0.196 (FISHER/1) - Control")
    print(f"   Disk 1: θ=0.0 (ROBUST/0) - Target")
    print(f"   LINK(0,1) applied BEFORE braid (Cold-Start!)")
    
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
    print(f"   |01⟩ Leakage: {p_01:.1%}")
    
    print(f"\n📈 Comparison:")
    print(f"   v3.0 |11⟩: 0.6%   → v3.1: {p_11:.1%}")
    print(f"   v3.0 Bell: 6.2%   → v3.1: {bell_prob:.1%}")
    print(f"   v3.0 |01⟩: 92.2%  → v3.1: {p_01:.1%}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    success = p_11 > 0.40 and bell_prob > 0.65
    partial = p_11 > 0.20 or bell_prob > 0.50
    
    if success:
        print("🎉 v3.1 COLD-START GEARING VERIFIED!")
        print("   Linking before braid WORKS!")
        print("   This is a MAJOR breakthrough! 🚀")
    elif partial:
        print("⚠️ PARTIAL IMPROVEMENT")
        print(f"   |11⟩ ({p_11:.1%}) or Bell ({bell_prob:.1%}) improved significantly")
    elif p_11 > 0.05:
        print("📈 SOME IMPROVEMENT")
        print(f"   |11⟩ improved from 0.6% to {p_11:.1%}")
    else:
        print("❌ v3.1 DID NOT IMPROVE")
        print("   Cold-Start may need additional tuning.")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_v3_1_cold_start_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": needle.backend.name if needle.backend else "unknown",
            "version": "3.1",
            "method": "cold_start",
            "sequence": "OPEN → GEAR → BRAID → SEAL",
            "config": {
                "disk_0_theta": 0.196,
                "disk_1_theta": 0.0,
                "link_before_braid": True
            },
            "results": {
                "p_00": p_00,
                "p_01": p_01,
                "p_10": p_10,
                "p_11": p_11,
                "bell_probability": bell_prob
            },
            "counts": counts,
            "success": success
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return success


if __name__ == "__main__":
    test_cold_start()
