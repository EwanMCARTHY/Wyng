import math

class Wing:
    def __init__(self, surface: float, aspect_ratio: float, taper_ratio: float, sweep_angle_deg: float = 0.0):
        """
        Initialise une aile.
        sweep_angle_deg: Angle de flèche au bord d'attaque en degrés.
        """
        self.surface = surface
        self.aspect_ratio = aspect_ratio
        self.taper_ratio = taper_ratio
        self.sweep_angle_deg = sweep_angle_deg
        
        # Conversion en radians pour les calculs
        self.sweep_angle_rad = math.radians(sweep_angle_deg)
        
        # Attributs géométriques
        self.span = 0.0
        self.root_chord = 0.0
        self.tip_chord = 0.0
        self.mean_aerodynamic_chord = 0.0
        self.tip_offset_x = 0.0 # Décalage vers l'arrière du saumon
        
        self._calculate_geometry()

    def _calculate_geometry(self):
        self.span = math.sqrt(self.surface * self.aspect_ratio)
        self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
        self.tip_chord = self.root_chord * self.taper_ratio
        self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))
        
        # Calcul du recul du saumon dû à la flèche
        self.tip_offset_x = (self.span / 2) * math.tan(self.sweep_angle_rad)

    def get_summary(self) -> dict:
        return {
            "Envergure (m)": round(self.span, 3),
            "Corde emplanture (m)": round(self.root_chord, 3),
            "Corde saumon (m)": round(self.tip_chord, 3),
            "MAC (m)": round(self.mean_aerodynamic_chord, 3),
            "Flèche (°)": round(self.sweep_angle_deg, 1)
        }