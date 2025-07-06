
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from io import BytesIO

st.set_page_config(page_title="IDF Curve Analyzer", layout="centered")

st.title("🌧️ IDF Curve Analyzer")
st.markdown("Upload rainfall data, visualize IDF curves, and get intensity values for any duration & return period.")

# Upload CSV or Excel
uploaded_file = st.file_uploader("📤 Upload CSV or Excel with durations as columns", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully!")
        st.dataframe(df.head())

        # Assume first column is Year, rest are durations
        duration_labels = df.columns[1:]
        durations_min = []
        for label in duration_labels:
            val = label.lower().replace("min", "").replace("h", "")
            try:
                if "h" in label.lower():
                    val = float(val) * 60
                durations_min.append(int(float(val)))
            except:
                durations_min.append(0)

        return_periods = [2, 5, 10, 25, 50, 100]

        def gumbel_K(T):
            γ = 0.5772
            return (np.sqrt(6) / np.pi) * (np.log(np.log(T / (T - 1))) + γ)

        idf_result = {}
        for i, label in enumerate(duration_labels):
            values = df[label].dropna().to_numpy()
            μ = np.mean(values)
            σ = np.std(values, ddof=1)
            K = gumbel_K(return_periods)
            P_T = μ + K * σ
            intensity = P_T / (durations_min[i] / 60)
            intensity[intensity <= 0] = np.nan
            idf_result[durations_min[i]] = intensity

        # Plotting
        st.subheader("📊 IDF Curves")
        fig, ax = plt.subplots(figsize=(8, 5))
        for i, T in enumerate(return_periods):
            curve = [idf_result[d][i] for d in durations_min]
            ax.plot(durations_min, curve, marker='o', label=f"T = {T} yrs")
        ax.set_xscale("log")
        ax.set_yscale("log")
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

        # Interpolation section
        st.subheader("🔍 Intensity Lookup")
        duration_input = st.number_input("Enter duration (minutes)", min_value=1, max_value=2000, value=10)
        T_input = st.selectbox("Select return period (years)", return_periods)

        interpolators = {}
        for i, T in enumerate(return_periods):
            intensities = [idf_result[d][i] for d in durations_min]
            interpolators[T] = interp1d(durations_min, intensities, kind='linear', fill_value='extrapolate')
        interpolated = float(interpolators[T_input](duration_input))
        st.success(f"Estimated intensity for {duration_input} min & T={T_input} yrs: **{interpolated:.2f} mm/hr**")

        # Export CSV
        out_df = pd.DataFrame({"Duration (min)": durations_min})
        for i, T in enumerate(return_periods):
            out_df[f"T = {T} yrs"] = [idf_result[d][i] for d in durations_min]
        csv_data = out_df.to_csv(index=False).encode("utf-8")
        st.download_button("📄 Download Intensity Table (CSV)", data=csv_data, file_name="idf_intensity_table.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload a CSV or Excel file with rainfall intensities.")
