import numpy as np
import streamlit as st
import plotly.graph_objects as go

# ============================
# Properties (engineering approx)
# ============================
MATERIALS = {
    "Copper":      {"rho0": 1.68e-8, "alpha": 0.0039, "emissivity": 0.70},
    "Pure Nickel": {"rho0": 6.99e-8, "alpha": 0.0060, "emissivity": 0.80},
    "Crofer22":    {"rho0": 1.20e-6, "alpha": 0.0010, "emissivity": 0.85},
}

SIGMA = 5.670374419e-8  # Stefan–Boltzmann [W/m^2/K^4]
T_REF = 293.15          # 20°C in K


# ============================
# Helpers
# ============================
def resistivity_at_T(rho0, alpha, T_K):
    """ρ(T) = ρ0*(1 + α*(T - Tref))"""
    return max(rho0 * (1.0 + alpha * (T_K - T_REF)), 1e-20)


def geom_rod(d_mm, L_mm):
    d = max(d_mm, 1e-6) / 1000.0
    L = max(L_mm, 1e-6) / 1000.0
    A_cs = np.pi * (d / 2.0) ** 2
    A_surf = np.pi * d * L  # ends neglected
    label = f"Rod: d={d_mm:.3g} mm, L={L_mm:.3g} mm"
    return A_cs, A_surf, label


def geom_plate(w_mm, t_mm, L_mm):
    w = max(w_mm, 1e-6) / 1000.0
    t = max(t_mm, 1e-6) / 1000.0
    L = max(L_mm, 1e-6) / 1000.0
    A_cs = w * t
    A_surf = 2.0 * (w + t) * L  # ends neglected
    label = f"Plate: w={w_mm:.3g} mm, t={t_mm:.3g} mm, L={L_mm:.3g} mm"
    return A_cs, A_surf, label


def solve_Trod_radiation(P_W, eps, A_surf, T_furnace_K):
    """
    Radiation-only balance:
      P = eps*sigma*A*(Trod^4 - Tf^4)
      => Trod = (P/(eps*sigma*A) + Tf^4)^(1/4)
    """
    if P_W <= 0:
        return T_furnace_K
    denom = max(eps * SIGMA * max(A_surf, 1e-20), 1e-20)
    return ((P_W / denom) + T_furnace_K**4) ** 0.25


def style_axes_black_grid(fig, x_range=(0, 300), title=""):
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=18)),
        margin=dict(l=80, r=25, t=55, b=70),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(font=dict(size=14)),
    )
    fig.update_xaxes(
        range=list(x_range),
        tickfont=dict(size=18),
        title_font=dict(size=18),
        showgrid=True,
        gridcolor="black",
        gridwidth=1,
        zeroline=True,
        zerolinecolor="black",
        zerolinewidth=1,
        showline=True,
        linecolor="black",
        linewidth=2,
        mirror=True,
    )
    fig.update_yaxes(
        tickfont=dict(size=18),
        title_font=dict(size=18),
        showgrid=True,
        gridcolor="black",
        gridwidth=1,
        zeroline=True,
        zerolinecolor="black",
        zerolinewidth=1,
        showline=True,
        linecolor="black",
        linewidth=2,
        mirror=True,
    )
    return fig


# ============================
# UI
# ============================
st.set_page_config(page_title="Current Conductor Loss & Temp Rise", layout="wide")

st.markdown(
    "<h2 style='margin-bottom:0.2rem;'>Current Conductor Loss & Temperature Rise (Furnace)</h2>",
    unsafe_allow_html=True
)

st.caption("Resistance loss (I²R) and radiation-only temperature rise estimate inside a hot furnace. "
           "This is an engineering approximation; gas convection and end conduction are not included.")

st.markdown("---")
st.subheader("Input Parameters")

c1, c2, c3, c4 = st.columns(4)

with c1:
    shape = st.selectbox("Shape", ["Rod", "Plate"])

with c2:
    furnace_temp_c = st.number_input("Furnace Temperature (°C)", min_value=600.0, max_value=800.0, value=700.0, step=5.0)

with c3:
    current_a = st.number_input("Current (A)", min_value=0.0, max_value=300.0, value=150.0, step=1.0)

with c4:
    length_mm = st.number_input("Length (mm)", min_value=10.0, max_value=5000.0, value=500.0, step=10.0)

c5, c6, c7, c8 = st.columns(4)

with c5:
    material_name = st.selectbox("Material", list(MATERIALS.keys()))

mat = MATERIALS[material_name]

