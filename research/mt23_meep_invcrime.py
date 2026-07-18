#!/usr/bin/env python
"""MT23 Stage-0 (Meep-only) — does optimizing at a coarse discretization exploit that discretization?

Inverse-crime / discretization-exploitation test on a 1D Fabry-Perot etalon (index-N slab in air).
Fabry-Perot transmission fringes T(FCEN) oscillate with slab length L; numerical dispersion makes the
effective optical path resolution-dependent, so the L that MAXIMIZES T at the target frequency at LOW
resolution is shifted at HIGH resolution.

Falsifiable: "optimize" L at low res (argmax T(FCEN)); evaluate that L* at high res.
  - inverse-crime gap = T_lowres(L*_low) - T_highres(L*_low)  (overoptimism)
  - argmax shift = |L*_low - L*_high|
KILL if the optimum is stable across resolutions (gap ~0 AND argmax shift <= 1 grid step) -> no exploitation.
Meep 1D, registration-free (physics sim). Isolated conda env (no shared-env pollution).
"""
import meep as mp, numpy as np, json, time
N = 3.5            # slab index (Si-like)
FCEN, DF = 1.0, 1.2
DPML, PAD, NFREQ = 2.0, 3.0, 400
LMIN, LMAX, NL = 0.30, 0.80, 26   # ~2 fringe periods (period = lambda/(2N) = 1/(2*3.5) ~ 0.143)
RES_LOW, RES_HIGH = 20, 120

def empty_flux(res):
    sz = 2*DPML + 2*PAD + LMAX
    cell = mp.Vector3(0, 0, sz)
    src_z = -0.5*sz + DPML + 0.5; mon_z = 0.5*sz - DPML - 0.5
    src = [mp.Source(mp.GaussianSource(FCEN, fwidth=DF), component=mp.Ex, center=mp.Vector3(0,0,src_z))]
    sim = mp.Simulation(cell_size=cell, boundary_layers=[mp.PML(DPML, direction=mp.Z)],
                        sources=src, resolution=res, dimensions=1)
    fr = sim.add_flux(FCEN, DF, NFREQ, mp.FluxRegion(center=mp.Vector3(0,0,mon_z)))
    sim.run(until_after_sources=mp.stop_when_fields_decayed(20, mp.Ex, mp.Vector3(0,0,mon_z), 1e-6))
    return np.array(mp.get_flux_freqs(fr)), np.array(mp.get_fluxes(fr)), src, sz, mon_z

def T_at_fcen(L, res, freqs0, flux0, src, sz, mon_z):
    cell = mp.Vector3(0, 0, sz)
    geom = [mp.Block(mp.Vector3(mp.inf, mp.inf, L), center=mp.Vector3(0,0,0), material=mp.Medium(index=N))]
    sim = mp.Simulation(cell_size=cell, boundary_layers=[mp.PML(DPML, direction=mp.Z)],
                        sources=src, geometry=geom, resolution=res, dimensions=1)
    fr = sim.add_flux(FCEN, DF, NFREQ, mp.FluxRegion(center=mp.Vector3(0,0,mon_z)))
    sim.run(until_after_sources=mp.stop_when_fields_decayed(20, mp.Ex, mp.Vector3(0,0,mon_z), 1e-6))
    T = np.array(mp.get_fluxes(fr)) / flux0
    i = int(np.argmin(np.abs(freqs0 - FCEN)))
    return float(T[i])

def sweep(res):
    freqs0, flux0, src, sz, mon_z = empty_flux(res)
    Ls = np.linspace(LMIN, LMAX, NL); Ts = []
    for L in Ls:
        Ts.append(T_at_fcen(L, res, freqs0, flux0, src, sz, mon_z))
    return Ls, np.array(Ts)

def main():
    t0 = time.time()
    print('low-res sweep...', flush=True)
    Ll, Tl = sweep(RES_LOW)
    print('high-res sweep...', flush=True)
    Lh, Th = sweep(RES_HIGH)
    i_low = int(np.argmax(Tl)); Lstar_low = float(Ll[i_low])
    i_high = int(np.argmax(Th)); Lstar_high = float(Lh[i_high])
    # high-res T at the low-res-optimal L (nearest grid point on the shared L grid)
    j = int(np.argmin(np.abs(Lh - Lstar_low)))
    T_high_at_lowopt = float(Th[j])
    gap = float(Tl[i_low] - T_high_at_lowopt)
    dstep = float(Ll[1] - Ll[0])
    shift = abs(Lstar_low - Lstar_high)
    res = {
        'experiment': 'MT23_meep_inverse_crime', 'index': N, 'FCEN': FCEN,
        'res_low': RES_LOW, 'res_high': RES_HIGH, 'L_grid_step': round(dstep, 4),
        'Lstar_low': round(Lstar_low, 4), 'T_low_at_Lstar_low': round(float(Tl[i_low]), 4),
        'T_high_at_Lstar_low': round(T_high_at_lowopt, 4),
        'inverse_crime_gap': round(gap, 4),
        'Lstar_high': round(Lstar_high, 4), 'argmax_shift': round(shift, 4),
        'argmax_shift_in_steps': round(shift / dstep, 2),
        'exploitation_detected': bool(gap > 0.05 or shift > dstep),
        'sweep_low': [[round(float(a),4), round(float(b),4)] for a,b in zip(Ll, Tl)],
        'sweep_high': [[round(float(a),4), round(float(b),4)] for a,b in zip(Lh, Th)],
        'seconds': round(time.time()-t0, 1),
    }
    json.dump(res, open('mt23_results.json', 'w'), indent=2)
    print(json.dumps({k: res[k] for k in ('Lstar_low','T_low_at_Lstar_low','T_high_at_Lstar_low',
          'inverse_crime_gap','Lstar_high','argmax_shift','argmax_shift_in_steps','exploitation_detected','seconds')}, indent=2))

if __name__ == '__main__':
    main()
