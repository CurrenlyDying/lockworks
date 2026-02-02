"""
CTM v1.3 Zeta Regularization Test
==================================

Tests the Casimir offset symmetry breaking.

Physics:
    EPSILON = π × |−1/12| × 0.1 ≈ 0.026 rad
    Applied as Rz(+ε) before CX and Rz(-ε) after CX.

Hypothesis:
    The regularization slip breaks the "infinite stability" of the
    ground state, allowing the CX to propagate the flip.

Success Criteria:
    - |11⟩ probability: > 20% (was 1.5% in v1.2)
    - Bell fidelity: > 65% (was ~58%)
    - |01⟩ leakage: < 30% (was ~40%)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder, create_memory
from src.needle import NeedleDriver
from src.gearbox import Gearbox


def test_zeta_regularization():
    """
    Test v1.3 Zeta Regularization.
    
    Setup:
        - Disk A: θ=0.196 (Excited/FISHER)
        - Disk B: θ=0.0 (Ground/ROBUST)
        - LINK(A, B) with Casimir slip
    
    Expected: |11⟩ manifests as the regularization breaks ground stability
    """
    print("=" * 70)
    print("    CTM v1.3 ZETA REGULARIZATION TEST")
    print("    Casimir Offset Symmetry Breaking")
    print("=" * 70)
    
    print(f"\n⚡ Regularization Parameters:")
    print(f"   ZETA_CONSTANT: {Gearbox.ZETA_CONSTANT:.6f} (-1/12)")
    print(f"   EPSILON: {Gearbox.EPSILON:.6f} rad ({Gearbox.EPSILON * 180 / 3.14159:.2f}°)")
    
    # Build memory
    mem = Cylinder(2)
    mem.disks[0].theta = 0.196  # FISHER pole (Excited)
    mem.disks[1].theta = 0.0    # ROBUST pole (Ground)
    mem.link(0, 1)
    
    print("\n📦 Configuration:")
    print(f"   Disk 0: θ=0.196 (FISHER/Excited)")
    print(f"   Disk 1: θ=0.0 (ROBUST/Ground)")
    print(f"   LINK(0, 1) with Zeta Regularization")
    
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
    
    print(f"\n📈 Comparison History:")
    print(f"   v1.1 |11⟩: ~1.5%  → v1.3: {p_11:.1%}")
    print(f"   v1.1 Bell: ~57%   → v1.3: {bell_prob:.1%}")
    print(f"   v1.1 |01⟩: ~40%   → v1.3: {leakage:.1%}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    success = p_11 > 0.20 and bell_prob > 0.65 and leakage < 0.30
    partial = p_11 > 0.10 or bell_prob > 0.60
    
    if success:
        print("✅ v1.3 ZETA REGULARIZATION VERIFIED!")
        print("   Casimir offset successfully breaks ground state stability.")
    elif partial:
        print("⚠️ PARTIAL IMPROVEMENT")
        print(f"   |11⟩ ({p_11:.1%}) or Bell ({bell_prob:.1%}) improved but not to target")
    else:
        print("❌ v1.3 DID NOT IMPROVE")
        print("   Need to investigate further.")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_v1_3_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": needle.backend.name if needle.backend else "unknown",
            "version": "1.3",
            "regularization": {
                "zeta_constant": Gearbox.ZETA_CONSTANT,
                "epsilon_rad": Gearbox.EPSILON,
                "epsilon_deg": Gearbox.EPSILON * 180 / 3.14159
            },
            "config": {
                "disk_0_theta": 0.196,
                "disk_1_theta": 0.0,
                "regularized_link": True
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
    test_zeta_regularization()
