import csv
import os

class Airfoil:
    def __init__(self, name: str, cl_max: float, cd_0: float, cm_0: float, thickness: float):
        """Représente les caractéristiques aérodynamiques d'un profil 2D."""
        self.name = name
        self.cl_max = cl_max
        self.cd_0 = cd_0
        self.cm_0 = cm_0
        self.thickness = thickness

class AirfoilDatabase:
    def __init__(self, filepath: str = "data/airfoils.csv"):
        """Charge et gère la base de données des profils."""
        self.filepath = filepath
        self.airfoils = {} # Dictionnaire pour stocker les profils avec leur nom comme clé
        self._load_database()

    def _load_database(self):
        """Lit le fichier CSV et peuple le dictionnaire de profils."""
        if not os.path.exists(self.filepath):
            print(f"Erreur : Le fichier {self.filepath} est introuvable depuis le répertoire actuel.")
            return

        with open(self.filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row["Name"].strip()
                self.airfoils[name] = Airfoil(
                    name=name,
                    cl_max=float(row["Cl_max"]),
                    cd_0=float(row["Cd_0"]),
                    cm_0=float(row["Cm_0"]),
                    thickness=float(row["Thickness"])
                )

    def get_airfoil(self, name: str) -> Airfoil:
        """Retourne l'objet Airfoil correspondant au nom."""
        return self.airfoils.get(name)

    def list_airfoils(self) -> list:
        """Retourne la liste des noms des profils disponibles."""
        return list(self.airfoils.keys())

# --- Test rapide ---
if __name__ == "__main__":
    # Si on exécute ce fichier depuis la racine avec python -m core.airfoil
    db = AirfoilDatabase() 
    
    print("--- Base de données Wyng ---")
    print("Profils disponibles :", db.list_airfoils())
    
    selig = db.get_airfoil("Selig 1223")
    if selig:
        print(f"\nFocus sur le {selig.name} :")
        print(f"  Cz_max (Portance) : {selig.cl_max}")
        print(f"  Cm_0 (Moment) : {selig.cm_0}")