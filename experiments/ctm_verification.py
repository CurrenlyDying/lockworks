"""
CTM QPU Verification Experiments
=================================

Testing the Cylindrical Topological Memory on IBM Quantum hardware.

EXPERIMENTS:
1. Single Disk Read/Write - Basic storage verification
2. Multi-Disk Isolation - Independent disks don't interfere
3. Link (Gearing) Test - CX correctly correlates disks
4. Write-Link-Read - Full storage scenario from spec

Each experiment has:
    - HYPOTHESIS: What we expect to observe
    - SUCCESS CRITERIA: Probability threshold for success
    - NULL RESULT: What failure means
"""

import sys
import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder, create_memory
from src.needle import NeedleDriver, NeedleResult


# =============================================================================
# EXPERIMENT DEFINITIONS
# =============================================================================

@dataclass
class Hypothesis:
    name: str
    description: str
    expected_outcome: str
    success_threshold: float
    null_interpretation: str


EXPERIMENTS = {
    "single_write_0": Hypothesis(
        name="Write 0, Read 0",
        description="Write position 0 to disk, read back 0",
        expected_outcome="Disk reads as 0 (θ=0.0, |00⟩ dominant)",
        success_threshold=0.85,
        null_interpretation="Disk failed to lock to ROBUST pole - topology broken"
    ),
    
    "single_write_1": Hypothesis(
        name="Write 1, Read 1",
        description="Write position 1 to disk, read back 1",
        expected_outcome="Disk reads as 1 (θ=0.196, |10⟩ dominant)",
        success_threshold=0.80,
        null_interpretation="Disk failed to lock to FISHER pole - topology broken"
    ),
    
    "multi_isolation": Hypothesis(
        name="Multi-Disk Isolation",
        description="4 disks with pattern [0,1,0,1], each reads independently",
        expected_outcome="Pattern [0,1,0,1] preserved with >75% per disk",
        success_threshold=0.75,
        null_interpretation="Cross-talk between disks - isolation failed"
    ),
    
    "link_test": Hypothesis(
        name="Link (Gearing) Test",
        description="Disk A=H, Disk B=0, LINK(A,B) → Bell state",
        expected_outcome="|00⟩ + |11⟩ correlation >60%",
        success_threshold=0.60,
        null_interpretation="CX gate didn't correlate disks - gearing failed"
    ),
    
    "full_scenario": Hypothesis(
        name="Write-Link-Read Scenario",
        description="A=0, B=1, LINK(A,B), read both - should be 0,1",
        expected_outcome="A=0, B=1 preserved through LINK",
        success_threshold=0.70,
        null_interpretation="LINK corrupted disk states"
    ),
}


# =============================================================================
# EXPERIMENT BUILDERS
# =============================================================================

def build_single_0() -> Tuple[Cylinder, List[int]]:
    """Single disk write 0, read back."""
    mem = create_memory(1)
    mem.rotate(0, 0)  # Write 0
    return mem, [0]


def build_single_1() -> Tuple[Cylinder, List[int]]:
    """Single disk write 1, read back."""
    mem = create_memory(1)
    mem.rotate(0, 1)  # Write 1
    return mem, [0]


def build_multi_isolation() -> Tuple[Cylinder, List[int]]:
    """4 disks with pattern [0,1,0,1]."""
    mem = create_memory(4)
    mem.rotate(0, 0)
    mem.rotate(1, 1)
    mem.rotate(2, 0)
    mem.rotate(3, 1)
    return mem, [0, 1, 2, 3]


def build_link_test() -> Tuple[Cylinder, List[int]]:
    """Bell state: A=H, B=0, LINK(A,B)."""
    mem = Cylinder(2)
    # Disk 0: Set to superposition (we'll use θ=0.1 edge)
    mem.disks[0].theta = 0.1  # Edge/superposition
    mem.disks[1].theta = 0.0  # Ground
    mem.link(0, 1)
    return mem, [0, 1]


def build_full_scenario() -> Tuple[Cylinder, List[int]]:
    """Full spec scenario: A=0, B=1, LINK, read both."""
    mem = create_memory(2)
    mem.rotate(0, 0)  # A = 0
    mem.rotate(1, 1)  # B = 1
    mem.link(0, 1)
    return mem, [0, 1]


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_single(result: NeedleResult, expected: int, hyp: Hypothesis) -> Dict:
    """Analyze single disk read."""
    value = result.values[0]
    fidelity = result.fidelity
    
    success = (value == expected) and (fidelity >= hyp.success_threshold)
    
    return {
        "outcome": "SUCCESS" if success else "NULL",
        "expected": expected,
        "observed": value,
        "fidelity": fidelity,
        "threshold": hyp.success_threshold,
        "interpretation": hyp.expected_outcome if success else hyp.null_interpretation,
    }


def analyze_multi(result: NeedleResult, pattern: List[int], hyp: Hypothesis) -> Dict:
    """Analyze multi-disk isolation."""
    values = result.values
    
    matches = sum(1 for v, e in zip(values, pattern) if v == e)
    accuracy = matches / len(pattern)
    
    success = accuracy >= hyp.success_threshold
    
    return {
        "outcome": "SUCCESS" if success else "NULL",
        "expected_pattern": pattern,
        "observed_pattern": values,
        "accuracy": accuracy,
        "threshold": hyp.success_threshold,
        "interpretation": hyp.expected_outcome if success else hyp.null_interpretation,
    }


