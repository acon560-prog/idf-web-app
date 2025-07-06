
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from io import BytesIO
from matplotlib.ticker import ScalarFormatter

st.set_page_config(page_title="IDF Curve Analyzer", layout="centered")
st.title("🌧️ IDF Curve Analyzer")
st.markdown("Upload rainfall data with durations in the first column and return periods as headers.")

uploaded_file = st.file_uploader("📤 Upload CSV or Excel (Duration column + T-year columns)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully!")
        st.dataframe(df)

        # Extract durations and return periods
        durations = df.iloc[:, 0].to_numpy(dtype=float)
        return_periods = df.columns[1:]
        idf_result = {rp: df[rp].astype(float).to_numpy() for rp in return_periods}

        # Plot IDF curves with human-readable ticks
        st.subheader("📊 IDF Curves")
        fig, ax = plt.subplots(figsize=(8, 5))
        for rp in return_periods:
            ax.plot(durations, idf_result[rp], marker='o', label=rp)

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.set_xlabel("Duration (min)")
        ax.set_ylabel("Intensity (mm/hr)")
        ax.set_title("IDF Curves")
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.legend()
        st.pyplot(fig)

        # Save PDF
        pdf_buffer = BytesIO()
        fig.savefig(pdf_buffer, format="pdf")
        st.download_button("📥 Download PDF", data=pdf_buffer.getvalue(), file_name="idf_curve.pdf", mime="application/pdf")

        # Interpolation lookup
        st.subheader("🔍 Intensity Lookup")
        duration_input = st.number_input("Enter duration (minutes)", min_value=1, max_value=2000, value=10)
        rp_input = st.selectbox("Select return period", return_periods)

        interp_func = interp1d(durations, df[rp_input].astype(float), kind='linear', fill_value='extrapolate')
        estimated = float(interp_func(float(duration_input)))
        st.success(f"Estimated intensity at {duration_input} min for {rp_input}: **{estimated:.2f} mm/hr**")

        # CSV Export
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("📄 Download Intensity Table (CSV)", data=csv_data, file_name="idf_intensity_table.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload a properly formatted file.")
