from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QFileDialog, QMessageBox)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.airfoil import AirfoilDatabase
from core.drone import Drone

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.resize(1000, 700) # Fenêtre un peu plus grande pour le schéma
        
        self.db = AirfoilDatabase()
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Panneau Gauche : Entrées ---
        input_layout = QVBoxLayout()
        
        self.mass_input = QLineEdit("2.5")
        input_layout.addWidget(QLabel("Masse cible (kg) :"))
        input_layout.addWidget(self.mass_input)
        
        self.vstall_input = QLineEdit("10.0")
        input_layout.addWidget(QLabel("Vitesse de décrochage (m/s) :"))
        input_layout.addWidget(self.vstall_input)
        
        self.sweep_input = QLineEdit("15.0") # Flèche de 15 degrés par défaut
        input_layout.addWidget(QLabel("Angle de flèche (°) :"))
        input_layout.addWidget(self.sweep_input)
        
        self.airfoil_combo = QComboBox()
        self.airfoil_combo.addItems(self.db.list_airfoils())
        input_layout.addWidget(QLabel("Profil de l'aile :"))
        input_layout.addWidget(self.airfoil_combo)
        
        self.calc_button = QPushButton("Calculer la géométrie")
        self.calc_button.clicked.connect(self.calculate_geometry)
        input_layout.addWidget(self.calc_button)
        
        self.export_button = QPushButton("Exporter les résultats")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False) # Désactivé au lancement
        input_layout.addWidget(self.export_button)
        
        input_layout.addStretch()
        
        # --- Panneau Droit : Résultats et Schéma ---
        right_layout = QVBoxLayout()
        
        # 1. Zone de texte (limitée en hauteur)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200) 
        self.result_text.setPlaceholderText("Les résultats s'afficheront ici...")
        right_layout.addWidget(self.result_text)
        
        # 2. Canevas Matplotlib pour le schéma
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Vue de dessus de la géométrie")
        self.ax.axis('equal') # Indispensable pour ne pas déformer le drone
        right_layout.addWidget(self.canvas)
        
        # Assemblage
        main_layout.addLayout(input_layout, 1) 
        main_layout.addLayout(right_layout, 2) 

    def calculate_geometry(self):
        try:
            mass = float(self.mass_input.text().replace(',', '.'))
            v_stall = float(self.vstall_input.text().replace(',', '.'))
            sweep = float(self.sweep_input.text().replace(',', '.'))
            airfoil_name = self.airfoil_combo.currentText()
            
            selected_airfoil = self.db.get_airfoil(airfoil_name)
            if not selected_airfoil:
                self.result_text.setText("Erreur : Profil introuvable.")
                return

            # Calcul physique
            drone = Drone(mass=mass, v_stall=v_stall, airfoil=selected_airfoil, sweep_angle=sweep)

            # Affichage texte
            results = f"=== DIMENSIONNEMENT WYNG ===\n"
            results += f"Masse : {mass} kg | Vitesse décrochage : {v_stall} m/s | Profil : {selected_airfoil.name}\n"
            results += f"Surface requise : {drone.required_surface:.3f} m²\n"
            results += "-" * 30 + "\n"
            results += f"AILE : Env={drone.main_wing.span:.2f}m, Corde Emp={drone.main_wing.root_chord:.2f}m, Corde Saum={drone.main_wing.tip_chord:.2f}m\n"
            results += f"EMPENNAGE : Env={drone.h_tail.span:.2f}m, Corde Emp={drone.h_tail.root_chord:.2f}m\n"
            
            self.result_text.setText(results)
            
            # Déclenchement du dessin 2D
            self._draw_drone(drone)
            
            self.export_button.setEnabled(True)

        except ValueError:
            self.result_text.setText("⚠️ Veuillez entrer des valeurs numériques valides.")

    def _draw_drone(self, drone):
        """Trace la géométrie du drone en vue de dessus."""
        self.ax.clear()
        
        # Configuration du graphique
        self.ax.set_title("Schéma 2D du Drone (Vue de dessus)")
        self.ax.set_xlabel("Axe longitudinal X (m)")
        self.ax.set_ylabel("Envergure Y (m)")

        # 1. Dessin de l'aile principale ...
        b2 = drone.main_wing.span / 2
        cr = drone.main_wing.root_chord
        ct = drone.main_wing.tip_chord
        offset = drone.main_wing.tip_offset_x # Le recul dû à la flèche
        
        # Coordonnées : Emplanture BA -> Saumon BA -> Saumon BF -> Emplanture BF -> Saumon gauche BF -> Saumon gauche BA
        x_wing = [0, offset, offset + ct, cr, offset + ct, offset]
        y_wing = [0, b2, b2, 0, -b2, -b2]
        self.ax.fill(x_wing, y_wing, color='skyblue', edgecolor='blue', alpha=0.6, label='Aile Principale')

        # 2. Dessin de l'empennage horizontal (Placé à x = tail_arm)
        arm = drone.tail_arm
        hb2 = drone.h_tail.span / 2
        hcr = drone.h_tail.root_chord
        hct = drone.h_tail.tip_chord
        
        x_htail = [arm, arm, arm+hct, arm+hcr, arm+hct, arm]
        y_htail = [0, hb2, hb2, 0, -hb2, -hb2]
        self.ax.fill(x_htail, y_htail, color='lightcoral', edgecolor='red', alpha=0.6, label='Empennage Horizontal')

        # 3. Dessin du fuselage (Ligne indicative)
        self.ax.plot([0, arm + hcr], [0, 0], color='black', linewidth=2, linestyle='--', label='Axe Fuselage')
    
        # 4. Dessin du Foyer global (Point Neutre) - Croix bleue
        self.ax.plot(drone.neutral_point_x, 0, marker='x', color='blue', markersize=10, 
                     markeredgewidth=2, label='Foyer (Point Neutre)')
                     
        # 5. Dessin du Centre de Gravité (CG) - Symbole classique de centrage noir et blanc
        self.ax.plot(drone.cg_x, 0, marker='o', color='black', markerfacecolor='white', 
                     markersize=12, markeredgewidth=2, label='Centre de Gravité (CG)')

        # Mise en forme finale
        self.ax.axis('equal') # Force les proportions réelles
        self.ax.grid(True, linestyle=':')
        self.ax.legend(loc='upper right', fontsize='small')
        
        # Rafraîchissement du canevas
        self.canvas.draw()
    
    def export_results(self):
        """Sauvegarde les résultats en format .txt et le schéma en .png."""
        # Ouvre une fenêtre de dialogue système pour choisir où enregistrer
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter la note de calcul", "Wyng_Design", "Fichier Texte (*.txt)")
        
        if file_path:
            try:
                # 1. Sauvegarde du texte
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.toPlainText())
                
                # 2. Sauvegarde du schéma Matplotlib
                # On remplace l'extension .txt par .png pour l'image
                image_path = file_path.replace('.txt', '.png')
                self.figure.savefig(image_path, dpi=300, bbox_inches='tight')
                
                # Confirmation utilisateur
                QMessageBox.information(self, "Export Réussi", 
                                        f"La note de calcul a été sauvegardée.\n\nTexte : {file_path}\nImage : {image_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'export", f"Impossible de sauvegarder les fichiers :\n{str(e)}")