def analyze_link(result: NeedleResult, hyp: Hypothesis) -> Dict:
    """Analyze Bell state correlation."""
    counts = result.raw_counts
    total = sum(counts.values())
    
    # Bell states: 00 and 11
    bell_prob = (counts.get("00", 0) + counts.get("11", 0)) / total
    
    success = bell_prob >= hyp.success_threshold
    
    return {
        "outcome": "SUCCESS" if success else "NULL",
        "bell_probability": bell_prob,
        "counts": counts,
        "threshold": hyp.success_threshold,
        "interpretation": hyp.expected_outcome if success else hyp.null_interpretation,
    }


def analyze_scenario(result: NeedleResult, hyp: Hypothesis) -> Dict:
    """Analyze full scenario."""
    values = result.values
    expected = [0, 1]
    
    matches = sum(1 for v, e in zip(values, expected) if v == e)
    accuracy = matches / 2
    
    success = accuracy >= hyp.success_threshold
    
    return {
        "outcome": "SUCCESS" if success else "NULL",
        "expected": expected,
        "observed": values,
        "accuracy": accuracy,
        "fidelity": result.fidelity,
        "interpretation": hyp.expected_outcome if success else hyp.null_interpretation,
    }


# =============================================================================
# MAIN
# =============================================================================

def run_ctm_experiments():
    print("=" * 70)
    print("    CTM QPU VERIFICATION")
    print("    Cylindrical Topological Memory on IBM Quantum")
    print("=" * 70)
    
    # Print hypotheses
    print("\n📋 EXPERIMENT HYPOTHESES:")
    print("-" * 70)
    for key, hyp in EXPERIMENTS.items():
        print(f"\n  {hyp.name}:")
        print(f"    Expected: {hyp.expected_outcome}")
        print(f"    Success if: ≥{hyp.success_threshold:.0%}")
        print(f"    Null means: {hyp.null_interpretation}")
    
    # Connect needle
    print("\n" + "=" * 70)
    print("🔌 CONNECTING NEEDLE TO IBM QUANTUM...")
    print("=" * 70)
    
    needle = NeedleDriver()
    needle.connect()
    
    results = {}
    
    # Experiment 1: Single Write 0
    print("\n📍 Experiment 1: Write 0, Read 0")
    mem, reads = build_single_0()
    r = needle.read(mem, reads)
    results["single_write_0"] = analyze_single(r, 0, EXPERIMENTS["single_write_0"])
    print(f"   Result: {results['single_write_0']['outcome']}")
    
    # Experiment 2: Single Write 1
    print("\n📍 Experiment 2: Write 1, Read 1")
    mem, reads = build_single_1()
    r = needle.read(mem, reads)
    results["single_write_1"] = analyze_single(r, 1, EXPERIMENTS["single_write_1"])
    print(f"   Result: {results['single_write_1']['outcome']}")
    
    # Experiment 3: Multi-Disk Isolation
    print("\n📍 Experiment 3: Multi-Disk Isolation [0,1,0,1]")
    mem, reads = build_multi_isolation()
    r = needle.read(mem, reads)
    results["multi_isolation"] = analyze_multi(r, [0, 1, 0, 1], EXPERIMENTS["multi_isolation"])
    print(f"   Result: {results['multi_isolation']['outcome']}")
    
    # Experiment 4: Link Test
    print("\n📍 Experiment 4: Link (Gearing) Test")
    mem, reads = build_link_test()
    r = needle.read(mem, reads)
    results["link_test"] = analyze_link(r, EXPERIMENTS["link_test"])
    print(f"   Result: {results['link_test']['outcome']}")
    
    # Experiment 5: Full Scenario
    print("\n📍 Experiment 5: Write-Link-Read Scenario")
    mem, reads = build_full_scenario()
    r = needle.read(mem, reads)
    results["full_scenario"] = analyze_scenario(r, EXPERIMENTS["full_scenario"])
    print(f"   Result: {results['full_scenario']['outcome']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("    RESULTS SUMMARY")
    print("=" * 70)
    
    success = sum(1 for r in results.values() if r["outcome"] == "SUCCESS")
    total = len(results)
    
    for key, res in results.items():
        hyp = EXPERIMENTS[key]
        emoji = "✅" if res["outcome"] == "SUCCESS" else "❌"
        print(f"\n{emoji} {hyp.name}")
        print(f"   → {res['interpretation']}")
        for k, v in res.items():
            if k not in ["outcome", "interpretation"]:
                print(f"   {k}: {v}")
    
    print("\n" + "-" * 70)
    print(f"TOTAL: {success}/{total} experiments passed")
    
    if success == total:
        print("✅ CTM FULLY VERIFIED - All storage operations work correctly!")
    elif success >= total // 2:
        print("⚠️ CTM PARTIALLY VERIFIED - Some operations need investigation")
    else:
        print("❌ CTM VERIFICATION FAILED - Core issues detected")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ctm_verification_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": needle.backend.name if needle.backend else "unknown",
            "experiments": results,
            "summary": {
                "success": success,
                "total": total,
                "verdict": "VERIFIED" if success == total else "PARTIAL" if success >= total//2 else "FAILED"
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    run_ctm_experiments()
