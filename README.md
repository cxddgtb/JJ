# Fund Analysis Workflow

This workflow automatically fetches, analyzes, and visualizes fund data from Tian Tian Fund.

## Workflow

1. **Data Fetching**: The workflow fetches historical fund data using the `get_fund_data` function in `scripts/fund_analysis.py`.
2. **Data Analysis**: The `analyze_data` function in `scripts/fund_analysis.py` analyzes the data to identify potential buy/sell signals.
3. **Data Visualization**: The `plot_data` function in `scripts/fund_analysis.py` creates plots to visualize the fund data.
4. **Automation**: The GitHub Actions workflow in `.github/workflows/main.yml` automates the entire process, running daily and on every push to the `main` branch.

## Usage

1. **Fork this repository.**
2. **Add your fund code to the `FUND_CODE` secret in your repository settings.**
3. **The workflow will automatically run and update the data and analysis in the `data` directory.**