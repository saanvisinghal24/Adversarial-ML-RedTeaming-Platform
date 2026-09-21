from ucimlrepo import fetch_ucirepo 
import pandas as pd 
d = fetch_ucirepo(id=327) 
X = d.data.features 
y = d.data.targets 
df = pd.concat([X, y], axis=1) 
df.to_csv('phishing_data.csv', index=False) 
print('Done! phishing_data.csv ban gayi.')
