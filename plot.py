import json
import matplotlib.pyplot as plt
import numpy as np
import sys
import glob

# --- CONFIGURATION ---
# Auto-detect the most recent JSON file if not specified
json_files = glob.glob("gambit_raw_*.json")
if not json_files:
    print("❌ No gambit_raw_*.json files found!")
    sys.exit(1)
target_file = sorted(json_files)[-1] # Pick the latest one
print(f"🔍 Analyzing: {target_file}")

with open(target_file, 'r') as f:
    data = json.load(f)

# Extract Data
results = data['results']
thetas = [r['theta'] for r in results]
z_scores = [r['metrics']['z_score'] for r in results]
dominances = [r['metrics']['dominance'] for r in results]

# State Populations for the "Roll"
# We want to track 00 and 10 specifically to show the flip
counts_00 = []
counts_10 = []
shots = data['shots']

for r in results:
    c = r['counts']
    counts_00.append(c.get('00', 0) / shots)
    counts_10.append(c.get('10', 0) / shots)

# --- PLOTTING ---
plt.style.use('dark_background') # Sigma Aesthetic
fig = plt.figure(figsize=(15, 10))
plt.suptitle(f"SCHRÖDINGER'S GAMBIT: SIGMA BENCHMARK\nBackend: {data['backend']} | Purity: {results[0]['metrics']['purity']:.4f}", 
             fontsize=16, color='#00ff41', fontweight='bold')

# PANEL 1: THE SOLITON ROLL (State Evolution)
ax1 = plt.subplot(2, 2, 1)
ax1.plot(thetas, counts_00, 'o-', color='#00ff41', linewidth=3, label='State |00> (Pole)')
ax1.plot(thetas, counts_10, 'o--', color='#ff00ff', linewidth=3, label='State |10> (Fisher)')
ax1.set_title("The Soliton Roll (Topological Switch)", fontsize=12, color='white')
ax1.set_xlabel("Braid Angle (Theta)", fontsize=10)
ax1.set_ylabel("Probability", fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.legend()
# Annotate the flip
ax1.annotate('The Flip', xy=(0.196, counts_10[1]), xytext=(0.25, 0.6),
             arrowprops=dict(facecolor='white', shrink=0.05), color='white')

# PANEL 2: THE Z-SCORE TOWER (Anomaly Detection)
ax2 = plt.subplot(2, 2, 2)
colors = ['#00ff41' if z > 14 else '#ff00ff' for z in z_scores]
bars = ax2.bar([str(t) for t in thetas], z_scores, color=colors, alpha=0.8)
ax2.set_title("The 148σ Anomaly (TDA Z-Score)", fontsize=12, color='white')
ax2.set_ylabel("Z-Score (Standard Deviations)", fontsize=10)
ax2.set_xlabel("Theta (rad)", fontsize=10)
# Add labels on bars
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}σ', ha='center', va='bottom', color='white', fontweight='bold')
ax2.axhline(y=14, color='red', linestyle='--', label='Ultra-Trivial Threshold (14σ)')
ax2.legend()

# PANEL 3: THE FINGERPRINTS (Histograms)
ax3 = plt.subplot(2, 1, 2)
# Prepare grouped bar chart data
x = np.arange(len(thetas))
width = 0.2
states = ['00', '01', '10', '11']
# Normalize counts for bar chart
state_probs = {s: [] for s in states}
for r in results:
    for s in states:
        state_probs[s].append(r['counts'].get(s, 0) / shots)

rects1 = ax3.bar(x - 1.5*width, state_probs['00'], width, label='|00>', color='#00ff41')
rects2 = ax3.bar(x - 0.5*width, state_probs['01'], width, label='|01>', color='#333333')
rects3 = ax3.bar(x + 0.5*width, state_probs['10'], width, label='|10>', color='#ff00ff')
rects4 = ax3.bar(x + 1.5*width, state_probs['11'], width, label='|11>', color='#555555')

ax3.set_title("Quantum Fingerprints (State Tomography)", fontsize=12, color='white')
ax3.set_xticks(x)
ax3.set_xticklabels([f"θ = {t} rad" for t in thetas])
ax3.legend()

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
output_filename = f"sigma_benchmark_{data['timestamp']}.png"
plt.savefig(output_filename, dpi=300, facecolor='black')
print(f"🚀 Visualizations saved to: {output_filename}")
plt.show()