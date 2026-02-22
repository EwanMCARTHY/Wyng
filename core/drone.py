from core.wing import Wing

class Drone:
    def __init__(self, mass: float, v_stall: float, cl_max: float = 1.2, aspect_ratio: float = 8.0, taper_ratio: float = 0.6):
        """
        Initialise le drone complet.
        mass: Masse totale en kg
        v_stall: Vitesse de décrochage cible en m/s
        cl_max: Coefficient de portance maximal estimé de l'aile
        aspect_ratio: Allongement cible
        taper_ratio: Effilement cible
        """
        self.mass = mass
        self.v_stall = v_stall
        self.cl_max = cl_max
        
        # Constantes (Atmosphère standard au niveau de la mer)
        self.rho = 1.225  # Densité de l'air (kg/m^3)
        self.g = 9.81     # Accélération de la pesanteur (m/s^2)
        
        # 1. Calcul de la surface requise
        self.required_surface = self._calculate_required_surface()
        
        # 2. Création automatique de l'aile principale
        self.main_wing = Wing(
            surface=self.required_surface, 
            aspect_ratio=aspect_ratio, 
            taper_ratio=taper_ratio
        )

    def _calculate_required_surface(self) -> float:
        """Calcule la surface alaire minimale (S) requise au décrochage."""
        weight = self.mass * self.g
        dynamic_pressure = 0.5 * self.rho * (self.v_stall ** 2)
        surface = weight / (dynamic_pressure * self.cl_max)
        return surface

# --- Test rapide ---
if __name__ == "__main__":
    # Exemple : Drone de 2.5 kg, décrochage à 10 m/s (36 km/h)
    my_drone = Drone(mass=2.5, v_stall=10.0, aspect_ratio=10)
    
    print(f"--- Dimensionnement Wyng : Drone de {my_drone.mass} kg ---")
    print(f"Surface alaire requise : {round(my_drone.required_surface, 3)} m2")
    print("\n--- Géométrie de l'aile générée ---")
    for key, value in my_drone.main_wing.get_summary().items():
        print(f"{key}: {value}")