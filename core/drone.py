from core.wing import Wing
from core.airfoil import Airfoil, AirfoilDatabase

class Drone:
    def __init__(self, mass: float, v_stall: float, airfoil: Airfoil, 
                 aspect_ratio: float = 8.0, taper_ratio: float = 0.6,
                 sweep_angle: float = 0.0, # <-- Nouveau paramètre
                 tail_arm: float = 1.0, vh: float = 0.5, vv: float = 0.04):
        
        """
        Initialise le drone complet avec son aile et ses empennages.
        tail_arm: Bras de levier de l'empennage en mètres (distance aile-queue)
        vh: Coefficient de volume d'empennage horizontal
        vv: Coefficient de volume d'empennage vertical
        """
        
        self.mass = mass
        self.v_stall = v_stall
        self.airfoil = airfoil
        self.tail_arm = tail_arm
        self.vh = vh
        self.vv = vv
        
        self.rho = 1.225  
        self.g = 9.81     
        
        self.required_surface = self._calculate_required_surface()
        
        # On transmet l'angle de flèche à l'aile
        self.main_wing = Wing(
            surface=self.required_surface, 
            aspect_ratio=aspect_ratio, 
            taper_ratio=taper_ratio,
            sweep_angle_deg=sweep_angle
        )
        
        self._calculate_tails()

    def _calculate_required_surface(self) -> float:
        """Calcule la surface alaire minimale requise au décrochage."""
        weight = self.mass * self.g
        dynamic_pressure = 0.5 * self.rho * (self.v_stall ** 2)
        surface = weight / (dynamic_pressure * self.airfoil.cl_max)
        return surface

    def _calculate_tails(self):
        """Calcule et instancie les empennages horizontal et vertical."""
        # Surface empennage horizontal (SH)
        sh_surface = (self.vh * self.main_wing.surface * self.main_wing.mean_aerodynamic_chord) / self.tail_arm
        # On instancie une nouvelle "Wing" pour l'empennage (allongement plus faible, ex: 4.0)
        self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=0.7)

        # Surface dérive verticale (SV)
        sv_surface = (self.vv * self.main_wing.surface * self.main_wing.span) / self.tail_arm
        # On instancie une nouvelle "Wing" pour la dérive (allongement très faible, ex: 1.5)
        self.v_tail = Wing(surface=sv_surface, aspect_ratio=1.5, taper_ratio=0.8)


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