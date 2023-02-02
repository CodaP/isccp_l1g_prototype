from find_files import all_files
from tqdm import tqdm
import pandas as pd
from pathlib import Path

INDEX = Path('index.csv')

if INDEX.exists():
    old_index = pd.read_csv(INDEX)
else:
    old_index = None

new_index = []

with tqdm(all_files()) as bar:
    for dt,k,f in bar:
        new_index.append((dt,k,f))

new_index = pd.DataFrame(new_index, columns=['dt','k','f'])
new_index = new_index.sort_values(['dt','k','f'])
new_index.to_csv(INDEX, index=False)

