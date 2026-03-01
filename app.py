import numpy as np
import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Material properties
# -----------------------------
materials = {
    "Copper":      {"rho0": 1.68e-8, "alpha": 0.0039, "emissivity": 0.70},
    "Pure Nickel": {"rho0": 6.99e-8, "alpha": 0.0060, "emissivity": 0.80},
    "Crofer22":    {"rho0": 1.20e-6, "alpha": 0.0010, "emissivity": 0.85},
}

SIGMA = 5.670374419e-8
T_REF = 293.15

st.set_page_config(layout="wide")

st.title("Current Conductor Loss & Temperature Rise Calculator")

# =============================
# INPUT SECTION (TOP DISPLAY)
# =============================

st.header("Input Parameters")

col1, col2, col3, col4 = st.columns(4)

with col1:
    shape = st.selectbox("Shape", ["Rod", "Plate"])

with col2:
    furnace_temp_c = st.number_input("Furnace Temperature (°C)", 600.0, 800.0, 700.0)

with col3:
    current_a = st.number_input("Current (A)", 0.0, 1000.0, 150.0)

with col4:
    length_mm = st.number_input("Length (mm)", 1.0, 5000.0, 500.0)

col5, col6, col7 = st.columns(3)

with col5:
    material_name = st.selectbox("Material", list(materials.keys()))

with col6:
    if shape == "Rod":
        diameter_mm = st.number_input("Diameter (mm)", 0.1, 100.0, 10.0)
    else:
        width_mm = st.number_input("Width (mm)", 0.1, 200.0, 20.0)

with col7:
    if shape == "Plate":
        thickness_mm = st.number_input("Thickness (mm)", 0.1, 100.0, 2.0)

# =============================
# CALCULATION
# =============================

L = length_mm / 1000.0
T_furnace = furnace_temp_c + 273.15
mat = materials[material_name]

rho_T = mat["rho0"] * (1 + mat["alpha"] * (T_furnace - T_REF))

if shape == "Rod":
    d = diameter_mm / 1000.0
    A_cs = np.pi * (d/2)**2
    A_surf = np.pi * d * L
else:
    w = width_mm / 1000.0
    t = thickness_mm / 1000.0
    A_cs = w * t
    A_surf = 2*(w + t) * L

R = rho_T * L / A_cs
P_loss = current_a**2 * R

epsilon = mat["emissivity"]

T_rod = ((P_loss/(epsilon*SIGMA*A_surf)) + T_furnace**4)**0.25
delta_T = T_rod - T_furnace

# =============================
# RESULTS
# =============================

st.header("Results")

r1, r2, r3, r4 = st.columns(4)

r1.metric("Resistance (Ω)", f"{R:.6g}")
r2.metric("Power Loss (W)", f"{P_loss:.2f}")
r3.metric("Rod Temperature (°C)", f"{T_rod-273.15:.1f}")
r4.metric("Temperature Rise ΔT (°C)", f"{delta_T:.1f}")

# =============================
# GRAPH
# =============================

st.header("Temperature Rise vs Current")

currents = np.linspace(0, 300, 60)
deltaTs = []

for I in currents:
    P = I**2 * R
    T_temp = ((P/(epsilon*SIGMA*A_surf)) + T_furnace**4)**0.25
    deltaTs.append(T_temp - T_furnace)

fig = go.Figure()
fig.add_trace(go.Scatter(x=currents, y=deltaTs, mode="lines"))

fig.update_layout(
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis_title="Current (A)",
    yaxis_title="Temperature Rise (°C)",
)

st.plotly_chart(fig, use_container_width=True)