with c6:
    eps_mode = st.selectbox("Emissivity ε", ["Use material default", "Manual"])
with c7:
    if eps_mode == "Manual":
        emissivity = st.number_input("ε (0.1–0.95)", min_value=0.10, max_value=0.95, value=float(mat["emissivity"]), step=0.01)
    else:
        emissivity = float(mat["emissivity"])
    st.write("")  # spacer
with c8:
    st.metric("ε used", f"{emissivity:.2f}")

# Geometry inputs
if shape == "Rod":
    g1, g2, g3 = st.columns(3)
    with g1:
        diameter_mm = st.number_input("Rod diameter (mm)", min_value=0.1, max_value=100.0, value=10.0, step=0.5)
    with g2:
        st.write("")
    with g3:
        st.write("")
    A_cs, A_surf, geom_label = geom_rod(diameter_mm, length_mm)
else:
    g1, g2, g3 = st.columns(3)
    with g1:
        width_mm = st.number_input("Plate width (mm)", min_value=0.1, max_value=200.0, value=20.0, step=1.0)
    with g2:
        thickness_mm = st.number_input("Plate thickness (mm)", min_value=0.1, max_value=50.0, value=2.0, step=0.1)
    with g3:
        st.write("")
    A_cs, A_surf, geom_label = geom_plate(width_mm, thickness_mm, length_mm)

st.caption(f"Geometry: {geom_label}")

# ============================
# Calculations
# ============================
T_furnace_K = furnace_temp_c + 273.15
rho_T = resistivity_at_T(mat["rho0"], mat["alpha"], T_furnace_K)

L_m = length_mm / 1000.0
R_ohm = rho_T * L_m / max(A_cs, 1e-20)
P_loss_W = (current_a ** 2) * R_ohm

T_rod_K = solve_Trod_radiation(P_loss_W, emissivity, A_surf, T_furnace_K)
deltaT_C = T_rod_K - T_furnace_K

qpp = P_loss_W / max(A_surf, 1e-20)  # W/m^2

# ============================
# Results
# ============================
st.markdown("---")
st.subheader("Results")

r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("Resistivity ρ(T) (Ω·m)", f"{rho_T:.3e}")
r2.metric("Resistance R (Ω)", f"{R_ohm:.6g}")
r3.metric("Power loss I²R (W)", f"{P_loss_W:.2f}")
r4.metric("Rod/Plate temp (°C)", f"{T_rod_K - 273.15:.1f}")
r5.metric("ΔT (°C) (radiation-only)", f"{deltaT_C:.1f}")

st.caption(f"Heat flux (P/A_surface): {qpp:.3g} W/m²")

# ============================
# Plot: ΔT vs Current (0–300A fixed)
# ============================
st.markdown("---")
st.subheader("Sweep Plot (Current axis fixed: 0–300A)")

currents = np.linspace(0.0, 300.0, 121)
deltaTs = []
powers = []

for I in currents:
    P = (I ** 2) * R_ohm
    Trod = solve_Trod_radiation(P, emissivity, A_surf, T_furnace_K)
    deltaTs.append(Trod - T_furnace_K)
    powers.append(P)

fig = go.Figure()
fig.add_trace(go.Scatter(x=currents, y=deltaTs, mode="lines", name="ΔT"))

fig.update_layout(
    xaxis_title="Current (A)",
    yaxis_title="Temperature rise ΔT (°C)",
)
style_axes_black_grid(fig, x_range=(0, 300), title="Temperature Rise ΔT vs Current")

st.plotly_chart(fig, use_container_width=True)

# Optional second plot (power) — comment out if you don't want it
with st.expander("Show power loss (I²R) vs Current"):
    figP = go.Figure()
    figP.add_trace(go.Scatter(x=currents, y=powers, mode="lines", name="I²R"))
    figP.update_layout(
        xaxis_title="Current (A)",
        yaxis_title="Power loss I²R (W)",
    )
    style_axes_black_grid(figP, x_range=(0, 300), title="Power Loss I²R vs Current")
    st.plotly_chart(figP, use_container_width=True)

# ============================
# Simple warnings
# ============================
warns = []
if P_loss_W > 50:
    warns.append("Power loss is > 50 W (check acceptable loss).")
if deltaT_C > 50:
    warns.append("Estimated ΔT > 50°C (check oxidation/creep/supports).")

if warns:
    st.warning("\n".join([f"- {w}" for w in warns]))
else:
    st.success("No immediate warnings for the selected condition (based on this simplified radiation-only model).")