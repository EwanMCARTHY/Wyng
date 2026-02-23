import math
from core.wing import Wing
from core.airfoil import Airfoil

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
                 num_motors: int = 1, y_motor: float = 0.0,
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
        self.num_motors = num_motors
        self.y_motor = y_motor
        
        self.m_batt = m_batt
        self.x_batt = x_batt
        self.m_payload = m_payload
        self.x_payload = x_payload
        
        self.eta_prop = eta_prop
        self.eta_motor = eta_motor
        
        self.n_max_struct = 5.0
        self.n_min_struct = -2.0
        self.oswald_e = 0.85
        
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

    def _calculate_cg_and_stability(self):
        static_margin_target = 0.15 
        if self.tail_type == "Aile Volante":
            self.neutral_point_x = self.main_wing.aerodynamic_center_x
        else:
            mac_wing = self.main_wing.mean_aerodynamic_chord
            area_wing = self.main_wing.surface
            x_ac_wing = self.main_wing.aerodynamic_center_x
            
            area_tail = self.h_tail.surface
            x_ac_tail = self.tail_arm + self.h_tail.aerodynamic_center_x
            
            self.neutral_point_x = (x_ac_wing * area_wing + x_ac_tail * area_tail) / (area_wing + area_tail)

        self.cg_x = self.neutral_point_x - (static_margin_target * self.main_wing.mean_aerodynamic_chord)

    def _calculate_incidence(self):
        weight = self.mass * self.g
        dynamic_pressure_cruise = 0.5 * self.rho * (self.v_cruise ** 2)
        cl_required = weight / (dynamic_pressure_cruise * self.main_wing.surface)
        lift_slope = 0.1 
        
        cl_0 = getattr(self.airfoil, 'cl_0', 0.2)
        self.wing_incidence = (cl_required - cl_0) / lift_slope

    def _calculate_actual_cg(self):
        self.total_motor_mass = self.num_motors * self.m_motor
        self.m_structure = self.mass - (self.total_motor_mass + self.m_batt + self.m_payload)
        
        x_structure = self.neutral_point_x
        
        sum_moments = (self.total_motor_mass * self.x_motor) + \
                      (self.m_batt * self.x_batt) + \
                      (self.m_payload * self.x_payload) + \
                      (self.m_structure * x_structure)
                      
        self.actual_cg_x = sum_moments / self.mass
        
        self.actual_static_margin = ((self.neutral_point_x - self.actual_cg_x) / self.main_wing.mean_aerodynamic_chord) * 100

    def _calculate_aerodynamics(self):
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
        self.oswald_e = e
        
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

    def get_vn_data(self):
        cl_max = self.airfoil.cl_max
        cl_min = -0.5 * cl_max
        w = self.mass * self.g
        
        v_s = math.sqrt((2 * w) / (self.rho * self.main_wing.surface * cl_max))
        v_a = v_s * math.sqrt(self.n_max_struct)
        v_ne = self.v_cruise * 2.5 
        
        v_list = [v for v in range(0, int(v_ne) + 5)]
        n_pos = []
        n_neg = []
        
        for v in v_list:
            q = 0.5 * self.rho * (v**2)
            n_p = (q * self.main_wing.surface * cl_max) / w
            n_n = (q * self.main_wing.surface * cl_min) / w
            
            n_pos.append(min(n_p, self.n_max_struct))
            n_neg.append(max(n_n, self.n_min_struct))
            
        return v_list, n_pos, n_neg, v_s, v_a, v_ne, self.n_max_struct, self.n_min_struct

    def get_polar_data(self):
        cl_0 = getattr(self.airfoil, 'cl_0', 0.2)
        cl_max = self.airfoil.cl_max
        lift_slope = 0.1
        
        integration_penalty = 0.01 
        if self.tail_type == "Aile Volante":
            integration_penalty = 0.003
        cd0 = self.airfoil.cd_0 + integration_penalty
        
        alphas = list(range(-5, 21))
        cz_list = []
        cd_list = []
        finesse_list = []
        
        alpha_stall = (cl_max - cl_0) / lift_slope
        
        for alpha in alphas:
            cz = cl_0 + lift_slope * alpha
            
            if cz > cl_max:
                cz = cl_max - 0.05 * (alpha - alpha_stall)
            elif cz < -cl_max * 0.6:
                cz = -cl_max * 0.6
                
            cdi = (cz ** 2) / (math.pi * self.oswald_e * self.main_wing.aspect_ratio)
            
            if alpha > alpha_stall:
                cd = cd0 + cdi + 0.05 * (alpha - alpha_stall)**2
            else:
                cd = cd0 + cdi
                
            cz_list.append(cz)
            cd_list.append(cd)
            
            finesse = cz / cd if cd > 0 else 0
            finesse_list.append(finesse)
            
        return alphas, cz_list, cd_list, finesse_list