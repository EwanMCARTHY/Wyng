from core.wing import Wing
from core.airfoil import Airfoil, AirfoilDatabase

class Drone:
    def __init__(self, mass: float, v_stall: float, v_cruise: float, airfoil: Airfoil,
                 aspect_ratio: float = 8.0, taper_ratio: float = 0.6,
                 sweep_angle: float = 0.0, dihedral_angle: float = 0.0,
                 tail_arm: float = 1.0, vh: float = 0.5, vv: float = 0.04,
                 nose_length: float = 0.2, tail_type: str = "Classique",
                 h_tail_sweep: float = 0.0, wing_shape: str = "Trapézoïdale",
                 washout: float = 0.0, kink_pos: float = 0.45, kink_angle: float = -30.0,
                 has_winglets: bool = False,
                 m_motor: float = 0.2, x_motor: float = -0.1,
                 m_batt: float = 0.5, x_batt: float = 0.0,
                 m_payload: float = 0.3, x_payload: float = 0.1,
                 eta_prop: float = 0.70, eta_motor: float = 0.80):
        
        self.mass = mass
        self.g = 9.81
        self.rho = 1.225
        self.v_stall = v_stall
        self.v_cruise = v_cruise
        self.airfoil = airfoil
        
        self.tail_arm = tail_arm
        self.vh = vh
        self.vv = vv
        self.nose_length = nose_length
        self.tail_type = tail_type
        self.h_tail_sweep = h_tail_sweep
        self.wing_shape = wing_shape
        
        self.m_motor = m_motor
        self.x_motor = x_motor
        self.m_batt = m_batt
        self.x_batt = x_batt
        self.m_payload = m_payload
        self.x_payload = x_payload
        
        self.eta_prop = eta_prop
        self.eta_motor = eta_motor
        
        self.required_surface = self._calculate_required_surface()
        
        self.main_wing = Wing(
            surface=self.required_surface, 
            aspect_ratio=aspect_ratio, taper_ratio=taper_ratio,
            sweep_angle_deg=sweep_angle, dihedral_angle_deg=dihedral_angle,
            wing_shape=wing_shape, washout_deg=washout,
            kink_pos_ratio=kink_pos, kink_angle_deg=kink_angle,
            has_winglets=has_winglets
        )
        
        self._calculate_tails()
        self._calculate_cg_and_stability()
        self._calculate_actual_cg()
        self._calculate_incidence()
        
        self.cz_cruise = 0.0
        self.cd_total = 0.0
        self.finesse = 0.0
        self.power_required = 0.0
        self.thrust_req_g = 0.0
        self.elec_power_req = 0.0
        
        self._calculate_aerodynamics()

    def _calculate_required_surface(self) -> float:
        weight = self.mass * self.g
        dynamic_pressure_stall = 0.5 * self.rho * (self.v_stall ** 2)
        return weight / (dynamic_pressure_stall * self.airfoil.cl_max)

    def _calculate_tails(self):
        import math
        if self.tail_type == "Aile Volante":
            self.h_tail = None
            self.v_tail = None
            self.v_tail_obj = None
            self.v_angle = 0.0
            return

        sh_surface = (self.vh * self.main_wing.surface * self.main_wing.mean_aerodynamic_chord) / self.tail_arm
        sv_surface = (self.vv * self.main_wing.surface * self.main_wing.span) / self.tail_arm

        if self.tail_type in ["Classique", "Empennage en T"]:
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=0.7, sweep_angle_deg=self.h_tail_sweep)
            self.v_tail = Wing(surface=sv_surface, aspect_ratio=1.5, taper_ratio=0.8)
            self.v_angle = 0.0
            
        elif self.tail_type == "Empennage en V":
            vtail_surface = sh_surface + sv_surface
            self.v_angle = math.degrees(math.atan(math.sqrt(sv_surface / sh_surface)))
            self.v_tail_obj = Wing(surface=vtail_surface, aspect_ratio=4.0, taper_ratio=0.7, sweep_angle_deg=self.h_tail_sweep)
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=0.7, sweep_angle_deg=self.h_tail_sweep)
            self.v_tail = None
    
    def _calculate_cg_and_stability(self, static_margin: float = 0.15):
        """Calcule le foyer global et la position cible du CG."""
        
        # Si c'est une aile volante, le foyer global EST le foyer de l'aile
        if self.tail_type == "Aile Volante" or self.h_tail is None:
            self.neutral_point_x = self.main_wing.aerodynamic_center_x
        else:
            # Calcul barycentrique classique avec empennage
            h_tail_ac_x = self.tail_arm + self.h_tail.aerodynamic_center_x
            numerator = (self.main_wing.aerodynamic_center_x * self.main_wing.surface) + \
                        (h_tail_ac_x * self.h_tail.surface)
            denominator = self.main_wing.surface + self.h_tail.surface
            self.neutral_point_x = numerator / denominator
        
        # Marge statique (Le CG devant le Foyer)
        margin_distance = static_margin * self.main_wing.mean_aerodynamic_chord
        self.cg_x = self.neutral_point_x - margin_distance
    
    def _calculate_incidence(self):
        """Calcule l'angle de calage de l'aile pour minimiser la traînée en croisière."""
        weight = self.mass * self.g
        dynamic_pressure_cruise = 0.5 * self.rho * (self.v_cruise ** 2)
        
        # Quel Cz faut-il pour voler en palier à la vitesse de croisière ?
        cz_cruise = weight / (dynamic_pressure_cruise * self.main_wing.surface)
        
        # Pente de portance standard (~0.11 par degré) et prise en compte du alpha_0 du profil
        self.wing_incidence = (cz_cruise / 0.11) + self.airfoil.alpha_0
    
    def _calculate_aerodynamics(self):
        import math
        
        dynamic_pressure_cruise = 0.5 * self.rho * (self.v_cruise ** 2)
        self.cz_cruise = (self.mass * self.g) / (dynamic_pressure_cruise * self.main_wing.surface)
        
        e = 0.85
        if self.wing_shape == "Delta":
            e = 0.70
        elif self.wing_shape == "Lambda":
            e = 0.88
            
        if self.main_wing.has_winglets:
            e += 0.05
            
        if e > 0.98: e = 0.98 
        
        cdi = (self.cz_cruise ** 2) / (math.pi * e * self.main_wing.aspect_ratio)
        
        integration_penalty = 0.01 
        if self.tail_type == "Aile Volante":
            integration_penalty = 0.003
            
        cd0 = self.airfoil.cd_0 + integration_penalty
        
        self.cd_total = cd0 + cdi
        self.finesse = self.cz_cruise / self.cd_total if self.cd_total > 0 else 0
        
        drag_force = dynamic_pressure_cruise * self.main_wing.surface * self.cd_total
        self.power_required = drag_force * self.v_cruise
        
        self.thrust_req_g = (drag_force / self.g) * 1000.0
        self.elec_power_req = self.power_required / (self.eta_prop * self.eta_motor)
    
    def _calculate_actual_cg(self):
        """Calcule la position réelle du Centre de Gravité selon la répartition des masses."""
        # La masse restante correspond à la structure (fuselage + ailes)
        self.m_structure = self.mass - (self.m_motor + self.m_batt + self.m_payload)
        
        # On estime que le centre de gravité de la structure vide est proche du foyer aérodynamique
        x_structure = self.neutral_point_x
        
        # Formule du barycentre
        sum_moments = (self.m_motor * self.x_motor) + \
                      (self.m_batt * self.x_batt) + \
                      (self.m_payload * self.x_payload) + \
                      (self.m_structure * x_structure)
                      
        self.actual_cg_x = sum_moments / self.mass
        
        # Calcul de la marge statique réelle (en % de la MAC)
        # MS > 0 = Stable (CG devant le foyer). MS < 0 = Instable.
        self.actual_static_margin = ((self.neutral_point_x - self.actual_cg_x) / self.main_wing.mean_aerodynamic_chord) * 100


# --- Test rapide ---
if __name__ == "__main__":
    db = AirfoilDatabase()
    selected_airfoil = db.get_airfoil("Selig 1223")
    
    if selected_airfoil:
        # On ajoute un bras de levier de 0.8 mètres (distance entre l'aile et la queue)
        my_drone = Drone(mass=2.5, v_stall=10.0, airfoil=selected_airfoil, aspect_ratio=10, tail_arm=0.8)
        
        print(f"--- Dimensionnement Wyng : Drone de {my_drone.mass} kg ---")
        print(f"Surface alaire requise : {round(my_drone.required_surface, 3)} m2")
        
        print("\n--- Empennage Horizontal ---")
        for key, value in my_drone.h_tail.get_summary().items():
            print(f"{key}: {value}")
            
        print("\n--- Empennage Vertical (Dérive) ---")
        for key, value in my_drone.v_tail.get_summary().items():
            print(f"{key}: {value}")