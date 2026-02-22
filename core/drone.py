from core.wing import Wing
from core.airfoil import Airfoil, AirfoilDatabase

class Drone:
    def __init__(self, mass: float, v_stall: float, v_cruise: float, airfoil: Airfoil, 
                 aspect_ratio: float = 8.0, taper_ratio: float = 0.6,
                 sweep_angle: float = 0.0,
                 nose_length: float = 0.2,
                 tail_arm: float = 1.0, vh: float = 0.5, vv: float = 0.04,
                 tail_type: str = "Classique"):
        
        """
        Initialise le drone complet avec son aile et ses empennages.
        tail_arm: Bras de levier de l'empennage en mètres (distance aile-queue)
        vh: Coefficient de volume d'empennage horizontal
        vv: Coefficient de volume d'empennage vertical
        """
        
        self.mass = mass
        self.v_stall = v_stall
        self.v_cruise = v_cruise
        self.airfoil = airfoil
        self.tail_arm = tail_arm
        self.nose_length = nose_length
        self.vh = vh
        self.vv = vv
        self.tail_type = tail_type
        
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
        self._calculate_cg_and_stability()
        self._calculate_incidence()

    def _calculate_required_surface(self) -> float:
        """Calcule la surface alaire minimale requise au décrochage."""
        weight = self.mass * self.g
        dynamic_pressure = 0.5 * self.rho * (self.v_stall ** 2)
        surface = weight / (dynamic_pressure * self.airfoil.cl_max)
        return surface

    def _calculate_tails(self):
        import math
        
        if self.tail_type == "Aile Volante":
            # Pas d'empennage, la machine est réduite à son aile
            self.h_tail = None
            self.v_tail = None
            self.v_tail_obj = None
            self.v_angle = 0.0
            return # On sort de la fonction

        sh_surface = (self.vh * self.main_wing.surface * self.main_wing.mean_aerodynamic_chord) / self.tail_arm
        sv_surface = (self.vv * self.main_wing.surface * self.main_wing.span) / self.tail_arm

        if self.tail_type == "Classique":
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=0.7)
            self.v_tail = Wing(surface=sv_surface, aspect_ratio=1.5, taper_ratio=0.8)
            self.v_angle = 0.0
            
        elif self.tail_type == "Empennage en V":
            vtail_surface = sh_surface + sv_surface
            self.v_angle = math.degrees(math.atan(math.sqrt(sv_surface / sh_surface)))
            self.v_tail_obj = Wing(surface=vtail_surface, aspect_ratio=4.0, taper_ratio=0.7)
            self.h_tail = Wing(surface=sh_surface, aspect_ratio=4.0, taper_ratio=0.7)
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