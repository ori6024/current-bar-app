import numpy as np
import streamlit as st
import plotly.graph_objects as go

# ============================
# Material properties
# ============================
# For Copper / Pure Nickel: linear model from 20°C
# For Crofer22: measured points (700/800/900°C) and interpolation
MATERIALS = {
    "Copper": {
        "model": "linear",
        "rho0_ohm_m": 1.68e-8,     # at 20°C
        "alpha_1_per_K": 0.0039,
        "emissivity": 0.70,
    },
    "Pure Nickel": {
        "model": "linear",
        "rho0_ohm_m": 6.99e-8,     # at 20°C
        "alpha_1_per_K": 0.0060,
        "emissivity": 0.80,
    },
    "Crofer22": {
        "model": "measured_interp",
        # Measured representative values (Excel): ρ700/800/900 in µΩ·cm
        # Convert: (µΩ·cm) -> (Ω·m) by ×1e-8
        # because 1 µΩ·cm = 1e-6 Ω·cm = 1e-8 Ω·m
        "T_C_points": [700.0, 800.0, 900.0],
        "rho_uohm_cm_points": [110.0, 115.0, 117.5],
        "emissivity": 0.85,
    },
}

SIGMA = 5.670374419e-8  # Stefan–Boltzmann [W/m^2/K^4]
T_REF_K = 293.15        # 20°C in K


# ============================
# Helpers
# ============================
def uohm_cm_to_ohm_m(x_uohm_cm: float) -> float:
    # 1 µΩ·cm = 1e-8 Ω·m
    return float(x_uohm_cm) * 1e-8


def rho_linear(rho0_ohm_m: float, alpha_1_per_K: float, T_K: float) -> float:
    """ρ(T) = ρ0*(1 + α*(T - Tref))"""
    return max(rho0_ohm_m * (1.0 + alpha_1_per_K * (T_K - T_REF_K)), 1e-20)


def rho_crofer_interp(T_C: float, T_points_C, rho_points_uohm_cm) -> float:
    """Piecewise linear interpolation on measured ρ(T) points. Clamped outside range."""
    T_points_C = np.array(T_points_C, dtype=float)
    rho_points = np.array([uohm_cm_to_ohm_m(v) for v in rho_points_uohm_cm], dtype=float)

    # Clamp outside range (so it doesn't extrapolate wildly)
    if T_C <= T_points_C.min():
        return float(rho_points[0])
    if T_C >= T_points_C.max():
        return float(rho_points[-1])

    return float(np.interp(T_C, T_points_C, rho_points))


def geom_rod(d_mm: float, L_mm: float):
    d_m = max(d_mm, 1e-9) / 1000.0
    L_m = max(L_mm, 1e-9) / 1000.0
    A_cs = np.pi * (d_m / 2.0) ** 2
    A_surf = np.pi * d_m * L_m  # ends neglected
    label = f"Rod: d={d_mm:g} mm, L={L_mm:g} mm"
    return A_cs, A_surf, label


def geom_plate(w_mm: float, t_mm: float, L_mm: float):
    w_m = max(w_mm, 1e-9) / 1000.0
    t_m = max(t_mm, 1e-9) / 1000.0
    L_m = max(L_mm, 1e-9) / 1000.0
    A_cs = w_m * t_m
    A_surf = 2.0 * (w_m + t_m) * L_m  # ends neglected
    label = f"Plate: w={w_mm:g} mm, t={t_mm:g} mm, L={L_mm:g} mm"
    return A_cs, A_surf, label


def solve_Trod_radiation(P_W: float, eps: float, A_surf: float, T_furnace_K: float) -> float:
    """Radiation-only: P = eps*sigma*A*(Trod^4 - Tf^4)"""
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


def compute_rho(material_name: str, furnace_temp_c: float) -> tuple[float, str]:
    """Return rho(T) in Ω·m and a short model description."""
    mat = MATERIALS[material_name]
    model = mat["model"]

    if model == "linear":
        T_K = furnace_temp_c + 273.15
        rho = rho_linear(mat["rho0_ohm_m"], mat["alpha_1_per_K"], T_K)
        return rho, f"Linear from 20°C: ρ(T)=ρ0(1+αΔT), ρ0={mat['rho0_ohm_m']:.3e}, α={mat['alpha_1_per_K']:.4f}"
    elif model == "measured_interp":
        rho = rho_crofer_interp(furnace_temp_c, mat["T_C_points"], mat["rho_uohm_cm_points"])
        pts = ", ".join([f"{T:g}°C→{v:g} µΩ·cm" for T, v in zip(mat["T_C_points"], mat["rho_uohm_cm_points"])])
        return rho, f"Measured interpolation (clamped): {pts}"
    else:
        # fallback
        return 1e-6, "Unknown model (fallback)"


# ============================
# UI
# ============================
st.set_page_config(page_title="Current Conductor Loss & Temp Rise", layout="wide")

