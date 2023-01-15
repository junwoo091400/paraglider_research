import matplotlib.pyplot as plt
import numpy as np

import pfh.glidersim as gsim
from pfh.glidersim import orientation

import gpxpy

## Load real flight data
def get_real_flight_data():
    file_name = '2022-06-12_Flight_15_-_Jun_12,_2022_16_15_11.gpx' # Fronalpstock. Nice glide
    gpx_file = open(file_name, 'r')
    gpx_data = gpxpy.parse(gpx_file)

    len_tracks = len(gpx_data.tracks)
    len_segments = len(gpx_data.tracks[0].segments)
    len_points = len(gpx_data.tracks[0].segments[0].points)

    print(f"Tracks: {len_tracks} \nSegments: {len_segments} \nPoints: {len_points} \n")

    gpx_points = gpx_data.tracks[0].segments[0].points
    velocities = np.empty([len(gpx_points),2]) # Hor, Ver velocities

    for idx, point in enumerate(gpx_points):
        if point.speed != None:
            print('Speed:', point.speed)
        elif idx > 0:
            prev_point = gpx_points[idx-1]
            dt = point.time_difference(prev_point)
            l_xyz = point.distance_3d(prev_point)
            l_xy = point.distance_2d(prev_point)
            l_z = (l_xyz**2 - l_xy**2)**0.5

            v_xy = l_xy/dt
            v_z = l_z/dt
            # print('Calculated speed:', v_xy, v_z)

            if v_xy >= 6.0:
                # If under certain forward speed, assume it's a bad data (shouldn't be plotted)
                velocities[idx][0] = v_xy
                velocities[idx][1] = v_z
            else:
                velocities[idx][0] = None
                velocities[idx][1] = None

    return velocities

