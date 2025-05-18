# Building Retrofit Multi-Task Learning

This repository contains an end-to-end pipeline for predicting energy use, cost, carbon emission and comfort for building retrofit scenarios. The project uses multi-task learning (MTL) models and provides utilities for optimization and decision making.

## Project Structure

- **Data preprocessing** (`src/data_preprocessing.py`)
  - Reads input CSV files from the `inputs/` directory.
  - Computes additional features such as total cost, total carbon emission and comfort days.
  - Splits the data into training, validation and test sets and saves intermediate CSVs in `ARCHIEVE/`.

- **Training** (`src/training_pipeline.py`)
  - Trains multiple neural network architectures and saving the models to `models/`.
  - Corresponding input and output scalers are stored under `scalers/`.

- **Evaluation** (`src/evaluation_pipeline.py`)
  - Loads saved models and scalers to compute metrics and generate plots.

- **Optimization** (`src/optimization_pipeline.py`)
  - Provides user-driven and constraint-based multi-objective optimization approaches for selecting retrofit solutions.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the main pipeline. Optional arguments can be combined as needed:
   ```bash
   python main.py [--train] [--evaluate] [--inference] [--optimize] [--mcdm] [--postprocess]
   ```

3. Launch the Streamlit web interface:
   ```bash
   streamlit run streamlit_app.py
   ```

## Data and Outputs

- Input CSV files are located in the `inputs/` folder (e.g. `2020_merged_simulation_results.csv`).
- Trained model weights are saved in the `models/` directory.
- Scalers used for normalization are stored in the `scalers/` directory.

