import math
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

class PlotManager:
    def __init__(self):
        self.figure_3d = Figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.view_needs_reset = True
        self.canvas_3d.mpl_connect('scroll_event', self._on_scroll)
        
        self.figure_vn = Figure()
        self.canvas_vn = FigureCanvas(self.figure_vn)
        self.ax_vn = self.figure_vn.add_subplot(111)
        
        self.figure_polars = Figure()
        self.canvas_polars = FigureCanvas(self.figure_polars)
        
        self.figure_struct = Figure()
        self.canvas_struct = FigureCanvas(self.figure_struct)
        
        self.figure_opti = Figure()
        self.canvas_opti = FigureCanvas(self.figure_opti)
        self.ax_opti = self.figure_opti.add_subplot(111)
        self.clear_opti_plot()

    def _on_scroll(self, event):
        if not hasattr(self, 'ax') or event.inaxes != self.ax: return
        scale_factor = 0.9 if event.button == 'up' else 1.1
        xlim = self.ax.get_xlim3d()
        ylim = self.ax.get_ylim3d()
        zlim = self.ax.get_zlim3d()
        x_center, y_center, z_center = sum(xlim)/2, sum(ylim)/2, sum(zlim)/2
        x_range, y_range, z_range = (xlim[1]-xlim[0])*scale_factor/2, (ylim[1]-ylim[0])*scale_factor/2, (zlim[1]-zlim[0])*scale_factor/2
        self.ax.set_xlim3d([x_center - x_range, x_center + x_range])
        self.ax.set_ylim3d([y_center - y_range, y_center + y_range])
        self.ax.set_zlim3d([z_center - z_range, z_center + z_range])
        self.canvas_3d.draw()

    def reset_3d_view(self):
        self.view_needs_reset = True

    def clear_opti_plot(self):
        self.ax_opti.clear()
        self.ax_opti.set_title("Convergence de l'Algorithme")
        self.ax_opti.set_xlabel("Générations")
        self.ax_opti.set_ylabel("Score (Fitness)")
        self.ax_opti.grid(True, linestyle=':')
        self.canvas_opti.draw()

    def update_opti_plot(self, best_history, avg_history):
        self.ax_opti.clear()
        self.ax_opti.set_title("Convergence de l'Algorithme Génétique")
        self.ax_opti.set_xlabel("Générations")
        self.ax_opti.set_ylabel("Score (Fitness)")
        self.ax_opti.grid(True, linestyle=':')
        self.ax_opti.plot(best_history, 'b-', linewidth=2, label="Meilleur individu")
        self.ax_opti.plot(avg_history, 'g--', linewidth=1.5, label="Moyenne population")
        self.ax_opti.legend(loc="lower right")
        self.canvas_opti.draw()

    def draw_drone(self, drone, force_reset=False):
        if not hasattr(self, 'ax'):
            self.ax = self.figure_3d.add_subplot(111, projection='3d')
            self.view_needs_reset = True
            
        if self.view_needs_reset or force_reset:
            saved_elev, saved_azim, saved_xlim, saved_ylim, saved_zlim = None, None, None, None, None
        else:
            saved_elev, saved_azim = self.ax.elev, self.ax.azim
            saved_xlim, saved_ylim, saved_zlim = self.ax.get_xlim(), self.ax.get_ylim(), self.ax.get_zlim()
            
        self.ax.clear()
        self.ax.set_title("Visualisation 3D du Projet")
        self.ax.set_xlabel("Axe Longitudinal X (m)")
        self.ax.set_ylabel("Envergure Y (m)")
        self.ax.set_zlabel("Hauteur Z (m)")
        self.ax.set_box_aspect((1, 1, 1))
        
        def add_symmetric_poly(x_coords, y_coords, z_coords, color, alpha=0.6):
            verts_right = list(zip(x_coords, y_coords, z_coords))
            self.ax.add_collection3d(Poly3DCollection([verts_right], facecolors=color, edgecolors='black', alpha=alpha))
            verts_left = list(zip(x_coords, [-y for y in y_coords], z_coords))
            self.ax.add_collection3d(Poly3DCollection([verts_left], facecolors=color, edgecolors='black', alpha=alpha))

        y_coords, x_coords = drone.main_wing.outline_y, drone.main_wing.outline_x
        z_coords = [y * math.tan(drone.main_wing.dihedral_angle_rad) for y in y_coords]
        add_symmetric_poly(x_coords, y_coords, z_coords, 'skyblue')

        if drone.main_wing.has_winglets:
            b2 = drone.main_wing.span / 2
            tip_x, tip_c, tip_z = drone.main_wing.tip_offset_x, drone.main_wing.tip_chord, b2 * math.tan(drone.main_wing.dihedral_angle_rad)
            w_x, w_y, w_z = [tip_x, tip_x + tip_c, tip_x + tip_c * 0.5, tip_x], [b2, b2, b2, b2], [tip_z, tip_z, tip_z + b2 * 0.15, tip_z + b2 * 0.15]
            add_symmetric_poly(w_x, w_y, w_z, 'darkblue', 0.8)

        if drone.tail_type != "Aile Volante":
            arm, hb2 = drone.tail_arm, drone.h_tail.span / 2
            hcr, hct, hoff = drone.h_tail.root_chord, drone.h_tail.tip_chord, drone.h_tail.tip_offset_x
            
            if drone.tail_type in ["Classique", "Empennage en T"]:
                z_htail = 0 if drone.tail_type == "Classique" else drone.v_tail.span
                hx, hy, hz = [arm, arm + hoff, arm + hoff + hct, arm + hcr], [0, hb2, hb2, 0], [z_htail, z_htail, z_htail, z_htail]
                add_symmetric_poly(hx, hy, hz, 'lightcoral')
                vx = [arm, arm + drone.v_tail.tip_offset_x, arm + drone.v_tail.tip_offset_x + drone.v_tail.tip_chord, arm + drone.v_tail.root_chord]
                vy, vz = [0, 0, 0, 0], [0, drone.v_tail.span, drone.v_tail.span, 0]
                self.ax.add_collection3d(Poly3DCollection([list(zip(vx, vy, vz))], facecolors='darkred', edgecolors='black', alpha=0.6))
                
            elif drone.tail_type == "Empennage en V":
                v_span, v_angle_rad = drone.v_tail_obj.span / 2, math.radians(drone.v_angle)
                z_tip, y_tip = v_span * math.sin(v_angle_rad), v_span * math.cos(v_angle_rad)
                vcr, vct, voff = drone.v_tail_obj.root_chord, drone.v_tail_obj.tip_chord, drone.v_tail_obj.tip_offset_x
                vx, vy, vz = [arm, arm + voff, arm + voff + vct, arm + vcr], [0, y_tip, y_tip, 0], [0, z_tip, z_tip, 0]
                add_symmetric_poly(vx, vy, vz, 'mediumorchid')

        if drone.num_motors == 1:
            self.ax.scatter([drone.x_motor], [0], [0], color='orange', s=40, label='Moteur')
        else:
            z_m = drone.y_motor * math.tan(drone.main_wing.dihedral_angle_rad)
            self.ax.scatter([drone.x_motor, drone.x_motor], [drone.y_motor, -drone.y_motor], [z_m, z_m], color='orange', s=40, label='Moteurs')
            
        self.ax.scatter([drone.x_batt], [0], [0], color='green', s=40, label='Batterie')
        self.ax.scatter([drone.x_payload], [0], [0], color='cyan', s=40, label='Charge U.')
        self.ax.scatter([drone.neutral_point_x], [0], [0], color='blue', marker='x', s=60, label='Foyer')
        self.ax.scatter([drone.cg_x], [0], [0], color='black', marker='o', s=40, label='CG Cible')
        self.ax.scatter([drone.actual_cg_x], [0], [0], color='red', marker='+', s=100, label='CG Réel')

        end_x = drone.tail_arm + (drone.h_tail.root_chord if drone.tail_type != "Aile Volante" else 0)
        self.ax.plot([-drone.nose_length, end_x], [0, 0], [0, 0], color='black', linewidth=1, linestyle='-.')

        if saved_xlim is not None and saved_ylim is not None and saved_zlim is not None:
            self.ax.set_xlim(saved_xlim); self.ax.set_ylim(saved_ylim); self.ax.set_zlim(saved_zlim)
        else:
            all_x, all_y, all_z = [-drone.nose_length, end_x, drone.main_wing.root_chord], [-drone.main_wing.span/2, drone.main_wing.span/2], [-0.2, drone.main_wing.tip_offset_z + 0.3]
            max_range = max(max(all_x)-min(all_x), max(all_y)-min(all_y)) / 2.0
            mid_x, mid_y, mid_z = (max(all_x) + min(all_x)) * 0.5, (max(all_y) + min(all_y)) * 0.5, (max(all_z) + min(all_z)) * 0.5
            self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
            self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

        if saved_elev is not None and saved_azim is not None:
            self.ax.view_init(elev=saved_elev, azim=saved_azim)
        else:
            self.ax.view_init(elev=30, azim=-60)

        self.view_needs_reset = False
        self.ax.legend(loc='upper right', fontsize='x-small')
        self.canvas_3d.draw()

    def draw_vn(self, drone):
        self.ax_vn.clear()
        v_list, n_pos, n_neg, v_s, v_a, v_ne, n_max, n_min = drone.get_vn_data()
        self.ax_vn.plot(v_list, n_pos, color='blue', linewidth=2, label="Limite Positive (+5g)")
        self.ax_vn.plot(v_list, n_neg, color='red', linewidth=2, label="Limite Négative (-2g)")
        self.ax_vn.plot([v_ne, v_ne], [n_min, n_max], color='black', linewidth=2, linestyle='--', label=f"VNE ({v_ne:.1f} m/s)")
        self.ax_vn.plot([v_a, v_a], [0, n_max], color='green', linestyle=':', label=f"Va ({v_a:.1f} m/s)")
        self.ax_vn.plot([v_s, v_s], [0, 1], color='orange', linestyle=':', label=f"Vs ({v_s:.1f} m/s)")
        self.ax_vn.axhline(0, color='black', linewidth=1)
        self.ax_vn.axhline(1, color='gray', linewidth=1, linestyle=':')
        self.ax_vn.set_title("Diagramme V-n (Enveloppe de vol)")
        self.ax_vn.set_xlabel("Vitesse V (m/s)")
        self.ax_vn.set_ylabel("Facteur de charge n (g)")
        self.ax_vn.grid(True, linestyle='--')
        self.ax_vn.legend(loc='lower left', fontsize='small')
        self.ax_vn.fill_between(v_list, n_neg, n_pos, color='green', alpha=0.1)
        self.canvas_vn.draw()

    def draw_polars(self, drone):
        self.figure_polars.clear()
        ax1, ax2, ax3 = self.figure_polars.add_subplot(131), self.figure_polars.add_subplot(132), self.figure_polars.add_subplot(133)
        alphas, cz_list, cd_list, finesse_list = drone.get_polar_data()
        
        ax1.plot(alphas, cz_list, 'b-', linewidth=2)
        ax1.axhline(0, color='black', linewidth=0.8); ax1.axvline(0, color='black', linewidth=0.8)
        ax1.set_title("Portance (Cz) vs Angle (α)"); ax1.set_xlabel("Angle d'attaque α (°)"); ax1.set_ylabel("Cz")
        ax1.grid(True, linestyle=':')
        
        ax2.plot(cd_list, cz_list, 'r-', linewidth=2)
        ax2.set_title("Polaire (Cz vs Cx)"); ax2.set_xlabel("Traînée Cx"); ax2.set_ylabel("Portance Cz")
        ax2.grid(True, linestyle=':')
        
        ax3.plot(alphas, finesse_list, 'g-', linewidth=2)
        ax3.set_title("Finesse (L/D) vs Angle (α)"); ax3.set_xlabel("Angle d'attaque α (°)"); ax3.set_ylabel("Finesse")
        ax3.grid(True, linestyle=':')
        self.figure_polars.subplots_adjust(wspace=0.35, bottom=0.15)
        self.canvas_polars.draw()

    def draw_structure(self, drone):
        self.figure_struct.clear()
        ax1, ax2, ax3 = self.figure_struct.add_subplot(131), self.figure_struct.add_subplot(132), self.figure_struct.add_subplot(133)
        y_vals, l_dist, v_dist, m_dist, max_shear, max_moment = drone.get_structural_data()
        
        ax1.plot(y_vals, l_dist, 'b-', linewidth=2)
        ax1.fill_between(y_vals, 0, l_dist, color='blue', alpha=0.1)
        ax1.set_title("Répartition de Portance (Schrenk)"); ax1.set_xlabel("Demi-envergure y (m)"); ax1.set_ylabel("L' (N/m)")
        ax1.grid(True, linestyle=':')
        
        ax2.plot(y_vals, v_dist, 'r-', linewidth=2)
        ax2.fill_between(y_vals, 0, v_dist, color='red', alpha=0.1)
        ax2.set_title(f"Effort Tranchant (Max: {max_shear:.0f} N)"); ax2.set_xlabel("Demi-envergure y (m)"); ax2.set_ylabel("V (N)")
        ax2.grid(True, linestyle=':')
        
        ax3.plot(y_vals, m_dist, 'g-', linewidth=2)
        ax3.fill_between(y_vals, 0, m_dist, color='green', alpha=0.1)
        ax3.set_title(f"Moment Fléchissant (Max: {max_moment:.1f} N.m)"); ax3.set_xlabel("Demi-envergure y (m)"); ax3.set_ylabel("M (N.m)")
        ax3.grid(True, linestyle=':')
        self.figure_struct.subplots_adjust(wspace=0.35, bottom=0.15)
        self.canvas_struct.draw()