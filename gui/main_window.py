from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QFileDialog, QMessageBox, QSlider,
                             QGroupBox, QGridLayout, QFormLayout)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.airfoil import AirfoilDatabase
from core.drone import Drone

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.setMinimumSize(1000, 700)
        self.setWindowIcon(QIcon('wing.ico'))
        
        self.db = AirfoilDatabase()
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Panneau Gauche : Entrées ---
        input_layout = QVBoxLayout()
        
        # Entrées textuelles (pour les valeurs absolues)
        self.mass_input = QLineEdit("2.5")
        self.mass_input.textChanged.connect(self.calculate_geometry)
        input_layout.addWidget(QLabel("Masse cible (kg) :"))
        input_layout.addWidget(self.mass_input)
        
        self.vstall_input = QLineEdit("10.0")
        self.vstall_input.textChanged.connect(self.calculate_geometry)
        input_layout.addWidget(QLabel("Vitesse décrochage (m/s) :"))
        input_layout.addWidget(self.vstall_input)
        
        self.vcruise_input = QLineEdit("15.0")
        self.vcruise_input.textChanged.connect(self.calculate_geometry)
        input_layout.addWidget(QLabel("Vitesse croisière (m/s) :"))
        input_layout.addWidget(self.vcruise_input)
        
        self.airfoil_combo = QComboBox()
        self.airfoil_combo.addItems(self.db.list_airfoils())
        self.airfoil_combo.currentTextChanged.connect(self.calculate_geometry) # MàJ auto si on change de profil
        input_layout.addWidget(QLabel("Profil de l'aile :"))
        input_layout.addWidget(self.airfoil_combo)
        
        self.tail_combo = QComboBox()
        self.tail_combo.addItems(["Classique", "Empennage en V", "Aile Volante"])
        self.tail_combo.currentTextChanged.connect(self._on_tail_changed)
        input_layout.addWidget(QLabel("Architecture Empennage :"))
        input_layout.addWidget(self.tail_combo)
        
        # 1. Slider : Angle de flèche (0 à 45°)
        self.sweep_label = QLabel("Angle de flèche : 0.0 °")
        self.sweep_slider = QSlider(Qt.Orientation.Horizontal)
        self.sweep_slider.setRange(0, 450) # 0 à 45.0° (multiplié par 10)
        self.sweep_slider.setValue(0)
        self.sweep_slider.valueChanged.connect(self.calculate_geometry) # Déclenche le calcul en direct !
        input_layout.addWidget(self.sweep_label)
        input_layout.addWidget(self.sweep_slider)
        
        self.dihedral_label = QLabel("Angle de dièdre : 0.0 °")
        self.dihedral_slider = QSlider(Qt.Orientation.Horizontal)
        self.dihedral_slider.setRange(0, 150) # 0 à 15.0°
        self.dihedral_slider.setValue(0)
        self.dihedral_slider.valueChanged.connect(self.calculate_geometry)
        input_layout.addWidget(self.dihedral_label)
        input_layout.addWidget(self.dihedral_slider)

        # 2. Slider : Bras de levier (0.3m à 2.5m)
        self.tailarm_label = QLabel("Bras de levier empennage : 1.0 m")
        self.tailarm_slider = QSlider(Qt.Orientation.Horizontal)
        self.tailarm_slider.setRange(30, 250) # 0.3m à 2.5m
        self.tailarm_slider.setValue(100)
        self.tailarm_slider.valueChanged.connect(self.calculate_geometry)
        input_layout.addWidget(self.tailarm_label)
        input_layout.addWidget(self.tailarm_slider)
        
        self.htail_sweep_label = QLabel("Flèche empennage : 0.0 °")
        self.htail_sweep_slider = QSlider(Qt.Orientation.Horizontal)
        self.htail_sweep_slider.setRange(0, 450) # 0 à 45.0°
        self.htail_sweep_slider.setValue(0)
        self.htail_sweep_slider.valueChanged.connect(self.calculate_geometry)
        input_layout.addWidget(self.htail_sweep_label)
        input_layout.addWidget(self.htail_sweep_slider)

        # 3. Slider : Longueur du Nez (0.0m à 1.0m)
        self.nose_label = QLabel("Longueur du nez : 0.2 m")
        self.nose_slider = QSlider(Qt.Orientation.Horizontal)
        self.nose_slider.setRange(0, 100) # 0.0m à 1.0m
        self.nose_slider.setValue(20)
        self.nose_slider.valueChanged.connect(self.calculate_geometry)
        input_layout.addWidget(self.nose_label)
        input_layout.addWidget(self.nose_slider)
        
        # Bouton d'export (Le bouton Calculer disparait, c'est automatique maintenant !)
        self.export_button = QPushButton("Exporter les résultats")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        input_layout.addWidget(self.export_button)
        
        input_layout.addStretch()
        
        # --- Panneau Droit : Résultats et Schéma ---
        right_layout = QVBoxLayout()
        
        # 1. Le Tableau de Bord des Résultats
        self.results_box = QGroupBox("Paramètres Géométriques")
        results_layout = QGridLayout()

        # Encart : Aile Principale
        wing_group = QGroupBox("Aile Principale")
        wing_layout = QFormLayout()
        self.lbl_surface = QLabel("-")
        self.lbl_wing_span = QLabel("-")
        self.lbl_wing_root = QLabel("-")
        self.lbl_wing_tip = QLabel("-")
        self.lbl_wing_inc = QLabel("-")
        
        wing_layout.addRow("Surface requise :", self.lbl_surface)
        wing_layout.addRow("Envergure :", self.lbl_wing_span)
        wing_layout.addRow("Corde emplanture :", self.lbl_wing_root)
        wing_layout.addRow("Corde saumon :", self.lbl_wing_tip)
        wing_layout.addRow("Calage requis :", self.lbl_wing_inc)
        wing_group.setLayout(wing_layout)

        # Encart : Empennage
        tail_group = QGroupBox("Empennage")
        self.tail_layout = QFormLayout()
        self.lbl_tail_type = QLabel("-")
        self.lbl_tail_span = QLabel("-")
        self.lbl_tail_root = QLabel("-")
        self.lbl_tail_angle = QLabel("-")
        self.tail_layout.addRow("Architecture :", self.lbl_tail_type)
        self.tail_layout.addRow("Envergure totale :", self.lbl_tail_span)
        self.tail_layout.addRow("Corde emplanture :", self.lbl_tail_root)
        self.tail_layout.addRow("Angle d'ouverture :", self.lbl_tail_angle)
        tail_group.setLayout(self.tail_layout)

        # Encart : Corps & Stabilité
        stab_group = QGroupBox("Corps & Stabilité")
        stab_layout = QFormLayout()
        self.lbl_length = QLabel("-")
        self.lbl_np = QLabel("-")
        self.lbl_cg = QLabel("-")
        self.lbl_alert = QLabel("")
        self.lbl_alert.setStyleSheet("color: red; font-weight: bold;") # Texte en rouge pour l'alerte
        stab_layout.addRow("Longueur totale :", self.lbl_length)
        stab_layout.addRow("Foyer (X_NP) :", self.lbl_np)
        stab_layout.addRow("CG cible (X_CG) :", self.lbl_cg)
        stab_layout.addRow("", self.lbl_alert)
        stab_group.setLayout(stab_layout)

        # Assemblage de la grille de résultats
        results_layout.addWidget(wing_group, 0, 0)
        results_layout.addWidget(tail_group, 0, 1)
        results_layout.addWidget(stab_group, 0, 2)
        self.results_box.setLayout(results_layout)
        
        right_layout.addWidget(self.results_box)
        
        # 2. Canevas Matplotlib pour les schémas
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        
        # On divise en 2 lignes, 1 colonne
        self.ax_top = self.figure.add_subplot(211) # En haut : Vue de dessus
        self.ax_front = self.figure.add_subplot(212) # En bas : Vue de face
        
        # On ajuste l'espacement pour que ça ne se chevauche pas
        self.figure.subplots_adjust(hspace=0.3)
        
        right_layout.addWidget(self.canvas)
        
        main_layout.addLayout(input_layout, 1) 
        main_layout.addLayout(right_layout, 3)

        # On lance un premier calcul au démarrage pour éviter un écran blanc
        self.calculate_geometry()
    
    def _on_tail_changed(self):
        """Met à jour la liste des profils autorisés selon l'architecture choisie."""
        is_flying_wing = (self.tail_combo.currentText() == "Aile Volante")
        
        # On sauvegarde le profil actuellement sélectionné pour essayer de le garder
        current_airfoil = self.airfoil_combo.currentText()
        
        # On bloque temporairement les signaux pour éviter que le nettoyage de la liste 
        # ne déclenche calculate_geometry() dans le vide et fasse crasher le programme
        self.airfoil_combo.blockSignals(True)
        
        self.airfoil_combo.clear()
        valid_airfoils = self.db.list_airfoils(require_autostable=is_flying_wing)
        self.airfoil_combo.addItems(valid_airfoils)
        
        # Si l'ancien profil est toujours valide, on le remet. Sinon, on prend le premier de la liste.
        if current_airfoil in valid_airfoils:
            self.airfoil_combo.setCurrentText(current_airfoil)
            
        self.airfoil_combo.blockSignals(False)
        
        # On lance le calcul géométrique avec la nouvelle architecture
        self.calculate_geometry()

    def calculate_geometry(self):
        try:
            # 1. Récupération des entrées textuelles
            mass = float(self.mass_input.text().replace(',', '.'))
            v_stall = float(self.vstall_input.text().replace(',', '.'))
            v_cruise = float(self.vcruise_input.text().replace(',', '.'))
            
            # 2. Récupération des sliders (division pour remettre à l'échelle)
            sweep = self.sweep_slider.value() / 10.0
            tail_arm = self.tailarm_slider.value() / 100.0
            nose = self.nose_slider.value() / 100.0
            dihedral = self.dihedral_slider.value() / 10.0
            h_sweep = self.htail_sweep_slider.value() / 10.0
            
            tail_type = self.tail_combo.currentText()
            
            # 3. Masquage dynamique de l'interface (Logique UX)
            is_flying_wing = (tail_type == "Aile Volante")
            self.tailarm_label.setVisible(not is_flying_wing)
            self.tailarm_slider.setVisible(not is_flying_wing)
            self.htail_sweep_label.setVisible(not is_flying_wing)
            self.htail_sweep_slider.setVisible(not is_flying_wing)
            
            # Mise à jour des labels des sliders
            self.sweep_label.setText(f"Angle de flèche : {sweep:.1f} °")
            self.dihedral_label.setText(f"Angle de dièdre : {dihedral:.1f} °")
            self.tailarm_label.setText(f"Bras de levier empennage : {tail_arm:.2f} m")
            self.nose_label.setText(f"Longueur du nez : {nose:.2f} m")
            self.htail_sweep_label.setText(f"Flèche empennage : {h_sweep:.1f} °")
            
            airfoil_name = self.airfoil_combo.currentText()
            selected_airfoil = self.db.get_airfoil(airfoil_name)
            if not selected_airfoil: 
                return

            # 4. Instanciation du Modèle (Calculs physiques)
            drone = Drone(mass=mass, v_stall=v_stall, v_cruise=v_cruise, 
                          airfoil=selected_airfoil, sweep_angle=sweep, 
                          dihedral_angle=dihedral, tail_arm=tail_arm, 
                          nose_length=nose, tail_type=tail_type,
                          h_tail_sweep=h_sweep)

            # 5. Mise à jour de l'interface graphique (Tableau de bord)
            self.lbl_surface.setText(f"{drone.required_surface:.3f} m²")
            self.lbl_wing_span.setText(f"{drone.main_wing.span:.2f} m")
            self.lbl_wing_root.setText(f"{drone.main_wing.root_chord:.2f} m")
            self.lbl_wing_tip.setText(f"{drone.main_wing.tip_chord:.2f} m")
            self.lbl_wing_inc.setText(f"{drone.wing_incidence:.1f}°")

            self.lbl_alert.setText("") # On efface l'alerte par défaut

            if tail_type == "Classique":
                self.lbl_tail_type.setText("Classique")
                self.lbl_tail_span.setText(f"{drone.h_tail.span:.2f} m (H)")
                self.lbl_tail_root.setText(f"{drone.h_tail.root_chord:.2f} m (H)")
                self.lbl_tail_angle.setText("N/A")
            elif tail_type == "Empennage en V":
                self.lbl_tail_type.setText("V-Tail")
                self.lbl_tail_span.setText(f"{drone.v_tail_obj.span:.2f} m")
                self.lbl_tail_root.setText(f"{drone.v_tail_obj.root_chord:.2f} m")
                self.lbl_tail_angle.setText(f"{drone.v_angle:.1f}°")
            elif tail_type == "Aile Volante":
                self.lbl_tail_type.setText("Aucun")
                self.lbl_tail_span.setText("N/A")
                self.lbl_tail_root.setText("N/A")
                self.lbl_tail_angle.setText("N/A")
                if selected_airfoil.cm_0 < 0:
                    self.lbl_alert.setText("⚠️ Profil instable (Cm0 < 0)")

            longueur_totale = nose + drone.main_wing.root_chord + (tail_arm if not is_flying_wing else 0)
            self.lbl_length.setText(f"{longueur_totale:.2f} m")
            self.lbl_np.setText(f"{drone.neutral_point_x:.3f} m")
            self.lbl_cg.setText(f"{drone.cg_x:.3f} m")

            # 6. Sauvegarde silencieuse du texte pour la fonction d'export
            self.export_text = (f"=== DIMENSIONNEMENT WYNG ===\n"
                                f"Masse: {mass}kg | V_croisière: {v_cruise}m/s | Profil: {selected_airfoil.name}\n"
                                f"Surface: {drone.required_surface:.3f} m²\n"
                                f"Aile -> Env: {drone.main_wing.span:.2f}m | Corde: {drone.main_wing.root_chord:.2f}m | Calage: {drone.wing_incidence:.1f}°\n"
                                f"Architecture: {tail_type} | Foyer: {drone.neutral_point_x:.3f}m | CG: {drone.cg_x:.3f}m")

            self.export_button.setEnabled(True)
            self._draw_drone(drone)

        except ValueError:
            # Gestion basique de l'erreur
            pass

        except ValueError:
            self.result_text.setText("⚠️ Veuillez entrer des valeurs numériques valides pour la masse et les vitesses.")
    
    def _draw_drone(self, drone):
        """Trace la géométrie du drone en vue de dessus et de face."""
        self.ax_top.clear()
        self.ax_front.clear()
        
        # ==========================================
        # 1. VUE DE DESSUS (ax_top)
        # ==========================================
        self.ax_top.set_title("Schéma 2D (Vue de dessus)")
        self.ax_top.set_ylabel("Envergure Y (m)")

        b2 = drone.main_wing.span / 2
        cr = drone.main_wing.root_chord
        ct = drone.main_wing.tip_chord
        offset = drone.main_wing.tip_offset_x
        
        x_wing = [0, offset, offset + ct, cr, offset + ct, offset]
        y_wing = [0, b2, b2, 0, -b2, -b2]
        self.ax_top.fill(x_wing, y_wing, color='skyblue', edgecolor='blue', alpha=0.6)

        if drone.tail_type != "Aile Volante":
            arm = drone.tail_arm
            hb2 = drone.h_tail.span / 2
            hcr = drone.h_tail.root_chord
            hct = drone.h_tail.tip_chord
            h_offset = drone.h_tail.tip_offset_x
            
            x_htail = [arm, arm + h_offset, arm + h_offset + hct, arm + hcr, arm + h_offset + hct, arm + h_offset]
            y_htail = [0, hb2, hb2, 0, -hb2, -hb2]
            
            if drone.tail_type == "Classique":
                self.ax_top.fill(x_htail, y_htail, color='lightcoral', edgecolor='red', alpha=0.6)
                self.ax_top.plot([arm, arm+hcr], [0, 0], color='red', linewidth=2)
            elif drone.tail_type == "Empennage en V":
                self.ax_top.fill(x_htail, y_htail, color='mediumorchid', edgecolor='purple', alpha=0.6)

        if drone.tail_type == "Aile Volante":
            self.ax_top.plot([-drone.nose_length, cr], [0, 0], color='black', linewidth=3, linestyle='-.')
        else:
            self.ax_top.plot([-drone.nose_length, arm + (drone.h_tail.root_chord if drone.h_tail else 0)], 
                             [0, 0], color='black', linewidth=3, linestyle='-.')

        self.ax_top.plot(drone.neutral_point_x, 0, marker='x', color='blue', markersize=8, markeredgewidth=2)
        self.ax_top.plot(drone.cg_x, 0, marker='o', color='black', markerfacecolor='white', markersize=8)
        self.ax_top.axis('equal')
        self.ax_top.grid(True, linestyle=':')

        # ==========================================
        # 2. VUE DE FACE (ax_front)
        # ==========================================
        self.ax_front.set_title("Élévation (Vue de face)")
        self.ax_front.set_xlabel("Envergure Y (m)")
        self.ax_front.set_ylabel("Hauteur Z (m)")
        
        # Fuselage (point central)
        self.ax_front.plot(0, 0, marker='o', color='black', markersize=10)

        # Tracé des ailes principales (Dièdre)
        z_tip = drone.main_wing.tip_offset_z
        # Demi-aile droite
        self.ax_front.plot([0, b2], [0, z_tip], color='blue', linewidth=3, label="Aile Principale")
        # Demi-aile gauche
        self.ax_front.plot([0, -b2], [0, z_tip], color='blue', linewidth=3)

        # Tracé de l'empennage de face
        if drone.tail_type == "Classique":
            # Empennage horizontal (plat)
            self.ax_front.plot([-drone.h_tail.span/2, drone.h_tail.span/2], [0, 0], color='red', linewidth=2, label="H-Tail")
            # Dérive verticale (montante)
            self.ax_front.plot([0, 0], [0, drone.v_tail.span], color='darkred', linewidth=2, label="V-Tail")
            
        elif drone.tail_type == "Empennage en V":
            # Calcul de la géométrie de face du V
            import math
            v_span = drone.v_tail_obj.span / 2
            v_angle_rad = math.radians(drone.v_angle)
            z_vtail = v_span * math.sin(v_angle_rad)
            y_vtail = v_span * math.cos(v_angle_rad)
            
            # V droit
            self.ax_front.plot([0, y_vtail], [0, z_vtail], color='purple', linewidth=2, label="V-Tail")
            # V gauche
            self.ax_front.plot([0, -y_vtail], [0, z_vtail], color='purple', linewidth=2)

        self.ax_front.axis('equal')
        self.ax_front.grid(True, linestyle=':')
        self.ax_front.legend(loc='upper right', fontsize='small')
        
        self.canvas.draw()
    
    def export_results(self):
        """Sauvegarde les résultats en format .txt et le schéma en .png."""
        # Ouvre une fenêtre de dialogue système pour choisir où enregistrer
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter la note de calcul", "Wyng_Design", "Fichier Texte (*.txt)")
        
        if file_path:
            try:
                # 1. Sauvegarde du texte
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.export_text)
                
                # 2. Sauvegarde du schéma Matplotlib
                # On remplace l'extension .txt par .png pour l'image
                image_path = file_path.replace('.txt', '.png')
                self.figure.savefig(image_path, dpi=300, bbox_inches='tight')
                
                # Confirmation utilisateur
                QMessageBox.information(self, "Export Réussi", 
                                        f"La note de calcul a été sauvegardée.\n\nTexte : {file_path}\nImage : {image_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'export", f"Impossible de sauvegarder les fichiers :\n{str(e)}")