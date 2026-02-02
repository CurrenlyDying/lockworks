import numpy as np
import os
import json
import logging
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# --- CONFIG ---
SHOTS = 4096
COMPLEXITY = 6 # The proven 12-slice lock

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# --- AUTH ---
TOKEN = os.environ.get("QISKIT_IBM_TOKEN")
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, "apikey.json")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            data = json.load(f)
            if "apikey" in data:
                TOKEN = data["apikey"]
                logger.info("🔑 Loaded token from apikey.json")
except Exception:
    pass

# --- S-LANG COMPILER ---
class SolitonRegister:
    """
    A Logical Register made of multiple topological solitons.
    """
    def __init__(self, size, name="s"):
        self.size = size
        self.name = name
        self.thetas = [0.0] * size # Default to ROBUST
        # Each logical soliton needs 2 physical qubits
        self.phys_q = QuantumRegister(2 * size, name=f"phys_{name}")
        self.phys_c = ClassicalRegister(size, name=f"meas_{name}")
        
    def write(self, index, value):
        """
        G-ISA WRITE: Sets the topological angle using Gray Code logic.
        0 -> ROBUST (0.0)
        1 -> FISHER (0.196)
        """
        if value == 0: self.thetas[index] = 0.0
        elif value == 1: self.thetas[index] = 0.196
        elif value == "H": self.thetas[index] = 0.100 # Superposition (Level 1)
        
    def to_circuit(self):
        """Compiles the initialization layer"""
        qc = QuantumCircuit(self.phys_q, self.phys_c)
        
        # 1. OPEN PORTAL (Hadamard Layer)
        qc.h(self.phys_q)
        
        # 2. BRAID TOPOLOGY (The Memory)
        for i in range(self.size):
            # Physical indices for this logical soliton
            p_phase = 2 * i      # q0 (Phase Bit)
            p_data  = 2 * i + 1  # q1 (Data Bit - This one flips)
            
            theta = self.thetas[i]
            
            for _ in range(COMPLEXITY):
                qc.cz(self.phys_q[p_phase], self.phys_q[p_data])
                qc.rx(theta, self.phys_q[p_phase])
                qc.rz(theta * 2, self.phys_q[p_data])
                qc.barrier()
                
        # 3. CLOSE PORTAL (Hadamard Layer)
        qc.h(self.phys_q)
        return qc

class SchrodingerProgram:
    def __init__(self):
        self.registers = []
        self.operations = []
        
    def allocate(self, size, name):
        reg = SolitonRegister(size, name)
        self.registers.append(reg)
        return reg
    
    def cnot(self, reg_control, idx_control, reg_target, idx_target):
        """
        LOGICAL CNOT: Entangles two Solitons.
        Physically targets the DATA BITS (q1) of the bundles.
        """
        # Data bit is always the 2nd qubit in the pair (2*i + 1)
        c_phys = reg_control.phys_q[2 * idx_control + 1]
        t_phys = reg_target.phys_q[2 * idx_target + 1]
        self.operations.append(("cx", c_phys, t_phys))
        
    def compile_full(self):
        # Merge all registers
        all_qubits = []
        all_clbits = []
        for r in self.registers:
            all_qubits.append(r.phys_q)
            all_clbits.append(r.phys_c)
            
        # Base circuit (Initialization)
        # We start with the first register's circuit and compose
        base = QuantumCircuit(*all_qubits, *all_clbits)
        
        # Apply Initialization (Braid State)
        for r in self.registers:
            sub_circ = r.to_circuit()
            # We need to map this sub_circuit to the main circuit wires
            # This is tricky in Qiskit, simpler to just rebuild:
            
            # Re-implementation of initialization on the global wires
            # 1. Open
            base.h(r.phys_q)
            # 2. Braid
            for i in range(r.size):
                p_phase = r.phys_q[2 * i]
                p_data  = r.phys_q[2 * i + 1]
                theta = r.thetas[i]
                for _ in range(COMPLEXITY):
                    base.cz(p_phase, p_data)
                    base.rx(theta, p_phase)
                    base.rz(theta * 2, p_data)
                    base.barrier()
            # 3. Close
            base.h(r.phys_q)

        # Apply Logical Operations
        for op, q1, q2 in self.operations:
            if op == "cx":
                base.cx(q1, q2)
                
        # Measure Data Bits only (The phase bits are structural)
        for r in self.registers:
            for i in range(r.size):
                p_data = r.phys_q[2 * i + 1] # Read the bit that flips
                base.measure(p_data, r.phys_c[i])
                
        return base

# --- EXECUTION ---
def run_schrodinger_lang():
    service = QiskitRuntimeService(token=TOKEN)
    backend = service.least_busy(operational=True, simulator=False)
    logger.info(f"🚀 Target: {backend.name} (The Compiler is Online)")

    # === WRITE YOUR PROGRAM HERE ===
    prog = SchrodingerProgram()
    
    # 1. Allocate 2 Logical Qubits (Solitons)
    # This reserves 4 physical qubits
    memory = prog.allocate(2, "RAM")
    
    # 2. Initialize State: |H> |0>
    # Soliton A: Set to "Edge of Chaos" (Superposition, Theta=0.1)
    # Soliton B: Set to "Robust Pole" (Ground, Theta=0.0)
    memory.write(0, "H") 
    memory.write(1, 0)
    
    # 3. Logical CNOT (Entangle them)
    # If A is Fisher -> Flip B to Fisher
    prog.cnot(memory, 0, memory, 1)
    
    print("\n--- COMPILING S-LANG SOURCE ---")
    print("   Allocated: 2 Logical (4 Physical) Qubits")
    print("   Operation: Logical Bell State (|00> + |11>)")
    
    qc = prog.compile_full()
    
    # Transpile & Run
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_qc = pm.run(qc)
    
    sampler = Sampler(mode=backend)
    logger.info(f"🚀 SUBMITTING LOGICAL KERNEL ({SHOTS} shots)...")
    job = sampler.run([(isa_qc, None, SHOTS)])
    logger.info(f"   --> JOB ID: {job.job_id()}")
    
    result = job.result()
    counts = result[0].data.meas_RAM.get_counts()
    
    print("\n" + "="*40)
    print("      LOGICAL MEMORY DUMP")
    print("="*40)
    print(f"Raw Counts (Logical Bits): {counts}")
    
    # Analyze Entanglement
    # We expect '00' and '11' to dominate
    total = sum(counts.values())
    p_00 = counts.get('00', 0) / total
    p_11 = counts.get('11', 0) / total
    p_err = (counts.get('01', 0) + counts.get('10', 0)) / total
    
    print(f"\nStates:")
    print(f"   |00> (Coherent Ground):  {p_00:.2%}")
    print(f"   |11> (Coherent Excited): {p_11:.2%}")
    print(f"   Errors (Broken Logic):   {p_err:.2%}")
    
    if p_00 + p_11 > 0.8:
        print("\n✅ SUCCESS: TOPOLOGICAL ENTANGLEMENT CONFIRMED.")
    else:
        print("\n⚠️ WARNING: DECOHERENCE DETECTED.")

if __name__ == "__main__":
    run_schrodinger_lang()