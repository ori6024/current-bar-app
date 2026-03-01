import numpy as np
import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Material resistivity data (at 20°C, Ω·m)
# Temperature coefficient alpha (1/K)
# Emissivity (rough, oxidized at high T tends to higher)
# NOTE: These are engineering approximations.
# -----------------------------
materials = {
    "Copper":      {"rho0": 1.68e-8, "alpha": 0.0039, "emissivity": 0.70},
    "Pure Nickel": {"rho0": 6.99e-8, "alpha": 0.0060, "emissivity": 0.80},
    "Crofer22":    {"rho0": 1.20e-6, "alpha": 0.0010, "emissivity": 0.85},
}

SIGMA = 5.670374419e-8  # Stefan–Boltzmann [W/m^2/K^4]
T_REF = 293.15          # 20°C

st.set_page_config(page_title="Current Conductor Loss & Temp Rise", layout="wide")

st.markdown(
    "<h2 style='margin-bottom:0.2rem;'>Current Conductor Loss & Temperature Rise (Furnace)</h2>",
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("Inputs")

    shape = st.selectbox("Shape", ["Rod (cylindrical)", "Plate (rectangular)"])
    furnace_temp_c = st.slider("Furnace Temperature (°C)", 600, 800, 700, 5)
    current_a = st.slider("Current (A)", 50, 300, 150, 1)
    length_mm = st.slider("Length (mm)", 50, 2000, 500, 10)

    material_name = st.selectbox("Material", list(materials.keys()))
    emissivity_override = st.checkbox("Override emissivity (ε)", value=False)
    if emissivity_override:
        eps = st.slider("Emissivity ε", 0.10, 0.95, float(materials[material_name]["emissivity"]), 0.01)
    else:
        eps = float(materials[material_name]["emissivity"])

    st.markdown("---")
    st.caption("Geometry")

    if shape.startswith("Rod"):
        diameter_mm = st.slider("Rod diameter (mm)", 3, 30, 10, 1)
        width_mm = None
        thickness_mm = None
    else:
        width_mm = st.slider("Plate width (mm)", 3, 100, 20, 1)
        thickness_mm = st.slider("Plate thickness (mm)", 0.2, 30.0, 2.0, 0.1)
        diameter_mm = None

    st.markdown("---")
    st.caption("Notes: Temperature rise is estimated by radiation balance only (conservative in still furnace, may under/over depending on gas flow).")

# -----------------------------
# Geometry
# -----------------------------
L = length_mm / 1000.0  # m

if shape.startswith("Rod"):
    d = diameter_mm / 1000.0  # m
    A_cs = np.pi * (d / 2.0) ** 2              # cross-sectional area [m^2]
    A_surf = np.pi * d * L                     # lateral surface area [m^2] (ends neglected)
    geom_label = f"Rod: d={diameter_mm} mm, L={length_mm} mm"
else:
    w = width_mm / 1000.0
    t = thickness_mm / 1000.0
    A_cs = w * t                               # cross-sectional area [m^2]
    A_surf = 2.0 * (w + t) * L                 # perimeter*L [m^2] (ends neglected)
    geom_label = f"Plate: w={width_mm} mm, t={thickness_mm} mm, L={length_mm} mm"

# Guard against too-small geometry
A_cs = max(A_cs, 1e-12)
A_surf = max(A_surf, 1e-12)

# -----------------------------
# Resistivity model
# ρ(T) = ρ0 * (1 + α*(T - Tref))
# -----------------------------
mat = materials[material_name]
T_furnace = furnace_temp_c + 273.15

rho_T = mat["rho0"] * (1.0 + mat["alpha"] * (T_furnace - T_REF))
rho_T = max(rho_T, 1e-12)

# Electrical resistance and loss
R = rho_T * L / A_cs
P_loss = (current_a ** 2) * R

# -----------------------------
# Radiation-based temperature rise
# Solve: P = εσ A_s (T_rod^4 - T_furnace^4)
# -----------------------------
def solve_Trod(P):
    if P <= 0:
        return T_furnace
    # closed-form exists:
    # Trod = (P/(εσA) + Tf^4)^(1/4)
    return ((P / (eps * SIGMA * A_surf)) + (T_furnace ** 4)) ** 0.25

T_rod = solve_Trod(P_loss)
delta_T = T_rod - T_furnace

# Heat flux (useful for intuition)
qpp = P_loss / A_surf  # W/m^2

# -----------------------------
# Display results
# -----------------------------
st.subheader("Results")
st.caption(geom_label)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Resistance R (Ω)", f"{R:.6g}")
c2.metric("Power loss I²R (W)", f"{P_loss:.2f}")
c3.metric("Heat flux P/A (W/m²)", f"{qpp:.3g}")
c4.metric("ΔT (°C) (radiation-only)", f"{delta_T:.1f}")

st.markdown(
    f"- **ρ(T)** used at furnace T: `{rho_T:.3e} Ω·m`  (ε = {eps:.2f})\n"
    f"- **T_rod** ≈ `{T_rod - 273.15:.1f} °C`"
)

# -----------------------------
# Graph: ΔT vs Current (keeping geometry & furnace T fixed)
# -----------------------------
st.subheader("Sweep: Temperature rise vs Current (same geometry & furnace T)")
currents = np.linspace(50, 300, 60)
deltaTs = []

for I in currents:
    P_i = (I ** 2) * R
    T_i = solve_Trod(P_i)
    deltaTs.append(T_i - T_furnace)

fig = go.Figure()
fig.add_trace(go.Scatter(x=currents, y=deltaTs, mode="lines", name="ΔT"))
fig.update_layout(
    title=dict(text="ΔT vs Current", x=0.5, xanchor="center", font=dict(size=16)),
    margin=dict(l=60, r=20, t=55, b=70),
    xaxis_title="Current (A)",
    yaxis_title="Temperature rise ΔT (°C)",
)
fig.update_xaxes(tickfont=dict(size=10), fixedrange=True)
fig.update_yaxes(tickfont=dict(size=10), fixedrange=True)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Optional: quick warning thresholds
# -----------------------------
st.subheader("Quick checks")
warns = []
if P_loss > 50:
    warns.append("Power loss is > 50 W (check if acceptable for your stack / busbar).")
if delta_T > 50:
    warns.append("Estimated ΔT > 50°C (may risk oxidation/creep depending on material & supports).")
if warns:
    st.warning("\n".join([f"- {w}" for w in warns]))
else:
    st.success("No immediate warnings with the simple radiation-only estimate.")