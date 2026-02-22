import math

class Wing:
    def __init__(self, surface: float, aspect_ratio: float = 8.0, taper_ratio: float = 0.6, 
                 sweep_angle_deg: float = 0.0, dihedral_angle_deg: float = 0.0,
                 wing_shape: str = "Trapézoïdale", washout_deg: float = 0.0,
                 kink_pos_ratio: float = 0.45,
                 has_winglets: bool = False, kink_angle_deg: float = -30.0):
        
        self.surface = surface
        self.aspect_ratio = aspect_ratio
        self.taper_ratio = taper_ratio
        self.sweep_angle_deg = sweep_angle_deg
        self.dihedral_angle_deg = dihedral_angle_deg
        self.wing_shape = wing_shape
        self.washout_deg = washout_deg
        self.kink_pos_ratio = kink_pos_ratio
        self.kink_angle_deg = kink_angle_deg
        self.has_winglets = has_winglets
        
        self.sweep_angle_rad = math.radians(sweep_angle_deg)
        self.dihedral_angle_rad = math.radians(dihedral_angle_deg)
        
        self.span = 0.0
        self.root_chord = 0.0
        self.tip_chord = 0.0
        self.mean_aerodynamic_chord = 0.0
        self.aerodynamic_center_x = 0.0
        self.tip_offset_x = 0.0 
        self.tip_offset_z = 0.0 
        
        self.outline_x = []
        self.outline_y = []
        
        self._calculate_geometry()

    def _calculate_geometry(self):
        self.span = math.sqrt(self.surface * self.aspect_ratio)
        b2 = self.span / 2
        self.tip_offset_z = b2 * math.tan(self.dihedral_angle_rad)

        if self.wing_shape == "Delta":
            self.taper_ratio = 0.05 
            self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
            self.tip_chord = self.root_chord * self.taper_ratio
            self.tip_offset_x = self.root_chord - self.tip_chord 
            
            # --- CORRECTION DELTA ---
            # Le bord de fuite étant droit, la flèche est dictée par la géométrie.
            # On écrase la valeur donnée par l'utilisateur.
            self.sweep_angle_rad = math.atan(self.tip_offset_x / b2)
            self.sweep_angle_deg = math.degrees(self.sweep_angle_rad)
            
            self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))
            self.aerodynamic_center_x = self.root_chord - (0.75 * self.mean_aerodynamic_chord)
            
            self.outline_x = [0, self.tip_offset_x, self.tip_offset_x + self.tip_chord, self.root_chord]
            self.outline_y = [0, b2, b2, 0]

        elif self.wing_shape == "Lambda":
            y_kink = b2 * self.kink_pos_ratio
            inner_sweep_rad = self.sweep_angle_rad
            outer_sweep_rad = self.sweep_angle_rad # Bord d'attaque droit
            kink_angle_rad = math.radians(self.kink_angle_deg)
            
            # delta_chord = variation mathématique de la corde due aux deux angles de flèche
            delta_chord = y_kink * (math.tan(kink_angle_rad) - math.tan(inner_sweep_rad))
            
            # Résolution analytique de l'emplanture pour maintenir la surface cible S
            denominator = 2 * y_kink + (b2 - y_kink) * (1 + self.taper_ratio)
            self.root_chord = (self.surface - delta_chord * b2) / denominator
            
            # Sécurités géométriques pour éviter que les lignes ne se croisent (cordes négatives)
            if self.root_chord < 0.1: self.root_chord = 0.1
            c_kink = self.root_chord + delta_chord
            if c_kink < 0.05:
                c_kink = 0.05
                self.root_chord = c_kink - delta_chord
            
            self.tip_chord = self.root_chord * self.taper_ratio
            
            x_kink_le = y_kink * math.tan(inner_sweep_rad)
            self.tip_offset_x = x_kink_le + (b2 - y_kink) * math.tan(outer_sweep_rad)
            
            # Position exacte du bord de fuite à la cassure
            x_kink_te = self.root_chord + y_kink * math.tan(kink_angle_rad) 
            
            self.outline_x = [0.0, x_kink_le, self.tip_offset_x, self.tip_offset_x + self.tip_chord, x_kink_te, self.root_chord]
            self.outline_y = [0.0, y_kink, b2, b2, y_kink, 0.0]
            
            # Calcul de la MAC
            area_inner = 0.5 * y_kink * (self.root_chord + c_kink)
            area_outer = 0.5 * (b2 - y_kink) * (c_kink + self.tip_chord)
            
            t_in = c_kink / self.root_chord if self.root_chord > 0 else 1
            t_out = self.tip_chord / c_kink if c_kink > 0 else 1
            
            mac_inner = (2/3) * self.root_chord * ((1 + t_in + t_in**2) / (1 + t_in))
            mac_outer = (2/3) * c_kink * ((1 + t_out + t_out**2) / (1 + t_out))
            
            self.mean_aerodynamic_chord = (mac_inner * area_inner + mac_outer * area_outer) / (self.surface / 2)
            self.aerodynamic_center_x = (y_kink * 0.5 * math.tan(inner_sweep_rad)) + (0.25 * self.mean_aerodynamic_chord)

        else: # Trapézoïdale
            self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
            self.tip_chord = self.root_chord * self.taper_ratio
            self.tip_offset_x = b2 * math.tan(self.sweep_angle_rad)
            self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))
            y_mac = (b2 / 3) * ((1 + 2 * self.taper_ratio) / (1 + self.taper_ratio))
            self.aerodynamic_center_x = (y_mac * math.tan(self.sweep_angle_rad)) + (0.25 * self.mean_aerodynamic_chord)
            
            self.outline_x = [0, self.tip_offset_x, self.tip_offset_x + self.tip_chord, self.root_chord]
            self.outline_y = [0, b2, b2, 0]

    def get_summary(self) -> dict:
        summary = {
            "Forme": self.wing_shape,
            "Allongement": round(self.aspect_ratio, 2),
            "Effilement": round(self.taper_ratio, 2),
            "Envergure (m)": round(self.span, 3),
            "MAC (m)": round(self.mean_aerodynamic_chord, 3),
            "Flèche (°)": round(self.sweep_angle_deg, 1),
            "Dièdre (°)": round(self.dihedral_angle_deg, 1)
        }
        if self.washout_deg < 0:
            summary["Vrillage (°)"] = round(self.washout_deg, 1)
        if self.has_winglets:
            summary["Winglets"] = "Oui"
        return summary