st.markdown(
    "<h2 style='margin-bottom:0.2rem;'>Current Conductor Loss, Voltage Drop & Temperature Rise (Furnace)</h2>",
    unsafe_allow_html=True
)

st.caption(
    "Resistance loss (I²R), voltage drop (I·R), and radiation-only temperature rise estimate inside a hot furnace. "
    "Crofer22 uses measured-point interpolation (700/800/900°C)."
)

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
        emissivity = st.number_input("ε (0.10–0.95)", min_value=0.10, max_value=0.95, value=float(mat["emissivity"]), step=0.01)
    else:
        emissivity = float(mat["emissivity"])
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
rho_T, rho_model_note = compute_rho(material_name, furnace_temp_c)

L_m = length_mm / 1000.0
R_ohm = rho_T * L_m / max(A_cs, 1e-20)

P_loss_W = (current_a ** 2) * R_ohm
Vdrop_oneway = current_a * R_ohm
Vdrop_roundtrip = current_a * (2.0 * R_ohm)

T_furnace_K = furnace_temp_c + 273.15
T_rod_K = solve_Trod_radiation(P_loss_W, emissivity, A_surf, T_furnace_K)
deltaT_C = T_rod_K - T_furnace_K

qpp = P_loss_W / max(A_surf, 1e-20)

# ============================
# Results
# ============================
st.markdown("---")
st.subheader("Results")

r1, r2, r3, r4, r5, r6 = st.columns(6)
r1.metric("Resistivity ρ(T) (Ω·m)", f"{rho_T:.3e}")
r2.metric("Resistance R (Ω)", f"{R_ohm:.6g}")
r3.metric("Voltage drop (one-way) (V)", f"{Vdrop_oneway:.4f}")
r4.metric("Voltage drop (round-trip) (V)", f"{Vdrop_roundtrip:.4f}")
r5.metric("Power loss I²R (W)", f"{P_loss_W:.2f}")
r6.metric("ΔT (°C) (radiation-only)", f"{deltaT_C:.1f}")

st.caption(f"Rod/Plate temperature ≈ {T_rod_K - 273.15:.1f} °C    |    Heat flux: {qpp:.3g} W/m²")
st.info(f"ρ(T) model: {rho_model_note}")

# ============================
# Sweep plots (0–300A fixed)
# ============================
st.markdown("---")
st.subheader("Sweep Plot (Current axis fixed: 0–300A)")

currents = np.linspace(0.0, 300.0, 121)
deltaTs = []
powers = []
v_one = []
v_round = []

for I in currents:
    P = (I ** 2) * R_ohm
    Trod = solve_Trod_radiation(P, emissivity, A_surf, T_furnace_K)
    deltaTs.append(Trod - T_furnace_K)
    powers.append(P)
    v_one.append(I * R_ohm)
    v_round.append(I * 2.0 * R_ohm)

# ΔT vs I
figT = go.Figure()
figT.add_trace(go.Scatter(x=currents, y=deltaTs, mode="lines", name="ΔT"))
figT.update_layout(xaxis_title="Current (A)", yaxis_title="Temperature rise ΔT (°C)")
style_axes_black_grid(figT, x_range=(0, 300), title="Temperature Rise ΔT vs Current")
st.plotly_chart(figT, use_container_width=True)

with st.expander("Show power loss (I²R) vs Current"):
    figP = go.Figure()
    figP.add_trace(go.Scatter(x=currents, y=powers, mode="lines", name="I²R"))
    figP.update_layout(xaxis_title="Current (A)", yaxis_title="Power loss I²R (W)")
    style_axes_black_grid(figP, x_range=(0, 300), title="Power Loss I²R vs Current")
    st.plotly_chart(figP, use_container_width=True)

with st.expander("Show voltage drop vs Current"):
    figV = go.Figure()
    figV.add_trace(go.Scatter(x=currents, y=v_one, mode="lines", name="ΔV one-way"))
    figV.add_trace(go.Scatter(x=currents, y=v_round, mode="lines", name="ΔV round-trip"))
    figV.update_layout(xaxis_title="Current (A)", yaxis_title="Voltage drop ΔV (V)")
    style_axes_black_grid(figV, x_range=(0, 300), title="Voltage Drop ΔV vs Current")
    st.plotly_chart(figV, use_container_width=True)

# ============================
# Simple warnings
# ============================
warns = []
if P_loss_W > 50:
    warns.append("Power loss is > 50 W (check acceptable loss).")
if deltaT_C > 50:
    warns.append("Estimated ΔT > 50°C (check oxidation/creep/supports).")
if Vdrop_roundtrip > 0.5:
    warns.append("Round-trip voltage drop > 0.5 V (check system voltage margin).")

if warns:
    st.warning("\n".join([f"- {w}" for w in warns]))
else:
    st.success("No immediate warnings for the selected condition (based on this simplified model).")