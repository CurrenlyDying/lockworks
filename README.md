# LockWorks + SchrodingerLang

**A Complete Quantum Programming System for NISQ Hardware**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18457967.svg)](https://doi.org/10.5281/zenodo.18457967)
---

## What This Is

LockWorks is not just a circuit optimization library - it's a **complete quantum programming stack** from high-level language down to hardware-aware compilation:

```
SchrodingerLang (.sl)  ← High-level quantum programming language
        ↓
    Compiler           ← Parse, optimize, type-check
        ↓
    ISA Layer          ← Instruction set architecture
        ↓
    LockWorks Core     ← Circuit hardening primitives
        ↓
    Hardware Driver    ← IBM Quantum execution
```

## Quick Example

**Write quantum programs in clean syntax:**

```schrodinger
# bell_test.sl
program BellTest:
    soliton alpha = H;      # Superposition state
    soliton beta = 0;       # Ground state
    entangle(alpha, beta);  # Topological entanglement
    
    a = measure(alpha);
    b = measure(beta);
```

**The compiler automatically:**
- Applies circuit hardening (braid manifold, C=6)
- Aligns to hardware topology
- Inserts error detection witnesses
- Optimizes for the target backend

**Result:** 93%+ fidelity on real quantum hardware.

---

## Key Results

### LockWorks Circuit Hardening

| Metric | Baseline | LockWorks | Improvement |
|--------|----------|-----------|-------------|
| Bell Fidelity | 8.0% | **93.4%** | **+85.4pp** |
| Storage Fidelity | ~80% | **97.6%** | +17.6pp |
| Parity Witness | N/A | **95.1%** | — |
| Fault Absorption (SVR) | 0 | **15.4** | Strong |
| Syndrome Floor | N/A | **4.15%** | Hardware limit |

### Systematic Optimization

**Complexity Sweep (C parameter):**
```
C=0: 0.0%   (no protection)
C=2: 22.7%  (weak)
C=4: 63.9%  (good)
C=6: 93.3%  ← OPTIMAL
C=8: 84.8%  (depth penalty)
```

**Dynamical Decoupling Tests (v7.0-7.1):**
- Echo sequences INCREASED errors (gate costs > drift cancellation)
- Validated v6.4 freeze decision
- Documented negative results clarify mechanism

---

## The Stack

### 1. SchrodingerLang (High-Level Language)

Clean, intuitive syntax for quantum programming:

```schrodinger
# Declare quantum variables
soliton a = 0;         # Ground state
soliton b = H;         # Superposition
soliton c = 1;         # Excited state

# Quantum operations
entangle(a, b);        # CNOT with automatic hardening
phase_shift(c, 0.5);   # Controlled rotation

# Measurement
result = measure(a, b, c);
```

### 2. Compiler & ISA

**compiler.py** - Full compiler with:
- Lexing and parsing
- Type checking
- Optimization passes
- Code generation

**isa.py** - Instruction set defining:
- Logical operations
- Hardware primitives
- Error detection hooks

### 3. LockWorks Core (Circuit Hardening)

**cylinder.py** - Topological memory units:
```python
from src.cylinder import Cylinder

# 2-qubit "disk" = 1 logical qubit with hardening
cylinder = Cylinder(num_disks=2, complexity=6)
cylinder.write_disk(0, value=1)  # 97.6% fidelity
cylinder.write_disk(1, value=0)
```

**gearbox.py** - Entanglement strategies:
- Anchor Sequence (prevents phase kickback)
- Inverted CX (hardware-aligned)
- Cold-Start gearing

**witness.py** - Error detection:
- Parity witnesses (A ⊕ B)
- SVR timing diagnostics
- Post-selection filtering

### 4. Hardware Driver

**needle.py** - IBM Quantum interface:
```python
from src.needle import NeedleDriver

driver = NeedleDriver(backend_name='ibm_fez')
results = driver.execute(circuit, shots=4096)
```

---

## Project Structure

```
lockworks/
├── src/
│   ├── compiler.py         # SchrodingerLang compiler
│   ├── slang.py           # Language parser
│   ├── isa.py             # Instruction set architecture
│   ├── runtime.py         # Execution runtime
│   ├── sequencer.py       # Circuit sequencing
│   ├── cylinder.py        # Topological memory (CTM)
│   ├── gearbox.py         # Entanglement strategies
│   ├── needle.py          # Hardware driver
│   ├── witness.py         # Error detection (v6.0)
│   ├── witness_v6_4.py    # Phase stabilizer (GOLD)
│   └── fault_engine.py    # Controlled fault injection
│
├── examples/
│   ├── bell_test.sl       # Bell state demo
│   └── soliton_roll.sl    # Multi-qubit example
│
├── tests/                 # Complete test suite
│   ├── test_ctm_v3.py     # Core functionality
│   ├── test_v6_4_phase.py # Error detection
│   └── ...14 total tests
│
├── experiments/           # Research experiments
│   ├── complexity_scaling.py
│   ├── parity_witness.py
│   └── ...
│
└── docs/
    ├── LOCKWORKS_COMPLETE_DOCUMENTATION.md
    └── LOCKWORKS_ADR_FINAL.md
```

---

## Installation

```bash
git clone https://github.com/CurrenlyDying/lockworks.git
cd lockworks
pip install -r requirements.txt

# Set your IBM Quantum token
export QISKIT_IBM_TOKEN="your_token_here"
```

---

## Usage Examples

### Python API (LockWorks Core)

```python
from src.cylinder import Cylinder
from src.needle import NeedleDriver

# Initialize system
cylinder = Cylinder(num_disks=2, complexity=6)
driver = NeedleDriver(backend_name='ibm_fez')

# Write values with automatic hardening
cylinder.write_disk(0, value=1)
cylinder.write_disk(1, value=0)

# Create Bell pair (hardware-aligned)
cylinder.link_disks(0, 1)

# Execute on real hardware
circuit = cylinder.generate_circuit()
results = driver.execute(circuit)

print(f"Bell fidelity: {results.bell_fidelity:.1%}")
# Output: Bell fidelity: 93.4%
```

### SchrodingerLang (High-Level)

```python
# Run SchrodingerLang program
from src.slang import compile_and_run

compile_and_run("examples/bell_test.sl")
```

Or use the standalone compiler:

```bash
python schrodinger_lang.py
```

---

## Key Innovations

### 1. Hardware Direction Discovery

Discovered IBM's CX gate is physically `CX(target, control)`:

**Before alignment:** 8% Bell fidelity  
**After alignment:** 93.4% Bell fidelity  
**Impact:** 11.7x improvement from hardware awareness

### 2. SVR Metric (Syndrome Visibility Ratio)

Novel diagnostic for timing-dependent fault behavior:

```
SVR = Syndrome(LATE_fault) / Syndrome(MID_fault)

SVR > 10  → Strong absorption during formation
SVR < 2   → No clear absorption
```

LockWorks SVR = **15.4** (strong fault absorption during braid formation)

### 3. Systematic Negative Results

v7.0-7.1 Echo Chamber experiments proved dynamical decoupling **degraded** performance:
- Gate errors > drift cancellation on ibm_fez
- Validated architecture freeze at v6.4
- Established 4.15% as hardware noise floor

**Philosophy:** Document failures to clarify mechanisms.

### 4. Complete Language Stack

SchrodingerLang provides:
- Domain-specific syntax (.sl files)
- Full compiler pipeline
- Automatic hardware optimization
- Built-in error detection

---

## Design Philosophy

> **"Prevention over Cure"**

LockWorks is an **error prevention** system, not error correction:

- ❌ NOT quantum error correction (no syndrome decoding)
- ❌ NOT device-independent (hardware-specific)
- ✅ **Practical hardening** for near-term devices
- ✅ **Systematic optimization** through empirical testing
- ✅ **Honest engineering** (negative results documented)

---

## Research Methodology

### Witness-Driven Development

1. **v6.0:** Initial parity witness
2. **v6.1:** SVR timing test (fault absorption)
3. **v6.2:** Frame-matched faults (refute basis rotation critique)
4. **v6.3:** X-basis measurement (phase coherence)
5. **v6.4:** H-conjugated parity (phase-fault visibility) ← **GOLD**
6. **v6.5:** PLL test (proves "prevention not cure")
7. **v7.0-7.1:** Echo chamber (rejected - negative result)

Each version responds to potential critiques with targeted experiments.

---

## Hardware Tested

**Primary:** IBM Heron (`ibm_fez`) - 156 qubits  
**Date:** January 2026  
**Shots:** 4096 per experiment  
**Total experiments:** 50+ systematic tests

All results include:
- JSON-formatted data files
- Transpiled circuit metrics
- Hardware calibration snapshots

---

## Documentation

- [**Complete Technical Docs**](LOCKWORKS_COMPLETE_DOCUMENTATION.md) - Full system architecture
- [**Architecture Decision Record**](LOCKWORKS_ADR_FINAL.md) - Why v6.4 is frozen
- [**Development Log**](chat.md) - Evolution timeline

---

## Citing This Work

```bibtex
@software{lockworks2026,
  title = {LockWorks + SchrodingerLang: A Complete Quantum Programming System for NISQ},
  author = {Ziad Rabah},
  year = {2026},
  url = {https://github.com/CurrenlyDying/lockworks}
}
```

---

## Roadmap

**v1.0 (Current):**
- ✅ Core circuit hardening (LockWorks)
- ✅ SchrodingerLang compiler
- ✅ IBM Quantum driver
- ✅ Complete test suite
- ✅ Systematic validation

**v1.1 (Next):**
- [ ] Cross-backend support (ibm_sherbrooke, ibm_torino)
- [ ] Enhanced SchrodingerLang syntax (loops, conditionals)
- [ ] Logical operations (adder, teleportation)
- [ ] Interactive REPL

**v2.0 (Future):**
- [ ] Multi-backend optimization
- [ ] Algorithmic cooling integration
- [ ] Standard library of hardened primitives
- [ ] VS Code extension for .sl files

---

## License

MIT License - See [LICENSE](LICENSE) file

---

## Contact

**Available for collaboration, consulting, or full-time roles.**

- GitHub: CurrenlyDying
- Email: ziad.rabah@gmail.com
- LinkedIn: https://www.linkedin.com/in/ziad-rabah/
- Location: France (open to relocation)

**Skills:** Python, Qiskit, Compiler Design, Quantum Computing, Hardware Optimization

---

**Built with:** Python, Qiskit, IBM Quantum  
**Tested on:** Real quantum hardware (IBM Heron, Feb 2026)  
**Status:** Production-ready v6.4 (frozen), SchrodingerLang alpha