if __name__ == "__main__":
    print("\n-------------------------------------------------------------\n")

    use_6a = True
    use_6a = False  # Set to False to use Paraglider9a

    size = 'XS'

    wing = gsim.extras.wings.skywalk_mescal_6(size=size, verbose=True)

    if size == 'XS':
        harness = gsim.paraglider_harness.Spherical(
            mass=75, z_riser=0.5, S=0.55, CD=0.8, kappa_w=0.15
        )
    else:
        raise RuntimeError(f"Invalid Mescal 6 canopy size {size}")

    if use_6a:
        paraglider = gsim.paraglider.ParagliderSystemDynamics6a(wing, harness)
    else:
        paraglider = gsim.paraglider.ParagliderSystemDynamics9a(wing, harness)

    print("Computing the glider equilibrium state...\n")
    eq = paraglider.equilibrium_state()

    # Compute the residual acceleration at the given equilibrium state
    q_b2e = orientation.euler_to_quaternion(eq["Theta_b2e"])
    q_e2b = q_b2e * [1, -1, -1, -1]
    v_RM2e = orientation.quaternion_rotate(q_e2b, eq["v_RM2e"])

    if use_6a:
        a_RM2e, alpha_b2e, _ = paraglider.accelerations(
            v_RM2e=eq["v_RM2e"],
            omega_b2e=[0, 0, 0],
            g=orientation.quaternion_rotate(q_b2e, [0, 0, 9.8]),
            reference_solution=eq["reference_solution"],
        )
    else:
        a_RM2e, alpha_b2e, alpha_p2b, _ = paraglider.accelerations(
            v_RM2e=eq["v_RM2e"],
            omega_b2e=[0, 0, 0],
            omega_p2e=[0, 0, 0],
            Theta_p2b=eq["Theta_p2b"],
            g=orientation.quaternion_rotate(q_b2e, [0, 0, 9.8]),
            reference_solution=eq["reference_solution"],
        )

    print("Equilibrium state:")
    print(f"  alpha_b:     {np.rad2deg(eq['alpha_b']):>6.3f} [deg]")
    print(f"  theta_b2e:   {np.rad2deg(eq['Theta_b2e'][1]):>6.3f} [deg]")
    if use_6a is False:
        theta_p2e = eq["Theta_p2b"][1] + eq["Theta_b2e"][1]
        print(f"  theta_p2e:   {np.rad2deg(theta_p2e):>6.3f} [deg]")
    print(f"  Glide angle: {np.rad2deg(eq['gamma_b']):>6.3f} [deg]")
    print(f"  Glide ratio: {eq['glide_ratio']:>6.3f}")
    print(f"  Glide speed: {np.linalg.norm(v_RM2e):>6.3f}")
    print()
    print("Verify accelerations at equilibrium:")
    print(f"  a_RM2e:      {a_RM2e.round(4)}")
    print(f"  alpha_b2e:   {np.rad2deg(alpha_b2e).round(4)}")
    if use_6a is False:
        print(f"  alpha_p2b:   {np.rad2deg(alpha_p2b).round(4)}")

    print("\n<pausing before polar curves>\n")

    accelerating, braking = gsim.extras.compute_polars.compute_polar_data(
        paraglider,
    )

    # Just
    # gsim.extras.compute_polars.plot_wing_coefficients(paraglider)
    v_RM2e_a = accelerating["v_RM2e"]
    v_RM2e_b = braking["v_RM2e"]

    # -----------------------------------------------------------------------
    # Plot the curves
    fig = plt.figure()
    fig.suptitle('Mescal 6 {} Characteristics vs Real Data'.format(size))

    # https://matplotlib.org/stable/api/markers_api.html#module-matplotlib.markers
    MARKER = '+'
    # https://matplotlib.org/stable/gallery/color/named_colors.html
    COLOR = 'royalblue'

    # Raw velocities
    velocities = get_real_flight_data()

    # Raw glide ratios
    glide_ratios = np.divide(velocities[:, 0], velocities[:, 1])
    SANE_GLIDE_RATIO_CLIP = 10.0
    glide_ratios[glide_ratios > SANE_GLIDE_RATIO_CLIP] = np.nan # Remove datapoints above this glide ratio
    
    glide_ratios_clipped = glide_ratios
    # np.clip(glide_ratios, 0.0, SANE_GLIDE_RATIO_CLIP) # Clip impossible glide ratios (not good to plot)

    # breakpoint()

    # Vertical versus horizontal airspeed
    polar_plot = fig.add_subplot(1, 2, 1) # Main
    polar_plot.plot(v_RM2e_a.T[0], v_RM2e_a.T[2], "g")
    polar_plot.plot(v_RM2e_b.T[0], v_RM2e_b.T[2], "r")

    polar_plot.set_xlabel("Horizontal airspeed [m/s]")
    polar_plot.set_ylabel("sink rate [m/s]")
    polar_plot.grid(which="both")
    polar_plot.minorticks_on()

    x_lims = polar_plot.get_xlim()
    y_lims = polar_plot.get_ylim()

    # breakpoint()

    polar_plot.scatter(velocities[:, 0], velocities[:, 1], c=COLOR, marker=MARKER)
    
    polar_plot.set_xlim(x_lims)
    # polar_plot.set_xlim([np.min(v_RM2e_b.T[0]), np.max(v_RM2e_a.T[0])]) # Set X-axis to theoretical ratio range
    # polar_plot.set_ylim([np.nanmin(velocities[:, 1]), np.nanmax(velocities[:, 1])]) # Set Y-axis to real flight ratio

    polar_plot.invert_yaxis()

    # Glide ratio
    glide_ratio_plot = fig.add_subplot(1, 2, 2, sharex=polar_plot) # Lower Right. Share axis with polar plot (V forward)
    glide_ratio_plot.plot(v_RM2e_a.T[0], accelerating["glide_ratio"], "g")
    glide_ratio_plot.plot(v_RM2e_b.T[0], braking["glide_ratio"], "r")

    glide_ratio_plot.scatter(velocities[:, 0], glide_ratios_clipped, c=COLOR, marker=MARKER)
    
    # glide_ratio_plot.set_xlim(0, 25)
    
    glide_ratio_plot.set_xlabel("Horizontal airspeed [m/s]")
    glide_ratio_plot.set_ylabel("Glide ratio")
    glide_ratio_plot.grid()

    fig.tight_layout() # Make sure graphs don't overlap
    plt.show()

    # breakpoint()