import math

class Wing:
    def __init__(self, surface: float, aspect_ratio: float, taper_ratio: float):
        """
        Initialise une aile à partir de ses paramètres de design globaux.
        surface: Surface alaire en m^2
        aspect_ratio: Allongement (sans dimension)
        taper_ratio: Effilement (Corde saumon / Corde emplanture)
        """
        self.surface = surface
        self.aspect_ratio = aspect_ratio
        self.taper_ratio = taper_ratio
        
        # Attributs géométriques calculés
        self.span = 0.0
        self.root_chord = 0.0
        self.tip_chord = 0.0
        self.mean_aerodynamic_chord = 0.0
        
        self._calculate_geometry()

    def _calculate_geometry(self):
        """Calcule les dimensions physiques de l'aile."""
        # Calcul de l'envergure
        self.span = math.sqrt(self.surface * self.aspect_ratio)
        
        # Calcul de la corde à l'emplanture
        self.root_chord = (2 * self.surface) / (self.span * (1 + self.taper_ratio))
        
        # Calcul de la corde au saumon
        self.tip_chord = self.root_chord * self.taper_ratio
        
        # Calcul de la corde moyenne aérodynamique (MAC)
        self.mean_aerodynamic_chord = (2/3) * self.root_chord * ((1 + self.taper_ratio + self.taper_ratio**2) / (1 + self.taper_ratio))

    def get_summary(self) -> dict:
        """Retourne un dictionnaire avec les dimensions calculées."""
        return {
            "Envergure (m)": round(self.span, 3),
            "Corde emplanture (m)": round(self.root_chord, 3),
            "Corde saumon (m)": round(self.tip_chord, 3),
            "MAC (m)": round(self.mean_aerodynamic_chord, 3)
        }

# --- Test rapide (à supprimer plus tard) ---
if __name__ == "__main__":
    # Exemple : Aile de 0.5 m^2, allongement de 8, effilement de 0.6
    my_wing = Wing(surface=0.5, aspect_ratio=8, taper_ratio=0.6)
    print("--- Géométrie de l'aile Wyng ---")
    for key, value in my_wing.get_summary().items():
        print(f"{key}: {value}")