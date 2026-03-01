fig = go.Figure()
fig.add_trace(go.Scatter(x=currents, y=deltaTs, mode="lines", name="ΔT"))

# ---- 固定レンジ & 目盛拡大 & 黒い縦横グリッド ----
fig.update_layout(
    margin=dict(l=70, r=25, t=45, b=60),
    xaxis_title="Current (A)",
    yaxis_title="Temperature Rise (°C)",
    title=dict(text="Temperature Rise vs Current", x=0.5, xanchor="center", font=dict(size=18)),
    paper_bgcolor="white",
    plot_bgcolor="white",
    legend=dict(font=dict(size=14)),
)

fig.update_xaxes(
    range=[0, 300],          # ★ 0–300A 固定
    tickfont=dict(size=16),  # ★ 目盛を大きく
    title_font=dict(size=16),
    showgrid=True,
    gridcolor="black",       # ★ 縦グリッド黒
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
    tickfont=dict(size=16),  # ★ 目盛を大きく
    title_font=dict(size=16),
    showgrid=True,
    gridcolor="black",       # ★ 横グリッド黒
    gridwidth=1,
    zeroline=True,
    zerolinecolor="black",
    zerolinewidth=1,
    showline=True,
    linecolor="black",
    linewidth=2,
    mirror=True,
)

st.plotly_chart(fig, use_container_width=True)