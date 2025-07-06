
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# Raw data from 1961–2000 table (Gumbel analysis previously done)
durations_min = [5, 10, 15, 30, 60, 120, 360, 720, 1440]  # in minutes
return_periods = [2, 5, 10, 25, 50, 100]

# Intensity data (mm/hr) from the generated IDF table
idf_data = {
    5:   [126.1, 146.4, 159.3, 176.2, 189.1, 206.1],
    10:  [87.7, 102.3, 111.4, 124.4, 133.4, 145.2],
    15:  [70.0, 81.9, 89.2, 99.8, 107.2, 116.6],
    30:  [45.5, 53.9, 58.9, 66.1, 71.1, 77.5],
    60:  [27.6, 32.4, 35.2, 39.3, 42.1, 45.6],
    120: [15.0, 17.5, 19.0, 21.2, 22.7, 24.6],
    360: [6.3, 7.3, 7.8, 8.7, 9.3, 10.1],
    720: [3.6, 4.1, 4.4, 4.9, 5.2, 5.6],
    1440: [2.1, 2.4, 2.6, 2.9, 3.1, 3.3]
}

# Streamlit UI
st.title("IDF Curve Viewer")
st.write("Rainfall Intensity–Duration–Frequency (IDF) curves based on historical data (1961–2000)")

# Plotting
fig, ax = plt.subplots()
for i, T in enumerate(return_periods):
    intensities = [idf_data[d][i] for d in durations_min]
    ax.plot(durations_min, intensities, marker='o', label=f"T = {T} yrs")

ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel("Duration (min)")
ax.set_ylabel("Intensity (mm/hr)")
ax.set_title("IDF Curves (Gumbel Distribution)")
ax.legend()
ax.grid(True, which="both", linestyle="--", linewidth=0.5)
st.pyplot(fig)

# Interpolation
st.subheader("📌 Get Intensity for Specific Duration and Return Period")
duration_input = st.number_input("Enter duration (minutes)", min_value=1, max_value=2000, value=10)
T_input = st.selectbox("Select return period (years)", return_periods)

# Build interpolators
interpolators = {}
for i, T in enumerate(return_periods):
    y_vals = [idf_data[d][i] for d in durations_min]
    interpolators[T] = interp1d(durations_min, y_vals, kind='linear', fill_value='extrapolate')

if duration_input:
    intensity_result = float(interpolators[T_input](duration_input))
    st.success(f"Estimated intensity: **{intensity_result:.2f} mm/hr** for {duration_input} min, T = {T_input} yrs")
