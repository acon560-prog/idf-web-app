"""Excel formula builders for live rating curve (no Python needed at runtime).

Mirrors hydraulics.py algebra closely enough for design use.
Inlet transition uses HW/D thresholds (0.95 / 1.2) instead of Q-space blending.
"""

from __future__ import annotations

# Absolute Parametres references (must match build_excel.py layout)
P = {
    "D": "Parametres!$C$5",
    "L": "Parametres!$C$6",
    "b": "Parametres!$C$7",
    "z": "Parametres!$C$8",
    "zin": "Parametres!$C$9",
    "zout": "Parametres!$C$10",
    "zmax": "Parametres!$C$11",
    "S0": "Parametres!$C$13",
    "n_pipe": "Parametres!$C$14",
    "TW": "Parametres!$C$16",
    "mode": "Parametres!$C$17",
    "y0": "Parametres!$C$18",
    "n_surf": "Parametres!$C$19",
    "d50": "Parametres!$C$20",
    "npor": "Parametres!$C$21",
    "Cd": "Parametres!$C$22",
    "K": "Parametres!$C$25",
    "M": "Parametres!$C$26",
    "c": "Parametres!$C$27",
    "Y": "Parametres!$C$28",
    "Ke": "Parametres!$C$29",
}

KU = "1.811"
G = "9.81"


def _area_full() -> str:
    return f"PI()*({P['D']}/2)^2"


def formula_q_inlet(hw: str) -> str:
    """HDS-5 Form-2 inverse approx. for Q given HW."""
    A = _area_full()
    # arg from unsubmerged / submerged, then Q = Ku*A*sqrt(D)*arg
    qun = (
        f"{KU}*{A}*SQRT({P['D']})"
        f"*IF({P['K']}*{P['D']}<=0,0,({hw}/({P['K']}*{P['D']}))^(1/{P['M']}))"
    )
    qsub = (
        f"{KU}*{A}*SQRT({P['D']})"
        f"*SQRT(MAX(0,({hw}/{P['D']}-{P['Y']})/{P['c']}))"
    )
    t = f"MIN(1,MAX(0,({hw}/{P['D']}-0.95)/(1.2-0.95)))"
    return (
        f'IF({hw}<=0,0,'
        f'IF({hw}<0.95*{P["D"]},{qun},'
        f'IF({hw}>1.2*{P["D"]},{qsub},'
        f"(1-({t}))*({qun})+({t})*({qsub}))))"
    )


def formula_q_outlet(hw: str) -> str:
    """Outlet control: Manning part-full or energy full-pipe."""
    # Partial section
    ratio = f"MIN(0.999,MAX(1E-6,{hw}/{P['D']}))"
    theta = f"2*ACOS(1-2*({ratio}))"
    aseg = f"(({P['D']}/2)^2/2)*(({theta})-SIN({theta}))"
    pwet = f"({P['D']}/2)*({theta})"
    rh_p = f"IF(({pwet})<=0,0,({aseg})/({pwet}))"
    q_part = (
        f"IF({P['n_pipe']}<=0,0,(1/{P['n_pipe']})*({aseg})"
        f"*IF(({rh_p})<=0,0,({rh_p})^(2/3))*SQRT({P['S0']}))"
    )
    # Full pipe energy
    a_full = _area_full()
    rh_f = f"{P['D']}/4"
    hloss = f"{hw}-{P['TW']}+{P['S0']}*{P['L']}"
    denom = (
        f"(1+{P['Ke']})/(2*{G})+"
        f"({P['n_pipe']}^2)*{P['L']}/(({rh_f})^(4/3))"
    )
    q_full = (
        f"IF(({hloss})<=0,0,{a_full}*SQRT(({hloss})/({denom})))"
    )
    return f'IF({hw}<{P["D"]},{q_part},{q_full})'


def formula_q_pipe(hw: str) -> str:
    qi = formula_q_inlet(hw)
    qo = formula_q_outlet(hw)
    return f"MIN({qi},{qo})"


def formula_control(hw: str) -> str:
    qi = formula_q_inlet(hw)
    qo = formula_q_outlet(hw)
    return f'IF({qi}<={qo},"inlet","outlet")'


def formula_q_overflow(hw: str) -> str:
    y = f"MAX(0,{hw}-{P['y0']})"
    a = f"({P['b']}+{P['z']}*({y}))*({y})"
    pw = f"{P['b']}+2*({y})*SQRT(1+{P['z']}^2)"
    rh = f"IF(({pw})<=0,0,({a})/({pw}))"
    q_surf = (
        f"IF(({y})<=0,0,(1/{P['n_surf']})*({a})"
        f"*IF(({rh})<=0,0,({rh})^(2/3))*SQRT({P['S0']}))"
    )
    v_por = (
        f"{P['Cd']}*{P['npor']}*"
        f"SQRT({G}*{P['d50']}*{P['S0']}/(1-{P['npor']}))"
    )
    q_por = f"IF(({y})<=0,0,({a})*({v_por}))"
    return (
        f'IF(LOWER({P["mode"]})="porous",{q_por},'
        f'IF(LOWER({P["mode"]})="both",{q_por}+{q_surf},{q_surf}))'
    )


def formula_s_geo(hw: str) -> str:
    """Pipe barrel + ditch prism storage (no pond)."""
    hmax = f"({P['zmax']}-{P['zin']})"
    # pipe
    ratio = f"MIN(0.999,MAX(0,MIN({hw},{P['D']})/{P['D']}))"
    theta = f"IF(({ratio})<=0,0,2*ACOS(1-2*({ratio})))"
    aseg = (
        f"IF(({ratio})<=0,0,"
        f"IF({hw}>={P['D']},PI()*({P['D']}/2)^2,"
        f"(({P['D']}/2)^2/2)*(({theta})-SIN({theta}))))"
    )
    v_pipe = f"({aseg})*{P['L']}"
    # ditch above y0 up to hmax
    y0 = P["y0"]
    y_fill = f"MAX(0,MIN({hw},{hmax})-({y0}))"
    a_d = f"({P['b']}+{P['z']}*({y_fill}))*({y_fill})"
    v_ditch = f"IF(({y_fill})<=0,0,({a_d})*{P['L']})"
    return f"{v_pipe}+{v_ditch}"
