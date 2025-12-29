"""
Create a clean Model Rankings figure matching the article's Table 3.
Only includes the 10 models discussed in the paper.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Data from Table 3 in the article (tab:mtl_results)
# Format: (Architecture + Trainer, Composite Score, [Energy R², Cost R², Emission R², Comfort R²])
models_data = [
    ("Separate + MGDA", 1.000, [0.90, 0.63, 0.89, 0.89]),
    ("Separate + Uncertainty", 0.973, [0.91, 0.61, 0.88, 0.86]),
    ("Deep_Balanced + MGDA", 0.863, [0.87, 0.61, 0.84, 0.82]),
    ("Deep_Balanced + Weighted_Sum", 0.858, [0.87, 0.61, 0.85, 0.80]),
    ("Shared + MGDA", 0.835, [0.86, 0.60, 0.83, 0.79]),
    ("Deep_Balanced + Uncertainty", 0.828, [0.84, 0.60, 0.84, 0.76]),
    ("Data_Based + Uncertainty", 0.787, [0.85, 0.60, 0.81, 0.80]),
    ("Shared + Uncertainty", 0.767, [0.85, 0.59, 0.85, 0.76]),
    ("Data_Based + Weighted_Sum", 0.715, [0.85, 0.59, 0.80, 0.80]),
    ("Shared + Weighted_Sum", 0.709, [0.85, 0.58, 0.82, 0.78]),
]

# Extract data
model_names = [m[0] for m in models_data]
scores = [m[1] for m in models_data]
r2_values = [m[2] for m in models_data]

# Calculate average R² for each model
avg_r2 = [np.mean(r2) for r2 in r2_values]


def create_composite_score_chart():
    """Simple horizontal bar chart of composite scores."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Colors: highlight top 2 (MGDA variants), mid-performers, lower performers
    colors = []
    for i, (name, score, _) in enumerate(models_data):
        if "MGDA" in name and "Separate" in name:
            colors.append('#1f77b4')  # Dark blue - best
        elif "Uncertainty" in name and "Separate" in name:
            colors.append('#2ca02c')  # Green - 2nd best
        elif "MGDA" in name:
            colors.append('#7fbbdb')  # Light blue - MGDA variants
        elif "Uncertainty" in name:
            colors.append('#90d090')  # Light green - Uncertainty variants
        else:
            colors.append('#d4a574')  # Tan - Weighted_Sum variants

    y_pos = np.arange(len(model_names))
    bars = ax.barh(y_pos, scores, color=colors, edgecolor='black', linewidth=0.5)

    # Add score labels on bars
    for i, (bar, score) in enumerate(zip(bars, scores)):
        ax.text(score + 0.02, bar.get_y() + bar.get_height()/2,
                f'{score:.3f}', va='center', fontsize=10)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(model_names, fontsize=10)
    ax.invert_yaxis()  # Best at top
    ax.set_xlabel('Composite Score', fontsize=12)
    ax.set_title('MTL Configuration Rankings by Composite Score', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 1.15)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1f77b4', edgecolor='black', label='Best (Separate + MGDA)'),
        Patch(facecolor='#2ca02c', edgecolor='black', label='2nd Best (Separate + Uncertainty)'),
        Patch(facecolor='#7fbbdb', edgecolor='black', label='Other MGDA'),
        Patch(facecolor='#90d090', edgecolor='black', label='Other Uncertainty'),
        Patch(facecolor='#d4a574', edgecolor='black', label='Weighted Sum'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

    plt.tight_layout()
    return fig


def create_r2_per_task_chart():
    """Grouped bar chart showing R² per task for each model."""
    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(model_names))
    width = 0.2

    tasks = ['Energy', 'Cost', 'Emission', 'Comfort']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    for i, (task, color) in enumerate(zip(tasks, colors)):
        task_r2 = [r2[i] for r2 in r2_values]
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, task_r2, width, label=task, color=color, edgecolor='black', linewidth=0.5)

    ax.set_ylabel('R² Score', fontsize=12)
    ax.set_xlabel('Model Configuration', fontsize=12)
    ax.set_title('Task-Specific R² Scores Across MTL Configurations', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper right', fontsize=10)
    ax.set_ylim(0.5, 1.0)
    ax.axhline(y=0.8, color='gray', linestyle='--', alpha=0.5, label='R²=0.8 threshold')

    plt.tight_layout()
    return fig


def create_combined_chart():
    """Combined figure: Composite score + R² breakdown."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Left: Composite scores
    ax1 = axes[0]
    colors = []
    for name, score, _ in models_data:
        if "Separate" in name and "MGDA" in name:
            colors.append('#2E86AB')
        elif "Separate" in name:
            colors.append('#A23B72')
        elif "Deep_Balanced" in name:
            colors.append('#F18F01')
        elif "Data_Based" in name:
            colors.append('#C73E1D')
        else:
            colors.append('#6B717E')

    y_pos = np.arange(len(model_names))
    bars = ax1.barh(y_pos, scores, color=colors, edgecolor='black', linewidth=0.5)

    for bar, score in zip(bars, scores):
        ax1.text(score + 0.015, bar.get_y() + bar.get_height()/2,
                f'{score:.3f}', va='center', fontsize=9)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(model_names, fontsize=10)
    ax1.invert_yaxis()
    ax1.set_xlabel('Composite Score', fontsize=11)
    ax1.set_title('(a) Model Rankings', fontsize=12, fontweight='bold')
    ax1.set_xlim(0, 1.12)

    # Right: R² per task for top 5 only
    ax2 = axes[1]
    top_5_names = model_names[:5]
    top_5_r2 = r2_values[:5]

    x = np.arange(len(top_5_names))
    width = 0.18
    tasks = ['Energy', 'Cost', 'Emission', 'Comfort']
    task_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    for i, (task, color) in enumerate(zip(tasks, task_colors)):
        task_r2 = [r2[i] for r2 in top_5_r2]
        offset = (i - 1.5) * width
        ax2.bar(x + offset, task_r2, width, label=task, color=color, edgecolor='black', linewidth=0.5)

    ax2.set_ylabel('R² Score', fontsize=11)
    ax2.set_title('(b) Task R² for Top 5 Configurations', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.replace(' + ', '\n') for n in top_5_names], fontsize=9)
    ax2.legend(loc='lower right', fontsize=9)
    ax2.set_ylim(0.55, 0.95)
    ax2.axhline(y=0.8, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    # Create output directory
    import os
    output_dir = r"D:\__desktop\Isabella\Isa\Isabella2\figures"
    os.makedirs(output_dir, exist_ok=True)

    # Generate figures
    print("Creating figures...")

    # 1. Simple composite score chart
    fig1 = create_composite_score_chart()
    fig1.savefig(os.path.join(output_dir, "model_rankings_composite.png"), dpi=300, bbox_inches='tight')
    fig1.savefig(os.path.join(output_dir, "model_rankings_composite.pdf"), bbox_inches='tight')
    print("  Saved: model_rankings_composite.png/pdf")

    # 2. R² per task chart
    fig2 = create_r2_per_task_chart()
    fig2.savefig(os.path.join(output_dir, "model_rankings_r2_tasks.png"), dpi=300, bbox_inches='tight')
    fig2.savefig(os.path.join(output_dir, "model_rankings_r2_tasks.pdf"), bbox_inches='tight')
    print("  Saved: model_rankings_r2_tasks.png/pdf")

    # 3. Combined figure (recommended for paper)
    fig3 = create_combined_chart()
    fig3.savefig(os.path.join(output_dir, "model_rankings_combined.png"), dpi=300, bbox_inches='tight')
    fig3.savefig(os.path.join(output_dir, "model_rankings_combined.pdf"), bbox_inches='tight')
    print("  Saved: model_rankings_combined.png/pdf")

    print("\nDone! Figures saved to:", output_dir)
    # plt.show()  # Commented out for non-interactive execution
    plt.close('all')
