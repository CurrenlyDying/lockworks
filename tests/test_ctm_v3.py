"""
CTM v3.0 Full Stack Test
========================

Complete verification of the v3.0 Cylindrical Topological Memory.

Tests:
    1. Single WRITE(1) - Verify Data Bit = 1 at FISHER pole
    2. Single WRITE(0) - Verify Data Bit = 0 at ROBUST pole  
    3. LINK correlation - Verify Bell state >60%

Bit Mapping (CRITICAL):
    Phase Bit = q_2k (even indices) - NEVER measured
    Data Bit = q_2k+1 (odd indices) - The Needle readout
    
OSU Sequence:
    OPEN PORTAL → BRAID → GEAR → SEAL → READOUT
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder, create_memory
from src.needle import NeedleDriver
from src.gearbox import Gearbox


def test_single_write_1():
    """
    Test WRITE(1): θ=0.196 should produce |10⟩ → Data Bit = 1
    """
    print("\n" + "=" * 60)
    print("TEST 1: Single WRITE(1)")
    print("=" * 60)
    
    mem = Cylinder(1)
    mem.disks[0].theta = 0.196  # FISHER pole
    
    print(f"   Disk 0: θ=0.196 (FISHER)")
    print(f"   Expected: |10⟩ → Data=1")
    
    needle = NeedleDriver()
    result = needle.read(mem, [0])
    
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_0 = counts.get("0", 0) / total
    p_1 = counts.get("1", 0) / total
    
    print(f"\n   Results:")
    print(f"   Data=0: {p_0:.1%}")
    print(f"   Data=1: {p_1:.1%}")
    
    success = p_1 > 0.80  # Expect 80%+ for Data=1
    
    return {
        "test": "WRITE(1)",
        "expected": 1,
        "p_0": p_0,
        "p_1": p_1,
        "success": success,
        "message": "✅ FISHER pole correctly produces Data=1" if success else "❌ FISHER pole NOT producing Data=1 - bit mapping issue"
    }


def test_single_write_0():
    """
    Test WRITE(0): θ=0.0 should produce |00⟩ → Data Bit = 0
    """
    print("\n" + "=" * 60)
    print("TEST 2: Single WRITE(0)")
    print("=" * 60)
    
    mem = Cylinder(1)
    mem.disks[0].theta = 0.0  # ROBUST pole
    
    print(f"   Disk 0: θ=0.0 (ROBUST)")
    print(f"   Expected: |00⟩ → Data=0")
    
    needle = NeedleDriver()
    result = needle.read(mem, [0])
    
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_0 = counts.get("0", 0) / total
    p_1 = counts.get("1", 0) / total
    
    print(f"\n   Results:")
    print(f"   Data=0: {p_0:.1%}")
    print(f"   Data=1: {p_1:.1%}")
    
    success = p_0 > 0.85  # Expect 85%+ for Data=0
    
    return {
        "test": "WRITE(0)",
        "expected": 0,
        "p_0": p_0,
        "p_1": p_1,
        "success": success,
        "message": "✅ ROBUST pole correctly produces Data=0" if success else "❌ ROBUST pole NOT producing Data=0"
    }


def test_link_correlation():
    """
    Test LINK: A=1, B=0, LINK(A,B) → Bell correlation
    """
    print("\n" + "=" * 60)
    print("TEST 3: LINK Correlation (Bell State)")
    print("=" * 60)
    
    mem = Cylinder(2)
    mem.disks[0].theta = 0.196  # A = FISHER (1)
    mem.disks[1].theta = 0.0    # B = ROBUST (0)
    mem.link(0, 1)
    
    print(f"   Disk 0: θ=0.196 (FISHER/1)")
    print(f"   Disk 1: θ=0.0 (ROBUST/0)")
    print(f"   LINK(0, 1) with Phase Bias")
    print(f"   Expected: |11⟩ correlation")
    
    needle = NeedleDriver()
    result = needle.read(mem, [0, 1])
    
    counts = result.raw_counts
    total = sum(counts.values())
    
    p_00 = counts.get("00", 0) / total
    p_01 = counts.get("01", 0) / total
    p_10 = counts.get("10", 0) / total
    p_11 = counts.get("11", 0) / total
    
    bell_prob = p_00 + p_11
    
    print(f"\n   Results:")
    print(f"   |00⟩: {p_00:.1%}")
    print(f"   |01⟩: {p_01:.1%} (leakage)")
    print(f"   |10⟩: {p_10:.1%}")
    print(f"   |11⟩: {p_11:.1%}")
    print(f"   Bell: {bell_prob:.1%}")
    
    success = bell_prob > 0.60
    
    return {
        "test": "LINK",
        "p_00": p_00,
        "p_01": p_01,
        "p_10": p_10,
        "p_11": p_11,
        "bell_probability": bell_prob,
        "success": success,
        "counts": counts,
        "message": "✅ Bell correlation >60%" if success else f"❌ Bell correlation {bell_prob:.1%} < 60%"
    }


def run_v3_tests():
    print("=" * 70)
    print("    CTM v3.0 FULL STACK VERIFICATION")
    print("    Phase Bias Gearing + Correct Bit Mapping")
    print("=" * 70)
    
    print(f"\n⚙️ Gearbox v3.0 Config:")
    print(f"   PHASE_BIAS: {Gearbox.PHASE_BIAS} rad")
    
    results = []
    
    # Test 1: WRITE(1)
    results.append(test_single_write_1())
    
    # Test 2: WRITE(0)
    results.append(test_single_write_0())
    
    # Test 3: LINK
    results.append(test_link_correlation())
    
    # Summary
    print("\n" + "=" * 70)
    print("    SUMMARY")
    print("=" * 70)
    
    for r in results:
        print(f"\n{r['message']}")
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print("\n" + "-" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 CTM v3.0 FULLY VERIFIED!")
    elif passed >= 2:
        print("\n⚠️ CTM v3.0 PARTIALLY VERIFIED")
    else:
        print("\n❌ CTM v3.0 NEEDS INVESTIGATION")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_v3_0_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "version": "3.0",
            "phase_bias": Gearbox.PHASE_BIAS,
            "tests": results,
            "summary": {
                "passed": passed,
                "total": total,
                "verdict": "VERIFIED" if passed == total else "PARTIAL" if passed >= 2 else "FAILED"
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    run_v3_tests()
