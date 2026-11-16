# Office West engineering methods

This synthetic teaching case models a supply-air tree and a one-zone heat balance. Its calculations support concept comparison. Construction design requires verified project inputs, applicable standards and qualified review.

## A. Supply-air coordination

The AHU must deliver 270 L/s to the open office, 170 L/s to the meeting room, and 210 L/s to the studio. The flow demands are inputs. A depth-first traversal adds downstream flows from the leaves to the root, enforcing continuity at each junction. It gives 650 L/s at the root. Each segment has one upstream connection and is straight and orthogonal. This is a rooted tree with prescribed terminal flows. A looped network, fan curve intersection, leakage or predicted damper position would require additional equations and data.

For a round duct of inside diameter \(D\), area \(A=\pi D^2/4\), velocity \(v=Q/A\), and Reynolds number \(Re=\rho vD/\mu\). The inputs use air density \(\rho=1.2\) kg/m³, dynamic viscosity \(\mu=1.8\times10^{-5}\) Pa·s and roughness \(\varepsilon=0.09\) mm. The segment loss is

$$\Delta p = \left(f\frac{L}{D} + K\right)\frac{\rho v^2}{2}.$$

- \(L\) is centreline length in metres. \(f\) is the **Darcy** friction factor.
- For \(Re\leq 2300\), \(f=64/Re\). Above the transitional range, the explicit Swamee–Jain approximation is used. The model linearly blends the two expressions between 2300 and 4000.
- \(K\) represents the assumed local loss coefficient for a segment, referenced to that segment's velocity pressure. All coefficients in this case are synthetic. Real tee losses depend on flow split and reference area. Select fitting geometries and coefficients for the actual installation.
- The pressure budget is tested against the **largest sum on a root-to-terminal path**, including a 50 Pa fixed equipment allowance exactly once. Losses on parallel branches are not summed. Shaft/input power is estimated using \(Q\Delta p/\eta\) with a single assumed total efficiency \(\eta=0.62\). This is one operating point and does not predict annual electricity consumption.

Each circular duct and its 35 mm insulation have a conservative axis-aligned bounding box. A beam overlapping that envelope is flagged as a hard clash **candidate**. An additional 100 mm envelope marks clearance-only candidates. Rounded corners, fittings, supports, doors and site tolerances need higher-fidelity checks. The viewer colours the candidate red. IFC exports the bare duct mesh and records insulation thickness in the result properties.

For a fixed route, search all feasible combinations of 225, 280, 355 and 450 mm stock diameters. Reject any combination exceeding the velocity or critical-path pressure budget or flagged by the envelope checks. Minimise the proxy \(\sum_i \pi D_i L_i\), the developed sheet area of the straight segments. The minimum is exact within these finite candidates and the modelled constraints. The application provides two routes for comparison. It does not generate arbitrary routes or account for the lifecycle cost of fittings and fan energy.

| 85 Pa budget and 6 m/s limit | Hard clash candidates | Critical pressure | Result |
|---|---:|---:|---|
| Direct trunk, velocity-sized baseline | 1 | 82.8 Pa | Conflicts with beam |
| Beam bypass, velocity-sized baseline | 0 | 94.7 Pa | Exceeds pressure budget |
| Beam bypass, minimum sheet area | 0 | 82.9 Pa | Feasible with 18.23 m² and about 87 W |

## B. Meeting-room thermal response

At a prescribed meeting-room supply airflow of 170 L/s, take a lumped dry-bulb model:

$$C\dot T = U_A(T_o-T)+\rho c_p Q_s(T_s-T)+G.$$

\(C\) is effective heat capacity in J/K, \(U_A\) is envelope conductance in W/K, \(T_o\) is ambient outdoor temperature, \(T_s\) is supply-air temperature, \(Q_s\) is the fixed supply volumetric flow, \(c_p\) is air specific heat and \(G\) is internal sensible gain in watts. With constant inputs, let \(H=U_A+\rho c_p Q_s\), \(\tau=C/H\) and \(T_\infty=(U_AT_o+\rho c_pQ_sT_s+G)/H\). Then

$$T(t)=T_\infty+(T_0-T_\infty)e^{-t/\tau}.$$

For a numerical cross-check, backward Euler gives

$$T_{n+1}=T_\infty+\frac{T_n-T_\infty}{1+\Delta t/\tau}.$$

Here \(\Delta t\) is the time step. The method is first-order in time and stable for the scalar decay mode at any positive step. Reduce the step in the browser and compare maximum error at sample times. The default equilibrium is 27.73 °C and the 30-minute step error is 0.302 °C. The case excludes humidity, radiant exchange, solar gains, weather variation, control loops, occupant comfort and equipment sizing. It is a reproducible stepping stone to a detailed EnergyPlus zone or an OpenFOAM case.

## Scaling and verification

- With \(E\) segments, \(D\) stock sizes, \(O\) obstacle boxes and total root-to-terminal path length \(P\) measured in segment visits, precomputing the geometry/physics choices uses \(O(EDO)\) work. Exhaustive enumeration uses up to \(O(D^E(E+P))\) work. The sample bypass has only 16,384 assignments. The heat solver uses \(O(N)\) work and stores \(O(N)\) samples.
- Larger models can use a spatial index for envelope queries, and branch-and-bound using lower bounds on area and pressure. Independent scenario sets can be partitioned across CPU workers or dispatched to HPC when measurements justify it. Network communications and worker startup add overhead, so the included small case runs locally without worker infrastructure.
- Tests cover continuity, critical-path pressure accounting, feasible and infeasible search, hard and clearance-only envelopes, friction factor behaviour, and convergence against the analytic solution. The IFC example can be read back with IfcOpenShell, and duct and beam meshes can be tessellated independently of the browser.

## References

- [EPA EPANET 2.2 documentation](https://epanet22.readthedocs.io/en/latest/3_network_model.html) for Darcy–Weisbach and the Swamee–Jain approximation. EPANET's transitional implementation differs from the interpolation used here.
- [ASHRAE Duct Fitting Database](https://www.ashrae.org/technical-resources/bookstore/duct-fitting-database) for fitting-specific loss data in engineering work.
- [IfcOpenShell mesh geometry API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/add_mesh_representation/index.html) and [Bonsai IFC authoring](https://bonsaibim.org/).
- [EnergyPlus](https://energyplus.net/) and [OpenFOAM](https://www.openfoam.com/) for detailed energy and CFD workflows.
