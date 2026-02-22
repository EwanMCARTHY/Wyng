import math

class Wing:
    def __init__(self, surface: float, aspect_ratio: float, taper_ratio: float, 
                 sweep_angle_deg: float = 0.0, dihedral_angle_deg: float = 0.0,
                 wing_shape: str = "Trapézoïdale"): # <-- Nouveau paramètre
        
        self.surface = surface
        self.aspect_ratio = aspect_ratio
        self.taper_ratio = taper_ratio
        self.sweep_angle_deg = sweep_angle_deg
        self.dihedral_angle_deg = dihedral_angle_deg
        self.wing_shape = wing_shape
        
        self.sweep_angle_rad = math.radians(sweep_angle_deg)
        self.dihedral_angle_rad = math.radians(dihedral_angle_deg)
        
        self.span = 0.0
        self.root_chord = 0.0
        self.tip_chord = 0.0
        self.mean_aerodynamic_chord = 0.0
        self.aerodynamic_center_x = 0.0
        self.tip_offset_x = 0.0 
        self.tip_offset_z = 0.0 
        
        # Coordonnées pour le dessin (Demi-aile droite)
        self.outline_x = []
        self.outline_y = []
        
        self._calculate_geometry()

    def _calculate_geometry(self):
        self.span = math.sqrt(self.surface * self.aspect_ratio)
        b2 = self.span / 2
        
        # Élévation du saumon (Dièdre)
        self.tip_offset_z = b2 * math.tan(self.dihedral_angle_rad)

        if self.wing_shape == "Delta":
            # Une aile Delta pure a un bord de fuite droit et un saumon quasi nul
            self.taper_ratio = 0.05 # Pour éviter les divisions par zéro
            self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
            self.tip_chord = self.root_chord * self.taper_ratio
            self.tip_offset_x = self.root_chord - self.tip_chord # Force le bord de fuite droit
            self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))
            self.aerodynamic_center_x = self.root_chord - (0.75 * self.mean_aerodynamic_chord)
            
            # Coordonnées du polygone (Bord d'attaque puis Bord de fuite)
            self.outline_x = [0, self.tip_offset_x, self.tip_offset_x + self.tip_chord, self.root_chord]
            self.outline_y = [0, b2, b2, 0]

        elif self.wing_shape == "Lambda":
            # Aile Lambda Furtive (type X-47B / Cranked Kite)
            
            # 1. Forcer un effilement très fin au saumon (typique des ailes furtives)
            self.taper_ratio = 0.15 
            
            # 2. Paramètres géométriques de la cassure (Proportions X-47B)
            y_kink_ratio = 0.45  # La cassure est à 45% de la demi-envergure
            c_kink_ratio = 0.35  # La corde à la cassure fait 35% de l'emplanture
            
            # 3. Gestion des flèches (Bord d'attaque)
            inner_sweep_rad = self.sweep_angle_rad
            outer_sweep_rad = self.sweep_angle_rad * 0.6 # Flèche adoucie sur l'extérieur
            
            y_kink = b2 * y_kink_ratio
            
            # 4. Calcul de la corde d'emplanture pour respecter la surface imposée
            # (Calcul barycentrique des deux panneaux pour garantir la justesse physique)
            term_inner = 0.5 * y_kink_ratio * (1.0 + c_kink_ratio)
            term_outer = 0.5 * (1.0 - y_kink_ratio) * (c_kink_ratio + self.taper_ratio)
            
            self.root_chord = (self.surface / 2.0) / (b2 * (term_inner + term_outer))
            self.tip_chord = self.root_chord * self.taper_ratio
            c_kink = self.root_chord * c_kink_ratio
            
            # 5. Calcul des points X (Bord d'attaque et Bord de fuite)
            x_kink_le = y_kink * math.tan(inner_sweep_rad)
            self.tip_offset_x = x_kink_le + (b2 - y_kink) * math.tan(outer_sweep_rad)
            x_kink_te = x_kink_le + c_kink
            
            # 6. Coordonnées du polygone (Emplanture -> Cassure -> Saumon -> ... -> Emplanture)
            self.outline_x = [0.0, x_kink_le, self.tip_offset_x, self.tip_offset_x + self.tip_chord, x_kink_te, self.root_chord]
            self.outline_y = [0.0, y_kink, b2, b2, y_kink, 0.0]
            
            # 7. Aérodynamique (Approximation de la MAC globale pondérée par les surfaces)
            area_inner = 0.5 * y_kink * (self.root_chord + c_kink)
            area_outer = 0.5 * (b2 - y_kink) * (c_kink + self.tip_chord)
            mac_inner = (2/3) * self.root_chord * ((1 + c_kink_ratio + c_kink_ratio**2) / (1 + c_kink_ratio))
            mac_outer = (2/3) * c_kink * ((1 + (self.tip_chord/c_kink) + (self.tip_chord/c_kink)**2) / (1 + (self.tip_chord/c_kink)))
            
            self.mean_aerodynamic_chord = (mac_inner * area_inner + mac_outer * area_outer) / (self.surface / 2)
            
            avg_sweep = (inner_sweep_rad + outer_sweep_rad) / 2
            y_mac = b2 * 0.4
            self.aerodynamic_center_x = (y_mac * math.tan(avg_sweep)) + (0.25 * self.mean_aerodynamic_chord)

        else: # Trapézoïdale par défaut
            self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
            self.tip_chord = self.root_chord * self.taper_ratio
            self.tip_offset_x = b2 * math.tan(self.sweep_angle_rad)
            self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))
            y_mac = (b2 / 3) * ((1 + 2 * self.taper_ratio) / (1 + self.taper_ratio))
            self.aerodynamic_center_x = (y_mac * math.tan(self.sweep_angle_rad)) + (0.25 * self.mean_aerodynamic_chord)
            
            self.outline_x = [0, self.tip_offset_x, self.tip_offset_x + self.tip_chord, self.root_chord]
            self.outline_y = [0, b2, b2, 0]

    def get_summary(self) -> dict:
        return {
            "Forme": self.wing_shape,
            "Envergure (m)": round(self.span, 3),
            "Corde emplanture (m)": round(self.root_chord, 3),
            "Corde saumon (m)": round(self.tip_chord, 3),
            "MAC (m)": round(self.mean_aerodynamic_chord, 3),
            "Flèche (°)": round(self.sweep_angle_deg, 1),
            "Dièdre (°)": round(self.dihedral_angle_deg, 1)
        }