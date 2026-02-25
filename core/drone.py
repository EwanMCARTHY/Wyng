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
                 htail_shape: str = "Trapézoïdale",
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
        self.htail_shape = htail_shape
        
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
        
        wing_taper = 1.0 if wing_shape == "Droite" else (0.0 if wing_shape == "Delta" else taper_ratio)
        actual_wing_shape = "Trapézoïdale" if wing_shape == "Droite" else wing_shape
        
        self.main_wing = Wing(
            surface=self.required_surface, 
            aspect_ratio=aspect_ratio, taper_ratio=wing_taper,
            sweep_angle_deg=sweep_angle, dihedral_angle_deg=dihedral_angle,
            wing_shape=actual_wing_shape, washout_deg=washout,
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

        htail_taper = 1.0 if self.htail_shape == "Droite" else (0.0 if self.htail_shape == "Delta" else 0.7)
        actual_htail_shape = "Trapézoïdale" if self.htail_shape == "Droite" else self.htail_shape

        if self.tail_type in ["Classique", "Empennage en T"]:
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=htail_taper, sweep_angle_deg=self.h_tail_sweep, wing_shape=actual_htail_shape)
            self.v_tail = Wing(surface=sv_surface, aspect_ratio=1.5, taper_ratio=0.8)
            self.v_angle = 0.0
            
        elif self.tail_type == "Empennage en V":
            vtail_surface = sh_surface + sv_surface
            self.v_angle = math.degrees(math.atan(math.sqrt(sv_surface / sh_surface)))
            self.v_tail_obj = Wing(surface=vtail_surface, aspect_ratio=4.0, taper_ratio=htail_taper, sweep_angle_deg=self.h_tail_sweep, wing_shape=actual_htail_shape)
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=htail_taper, sweep_angle_deg=self.h_tail_sweep, wing_shape=actual_htail_shape)
            self.v_tail = None

    def _calculate_cg_and_stability(self):
        static_margin_target = 0.15 
        if self.tail_type == "Aile Volante":
            self.neutral_point_x = self.main_wing.aerodynamic_center_x
        else:
            # 1. Caractéristiques aérodynamiques de l'aile principale
            mac_wing = self.main_wing.mean_aerodynamic_chord
            area_wing = self.main_wing.surface
            x_ac_wing = self.main_wing.aerodynamic_center_x
            AR_w = self.main_wing.aspect_ratio
            sweep_w_rad = self.main_wing.sweep_angle_rad
            
            # Pente de portance 3D de l'aile (Diederich, en 1/rad)
            a_w = (2 * math.pi * AR_w) / (2 + math.sqrt(4 + (AR_w**2 / math.cos(sweep_w_rad)**2)))
            
            # 2. Caractéristiques aérodynamiques de l'empennage
            area_tail = self.h_tail.surface
            x_ac_tail = self.tail_arm + self.h_tail.aerodynamic_center_x
            AR_t = self.h_tail.aspect_ratio
            sweep_t_rad = self.h_tail.sweep_angle_rad
            
            # Pente de portance 3D de l'empennage (Diederich, en 1/rad)
            a_t = (2 * math.pi * AR_t) / (2 + math.sqrt(4 + (AR_t**2 / math.cos(sweep_t_rad)**2)))
            
            # 3. Calcul des interactions aérodynamiques de sillage
            # Estimation du downwash (déflexion du sillage par l'aile)
            deps_dalpha = (2 * a_w) / (math.pi * AR_w)
            
            # Ratio de pression dynamique (eta_t)
            # Un empennage en T échappe en grande partie au sillage freiné de l'aile
            eta_t = 1.0 if self.tail_type == "Empennage en T" else 0.9
            
            # Facteur d'efficacité globale de l'empennage
            tail_efficiency = (a_t / a_w) * eta_t * (1.0 - deps_dalpha)
            
            # 4. Nouveau calcul du Point Neutre (Foyer global pondéré aérodynamiquement)
            self.neutral_point_x = (x_ac_wing * area_wing + x_ac_tail * area_tail * tail_efficiency) / (area_wing + area_tail * tail_efficiency)

        # Le centre de gravité idéal cible est déduit à partir du nouveau point neutre
        self.cg_x = self.neutral_point_x - (static_margin_target * self.main_wing.mean_aerodynamic_chord)

    def _calculate_incidence(self):
        weight = self.mass * self.g
        dynamic_pressure_cruise = 0.5 * self.rho * (self.v_cruise ** 2)
        cl_required = weight / (dynamic_pressure_cruise * self.main_wing.surface)
        
        # Calcul de la pente de portance 3D (Théorie de Diederich pour voilure avec flèche)
        # a_0 est la pente 2D théorique d'un profil mince (environ 2*pi par radian)
        a_0 = 2 * math.pi
        AR = self.main_wing.aspect_ratio
        sweep_rad = self.main_wing.sweep_angle_rad
        
        # Formule de Diederich (résultat en 1/radian)
        # Elle prend en compte la perte d'efficacité due à l'allongement fini et à la flèche
        lift_slope_rad = (a_0 * AR) / (2 + math.sqrt(4 + (AR**2 / math.cos(sweep_rad)**2)))
        
        # Conversion de la pente en 1/degré pour s'adapter aux repères de l'application
        lift_slope_deg = math.radians(lift_slope_rad)
        
        cl_0 = getattr(self.airfoil, 'cl_0', 0.2)
        
        # L'incidence de croisière (en degrés) est désormais calculée sur le modèle 3D
        self.wing_incidence = (cl_required - cl_0) / lift_slope_deg

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
        
        # 1. Calcul dynamique du coefficient d'Oswald (e) - Formules de Raymer
        AR = self.main_wing.aspect_ratio
        sweep_deg = abs(self.main_wing.sweep_angle_deg)
        sweep_rad = self.main_wing.sweep_angle_rad
        
        if sweep_deg < 25.0:
            # Approximation pour ailes droites ou à faible flèche
            e = 1.78 * (1 - 0.045 * AR**0.68) - 0.64
        else:
            # Approximation pour ailes en flèche
            e = 4.61 * (1 - 0.045 * AR**0.68) * (math.cos(sweep_rad)**0.15) - 3.1
            
        # Bonus empirique des winglets (réduction de la traînée induite)
        if self.main_wing.has_winglets:
            e *= 1.15
            
        # Sécurité mathématique pour rester dans des limites physiques plausibles
        self.oswald_e = max(0.5, min(e, 0.98))
        
        # 2. Calcul de la traînée
        cdi = (self.cz_cruise ** 2) / (math.pi * self.oswald_e * AR)
        
        # Calcul de la traînée parasite via Component Build-up Method
        cd0 = self._estimate_cd0()
        
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
        
        # 1. Pente de portance 3D (Théorie de Diederich)
        a_0 = 2 * math.pi
        AR = self.main_wing.aspect_ratio
        sweep_rad = self.main_wing.sweep_angle_rad
        lift_slope_rad = (a_0 * AR) / (2 + math.sqrt(4 + (AR**2 / math.cos(sweep_rad)**2)))
        lift_slope_deg = math.radians(lift_slope_rad)
        
        # 2. Récupération du Cd0 calculé par la méthode des surfaces mouillées (Chantier 3)
        cd0 = self._estimate_cd0()
        
        # On pousse l'analyse jusqu'à 25° pour bien visualiser la zone de décrochage
        alphas = list(range(-5, 26))
        cz_list = []
        cd_list = []
        finesse_list = []
        
        # Angle critique où le profil atteint son Cz_max
        alpha_stall = (cl_max - cl_0) / lift_slope_deg
        
        for alpha in alphas:
            if alpha <= alpha_stall:
                # Comportement linéaire classique (vol normal)
                cz = cl_0 + lift_slope_deg * alpha
                
                # Limite basse (décrochage dos approximé)
                if cz < -cl_max * 0.6:
                    cz = -cl_max * 0.6
            else:
                # 3. Comportement post-décrochage non-linéaire (perte de portance parabolique)
                delta_alpha = alpha - alpha_stall
                cz = cl_max - 0.015 * (delta_alpha ** 2)
                
                # Palier minimal pour éviter un Cz absurdement négatif aux très grands angles
                if cz < cl_max * 0.3:
                    cz = cl_max * 0.3
                
            # Calcul de la traînée induite classique
            cdi = (cz ** 2) / (math.pi * self.oswald_e * self.main_wing.aspect_ratio)
            
            if alpha > alpha_stall:
                # En décrochage, la traînée de pression explose à cause du sillage turbulent
                delta_alpha = alpha - alpha_stall
                cd = cd0 + cdi + 0.02 * (delta_alpha ** 2)
            else:
                cd = cd0 + cdi
                
            cz_list.append(cz)
            cd_list.append(cd)
            
            finesse = cz / cd if cd > 0 else 0
            finesse_list.append(finesse)
            
        return alphas, cz_list, cd_list, finesse_list

    def get_structural_data(self):
        b2 = self.main_wing.span / 2
        S = self.main_wing.surface
        cr = self.main_wing.root_chord
        ct = self.main_wing.tip_chord
        
        L_max_half = (self.mass * self.g * self.n_max_struct) / 2.0
        
        n_points = 100
        dy = b2 / n_points
        y_vals = [i * dy for i in range(n_points + 1)]
        
        def get_chord_at(y):
            if self.wing_shape not in ["Lambda"]:
                return cr - (cr - ct) * (y / b2)
            else:
                y_kink = self.main_wing.outline_y[1]
                c_kink = self.main_wing.outline_x[4] - self.main_wing.outline_x[1]
                if y <= y_kink:
                    if y_kink == 0: return cr
                    return cr - (cr - c_kink) * (y / y_kink)
                else:
                    if b2 == y_kink: return c_kink
                    return c_kink - (c_kink - ct) * ((y - y_kink) / (b2 - y_kink))

        l_dist = []
        for y in y_vals:
            c_actual = get_chord_at(y)
            
            if y >= b2:
                c_ell = 0
            else:
                c_ell = (4 * S / (math.pi * self.main_wing.span)) * math.sqrt(1 - (y / b2)**2)
            
            c_schrenk = (c_actual + c_ell) / 2.0
            
            l_val = (L_max_half / (S / 2)) * c_schrenk
            l_dist.append(l_val)
            
        v_dist = [0] * (n_points + 1)
        m_dist = [0] * (n_points + 1)
        
        for i in range(n_points - 1, -1, -1):
            v_dist[i] = v_dist[i+1] + 0.5 * (l_dist[i] + l_dist[i+1]) * dy
            m_dist[i] = m_dist[i+1] + 0.5 * (v_dist[i] + v_dist[i+1]) * dy
            
        max_shear = v_dist[0]
        max_moment = m_dist[0]
        
        return y_vals, l_dist, v_dist, m_dist, max_shear, max_moment

    def _estimate_cd0(self) -> float:
        """
        Calcule la traînée parasite globale (Cd0) par la Component Build-up Method.
        Somme les contributions de friction et de forme de chaque surface mouillée.
        """
        # 1. Aile principale
        # L'épaisseur relative (t/c) est récupérée du profil (souvent donnée en %)
        tc_wing = self.airfoil.thickness / 100.0 if self.airfoil.thickness > 1.0 else self.airfoil.thickness
        swet_wing = 2.0 * self.main_wing.surface * (1.0 + 0.25 * tc_wing)
        cf_wing = 0.0055  # Cf estimé pour un écoulement mixte sur drone (Re ~ 500k)
        cd0_wing = cf_wing * swet_wing / self.main_wing.surface
        
        # 2. Fuselage (Modélisation par un corps profilé équivalent)
        cd0_fuselage = 0.0
        if self.tail_type == "Aile Volante":
            cd0_fuselage = 0.002 # Traînée résiduelle de la bosse centrale / charge utile
        else:
            # Estimation géométrique d'un fuselage à partir de l'architecture
            l_fuselage = self.nose_length + self.main_wing.root_chord + self.tail_arm
            # Volume estimé à partir de la masse (hyp: densité moyenne drone 300 kg/m^3)
            vol_fuselage = self.mass / 300.0
            d_fuselage = math.sqrt((4 * vol_fuselage) / (math.pi * l_fuselage))
            
            finesse_fuselage = l_fuselage / max(0.01, d_fuselage)
            swet_fuselage = math.pi * d_fuselage * l_fuselage * 0.75 # Forme en fuseau (facteur géométrique)
            
            # Facteur de forme (Form Factor) pour un corps 3D (Fuselage)
            ff_fuselage = 1.0 + 60.0 / (finesse_fuselage**3) + finesse_fuselage / 400.0
            cf_fuselage = 0.006
            cd0_fuselage = (cf_fuselage * ff_fuselage * swet_fuselage) / self.main_wing.surface
            
        # 3. Empennages (Hypothèse de profils symétriques fins type NACA 0009)
        cd0_tails = 0.0
        tc_tail = 0.09 
        cf_tail = 0.006
        
        if self.h_tail:
            swet_htail = 2.0 * self.h_tail.surface * (1.0 + 0.25 * tc_tail)
            cd0_tails += cf_tail * swet_htail / self.main_wing.surface
            
        if self.v_tail:
            swet_vtail = 2.0 * self.v_tail.surface * (1.0 + 0.25 * tc_tail)
            cd0_tails += cf_tail * swet_vtail / self.main_wing.surface
        elif getattr(self, 'v_tail_obj', None): # Pour le cas Empennage en V
            swet_vtail = 2.0 * self.v_tail_obj.surface * (1.0 + 0.25 * tc_tail)
            cd0_tails += cf_tail * swet_vtail / self.main_wing.surface
            
        # 4. Traînée parasite totale 
        # Majoration de 10% pour les interférences de jonctions (Interference Drag) et rugosités
        cd0_total = (cd0_wing + cd0_fuselage + cd0_tails) * 1.10
        
        # Sécurité : le Cd0 global ne peut pas être inférieur au Cd0 théorique en soufflerie du profil seul
        return max(cd0_total, self.airfoil.cd_0)