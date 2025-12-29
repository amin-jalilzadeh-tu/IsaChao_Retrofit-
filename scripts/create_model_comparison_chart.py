"""
Create a grouped bar chart comparing MTL architectures and trainers.
Based on Table 3 from the article - composite scores.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Data from Table 3 in the article
data = {
    'Architecture': ['Separate', 'Separate', 'Deep_Balanced', 'Deep_Balanced',
                     'Shared', 'Deep_Balanced', 'Data_Based', 'Shared',
                     'Data_Based', 'Shared'],
    'Trainer': ['MGDA', 'Uncertainty', 'MGDA', 'Weighted_Sum',
                'MGDA', 'Uncertainty', 'Uncertainty', 'Uncertainty',
                'Weighted_Sum', 'Weighted_Sum'],
    'Score': [1.000, 0.973, 0.863, 0.858, 0.835, 0.828, 0.787, 0.767, 0.715, 0.709],
    'Energy_R2': [0.90, 0.91, 0.87, 0.87, 0.86, 0.84, 0.85, 0.85, 0.85, 0.85],
    'Cost_R2': [0.63, 0.61, 0.61, 0.61, 0.60, 0.60, 0.60, 0.59, 0.59, 0.58],
    'Emission_R2': [0.89, 0.88, 0.84, 0.85, 0.83, 0.84, 0.81, 0.85, 0.80, 0.82],
    'Comfort_R2': [0.89, 0.86, 0.82, 0.80, 0.79, 0.76, 0.80, 0.76, 0.80, 0.78]
}

df = pd.DataFrame(data)

# Create pivot table for grouped bar chart
pivot_score = df.pivot_table(index='Architecture', columns='Trainer', values='Score', aggfunc='first')

# Reorder architectures by best performance
arch_order = ['Separate', 'Deep_Balanced', 'Shared', 'Data_Based']
trainer_order = ['MGDA', 'Uncertainty', 'Weighted_Sum']

# Reindex
pivot_score = pivot_score.reindex(arch_order)
pivot_score = pivot_score[trainer_order]

# Colors for trainers
colors = {
    'MGDA': '#2E86AB',           # Blue
    'Uncertainty': '#A23B72',    # Magenta/Pink
    'Weighted_Sum': '#F18F01'    # Orange
}

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(len(arch_order))
width = 0.25

# Plot bars for each trainer
for i, trainer in enumerate(trainer_order):
    values = pivot_score[trainer].values
    # Handle NaN values (some combinations may not exist in top 10)
    values = np.where(np.isnan(values), 0, values)
    bars = ax.bar(x + i*width, values, width, label=trainer, color=colors[trainer],
                  edgecolor='black', linewidth=0.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.annotate(f'{val:.3f}',
                       xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

# Customize
ax.set_xlabel('Architecture', fontsize=12, fontweight='bold')
ax.set_ylabel('Composite Score', fontsize=12, fontweight='bold')
ax.set_title('MTL Configuration Comparison: Architecture × Training Strategy',
             fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x + width)
ax.set_xticklabels(arch_order, fontsize=11)
ax.legend(title='Trainer', fontsize=10, title_fontsize=11, loc='upper right')
ax.set_ylim(0, 1.15)

# Add grid
ax.yaxis.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

# Add horizontal line at 0.8 for reference
ax.axhline(y=0.8, color='gray', linestyle=':', alpha=0.5, label='_nolegend_')

plt.tight_layout()

# Save figure
output_path = r'D:\__desktop\Isabella\Isa\Isabella2\__Artic2\figures\fig_mtl_comparison_grouped.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"Saved to: {output_path}")

# Also save PDF for LaTeX
output_pdf = r'D:\__desktop\Isabella\Isa\Isabella2\__Artic2\figures\fig_mtl_comparison_grouped.pdf'
plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
print(f"Saved to: {output_pdf}")

plt.close()
print("Done!")
