from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit)
from core.airfoil import AirfoilDatabase

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.resize(800, 500)
        
        # Chargement de la base de données
        self.db = AirfoilDatabase()
        
        # Mise en place de l'interface
        self._setup_ui()

    def _setup_ui(self):
        # Widget central et layout (mise en page) principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Panneau Gauche : Entrées (Layout Vertical) ---
        input_layout = QVBoxLayout()
        
        self.mass_input = QLineEdit("2.5")
        input_layout.addWidget(QLabel("Masse cible (kg) :"))
        input_layout.addWidget(self.mass_input)
        
        self.vstall_input = QLineEdit("10.0")
        input_layout.addWidget(QLabel("Vitesse de décrochage (m/s) :"))
        input_layout.addWidget(self.vstall_input)
        
        self.airfoil_combo = QComboBox()
        self.airfoil_combo.addItems(self.db.list_airfoils()) # Charge les profils du CSV
        input_layout.addWidget(QLabel("Profil de l'aile :"))
        input_layout.addWidget(self.airfoil_combo)
        
        self.calc_button = QPushButton("Calculer la géométrie")
        self.calc_button.clicked.connect(self.calculate_geometry)
        input_layout.addWidget(self.calc_button)
        
        input_layout.addStretch() # Pousse joliment les éléments vers le haut
        
        # --- Panneau Droit : Résultats ---
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Les résultats s'afficheront ici...")
        
        # Assemblage des deux panneaux
        main_layout.addLayout(input_layout, 1) # Occupe 1/3 de l'espace
        main_layout.addWidget(self.result_text, 2) # Occupe 2/3 de l'espace

    def calculate_geometry(self):
        # Jour 5 : C'est ici que nous lierons les valeurs tapées par l'utilisateur à ta classe Drone !
        self.result_text.setText("Le bouton fonctionne ! \nEn attente de connexion avec le moteur de calcul (Jour 5)...")