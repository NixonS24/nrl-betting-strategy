import pandas as pd
import sys

try:
    df = pd.read_excel('data/raw/nrl.xlsx', engine='openpyxl')
    print("Columns:", df.columns.tolist())
    print("\nHead of data:")
    print(df.head(10))
    print("\nShape:", df.shape)
except Exception as e:
    print(f"Error reading Excel file: {e}")
    sys.exit(1)
