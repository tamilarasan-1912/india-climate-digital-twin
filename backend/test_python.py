import numpy as np
import pandas as pd
import xarray as xr

print("================================")
print("INDIA CLIMATE DIGITAL TWIN")
print("Python scientific engine test")
print("================================")

values = np.array([25.4, 27.1, 29.8, 31.2])

print("Temperature values:")
print(values)

print()

print("Average temperature:")
print(values.mean())

print()

data = pd.DataFrame({
    "temperature": values
})

print("Pandas DataFrame:")
print(data)

print()

print("Python scientific engine is working.")

