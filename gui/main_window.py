from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QFileDialog, QMessageBox, QSlider,
                             QGroupBox, QGridLayout, QFormLayout, QTabWidget, QCheckBox)

from core.drone import Drone
from core.airfoil import AirfoilDatabase

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.setWindowIcon(QIcon('wyng.ico'))
        self.setMinimumSize(1200, 800)
        
        self.db = AirfoilDatabase()
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        self.tabs.setMaximumWidth(400)
        
        tab_general = QWidget()
        layout_general = QVBoxLayout(tab_general)
        
        self.mass_input = QLineEdit("2.5")
        self.mass_input.textChanged.connect(self.calculate_geometry)
        layout_general.addWidget(QLabel("Masse cible (kg) :"))
        layout_general.addWidget(self.mass_input)
        
        self.vstall_input = QLineEdit("10.0")
        self.vstall_input.textChanged.connect(self.calculate_geometry)
        self.lbl_vstall_title = QLabel("Vitesse décrochage (m/s) :")
        layout_general.addWidget(self.lbl_vstall_title)
        layout_general.addWidget(self.vstall_input)
        
        self.vcruise_input = QLineEdit("15.0")
        self.vcruise_input.textChanged.connect(self.calculate_geometry)
        self.lbl_vcruise_title = QLabel("Vitesse croisière (m/s) :")
        layout_general.addWidget(self.lbl_vcruise_title)
        layout_general.addWidget(self.vcruise_input)
        
        self.speed_unit_combo = QComboBox()
        self.speed_unit_combo.addItems(["m/s", "km/h"])
        self.speed_unit_combo.currentTextChanged.connect(self._on_unit_changed) 
        layout_general.addWidget(QLabel("Unité des vitesses :"))
        layout_general.addWidget(self.speed_unit_combo)
        
        self.airfoil_combo = QComboBox()
        self.airfoil_combo.addItems(self.db.list_airfoils())
        self.airfoil_combo.currentTextChanged.connect(self.calculate_geometry)
        layout_general.addWidget(QLabel("Profil de l'aile :"))
        layout_general.addWidget(self.airfoil_combo)
        
        layout_general.addStretch()
        self.tabs.addTab(tab_general, "Général")

        tab_wing = QWidget()
        layout_wing = QVBoxLayout(tab_wing)
        
        self.wing_shape_combo = QComboBox()
        self.wing_shape_combo.addItems(["Trapézoïdale", "Delta", "Lambda"])
        self.wing_shape_combo.currentTextChanged.connect(self.calculate_geometry)
        layout_wing.addWidget(QLabel("Forme de l'aile :"))
        layout_wing.addWidget(self.wing_shape_combo)
        
        self.ar_label = QLabel("Allongement (AR) : 8.0")
        self.ar_slider = self._create_slider(20, 200, 80, layout_wing, self.ar_label)
        
        self.sweep_label = QLabel("Angle de flèche : 0.0 °")
        self.sweep_slider = self._create_slider(0, 450, 0, layout_wing, self.sweep_label)
        
        self.dihedral_label = QLabel("Angle de dièdre : 0.0 °")
        self.dihedral_slider = self._create_slider(0, 150, 0, layout_wing, self.dihedral_label)
        
        self.kink_pos_label = QLabel("Position cassure : 45 %")
        self.kink_pos_slider = self._create_slider(20, 80, 45, layout_wing, self.kink_pos_label)
        
        self.kink_angle_label = QLabel("Angle de cassure (BF) : -30.0 °")
        self.kink_angle_slider = self._create_slider(-600, 600, -300, layout_wing, self.kink_angle_label)
        
        self.washout_label = QLabel("Vrillage (Washout) : 0.0 °")
        self.washout_slider = self._create_slider(-100, 0, 0, layout_wing, self.washout_label)
        
        self.winglets_cb = QCheckBox("Ajouter Winglets (Dérives de saumon)")
        self.winglets_cb.stateChanged.connect(self.calculate_geometry)
        layout_wing.addWidget(self.winglets_cb)
        
        layout_wing.addStretch()
        self.tabs.addTab(tab_wing, "Aile")

        tab_tail = QWidget()
        layout_tail = QVBoxLayout(tab_tail)
        
        self.tail_combo = QComboBox()
        self.tail_combo.addItems(["Classique", "Empennage en T", "Empennage en V", "Aile Volante"])
        self.tail_combo.currentTextChanged.connect(self._on_tail_changed)
        layout_tail.addWidget(QLabel("Architecture :"))
        layout_tail.addWidget(self.tail_combo)
        
        self.tailarm_label = QLabel("Bras de levier : 1.0 m")
        self.tailarm_slider = self._create_slider(30, 250, 100, layout_tail, self.tailarm_label)
        
        self.nose_label = QLabel("Longueur du nez : 0.2 m")
        self.nose_slider = self._create_slider(0, 100, 20, layout_tail, self.nose_label)
        
        self.htail_sweep_label = QLabel("Flèche empennage : 0.0 °")
        self.htail_sweep_slider = self._create_slider(0, 450, 0, layout_tail, self.htail_sweep_label)
        
        self.vh_label = QLabel("Volume Horizontal (Vh) : 0.50")
        self.vh_slider = self._create_slider(20, 150, 50, layout_tail, self.vh_label)
        
        self.vv_label = QLabel("Volume Vertical (Vv) : 0.040")
        self.vv_slider = self._create_slider(10, 100, 40, layout_tail, self.vv_label)
        
        layout_tail.addStretch()
        self.tabs.addTab(tab_tail, "Corps & Empennage")
        
        tab_mass = QWidget()
        layout_mass = QVBoxLayout(tab_mass)
        
        layout_mass.addWidget(QLabel("Moteur (Masse en kg puis Position X) :"))
        self.m_motor_input = QLineEdit("0.15")
        self.m_motor_input.textChanged.connect(self.calculate_geometry)
        layout_mass.addWidget(self.m_motor_input)
        self.lbl_x_motor = QLabel("Position Moteur : -0.20 m")
        self.x_motor_slider = self._create_slider(-50, 100, -20, layout_mass, self.lbl_x_motor)
        
        layout_mass.addWidget(QLabel("Batterie (Masse en kg puis Position X) :"))
        self.m_batt_input = QLineEdit("0.40")
        self.m_batt_input.textChanged.connect(self.calculate_geometry)
        layout_mass.addWidget(self.m_batt_input)
        self.lbl_x_batt = QLabel("Position Batterie : 0.00 m")
        self.x_batt_slider = self._create_slider(-50, 100, 0, layout_mass, self.lbl_x_batt)
        
        layout_mass.addWidget(QLabel("Charge Utile (Masse en kg puis Pos. X) :"))
        self.m_payload_input = QLineEdit("0.25")
        self.m_payload_input.textChanged.connect(self.calculate_geometry)
        layout_mass.addWidget(self.m_payload_input)
        self.lbl_x_payload = QLabel("Position Charge U. : 0.10 m")
        self.x_payload_slider = self._create_slider(-50, 100, 10, layout_mass, self.lbl_x_payload)
        
        layout_mass.addStretch()
        self.tabs.addTab(tab_mass, "Centrage")

        tab_propulsion = QWidget()
        layout_propulsion = QVBoxLayout(tab_propulsion)
        
        self.lbl_eta_prop = QLabel("Rendement Hélice : 70 %")
        self.eta_prop_slider = self._create_slider(40, 90, 70, layout_propulsion, self.lbl_eta_prop)
        
        self.lbl_eta_motor = QLabel("Rendement Moteur : 80 %")
        self.eta_motor_slider = self._create_slider(50, 95, 80, layout_propulsion, self.lbl_eta_motor)
        
        layout_propulsion.addStretch()
        self.tabs.addTab(tab_propulsion, "Propulsion")
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.tabs)
        
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Note de Calcul (.txt)")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        
        self.export_cad_button = QPushButton("Export CAO (.csv)")
        self.export_cad_button.clicked.connect(self.export_cad)
        self.export_cad_button.setEnabled(False)
        
        export_layout.addWidget(self.export_button)
        export_layout.addWidget(self.export_cad_button)
        left_layout.addLayout(export_layout)
        
        right_layout = QVBoxLayout()
        self.results_box = QGroupBox("Paramètres Géométriques")
        results_layout = QGridLayout()

        wing_group = QGroupBox("Aile Principale")
        wing_layout = QFormLayout()
        self.lbl_surface = QLabel("-")
        self.lbl_wing_span = QLabel("-")
        self.lbl_wing_root = QLabel("-")
        self.lbl_wing_tip = QLabel("-")
        self.lbl_wing_inc = QLabel("-")
        wing_layout.addRow("Surface :", self.lbl_surface)
        wing_layout.addRow("Envergure :", self.lbl_wing_span)
        wing_layout.addRow("Corde emplanture :", self.lbl_wing_root)
        wing_layout.addRow("Corde saumon :", self.lbl_wing_tip)
        wing_layout.addRow("Calage requis :", self.lbl_wing_inc)
        wing_group.setLayout(wing_layout)

        tail_group = QGroupBox("Empennage")
        self.tail_layout = QFormLayout()
        self.lbl_tail_type = QLabel("-")
        self.lbl_tail_span = QLabel("-")
        self.lbl_tail_root = QLabel("-")
        self.lbl_tail_angle = QLabel("-")
        self.tail_layout.addRow("Architecture :", self.lbl_tail_type)
        self.tail_layout.addRow("Envergure (H) :", self.lbl_tail_span)
        self.tail_layout.addRow("Corde emp (H) :", self.lbl_tail_root)
        self.tail_layout.addRow("Angle V-Tail :", self.lbl_tail_angle)
        tail_group.setLayout(self.tail_layout)

        stab_group = QGroupBox("Corps & Stabilité")
        stab_layout = QFormLayout()
        self.lbl_length = QLabel("-")
        self.lbl_np = QLabel("-")
        self.lbl_cg = QLabel("-")
        self.lbl_alert = QLabel("")
        self.lbl_alert.setStyleSheet("color: red; font-weight: bold;")
        stab_layout.addRow("Longueur totale :", self.lbl_length)
        stab_layout.addRow("Foyer (X_NP) :", self.lbl_np)
        stab_layout.addRow("CG cible (X_CG) :", self.lbl_cg)
        stab_layout.addRow("", self.lbl_alert)
        stab_group.setLayout(stab_layout)

        perf_group = QGroupBox("Performances de Vol (Croisière)")
        perf_layout = QFormLayout()
        self.lbl_cz = QLabel("-")
        self.lbl_finesse = QLabel("-")
        self.lbl_power = QLabel("-")
        self.lbl_thrust = QLabel("-")
        self.lbl_elec_power = QLabel("-")
        perf_layout.addRow("Cz croisière :", self.lbl_cz)
        perf_layout.addRow("Finesse estimée (L/D) :", self.lbl_finesse)
        perf_layout.addRow("Puissance aéro. :", self.lbl_power)
        perf_layout.addRow("Poussée requise :", self.lbl_thrust)
        perf_layout.addRow("Puiss. électrique :", self.lbl_elec_power)
        perf_group.setLayout(perf_layout)

        results_layout.addWidget(wing_group, 0, 0)
        results_layout.addWidget(tail_group, 0, 1)
        results_layout.addWidget(stab_group, 1, 0)
        results_layout.addWidget(perf_group, 1, 1)
        self.results_box.setLayout(results_layout)
        right_layout.addWidget(self.results_box)
        
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax_top = self.figure.add_subplot(211)
        self.ax_front = self.figure.add_subplot(212)
        self.figure.subplots_adjust(hspace=0.3)
        right_layout.addWidget(self.canvas)
        
        main_layout.addLayout(left_layout, 1) 
        main_layout.addLayout(right_layout, 3)

        self.calculate_geometry()

    def _create_slider(self, min_val, max_val, default, layout, label):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.valueChanged.connect(self.calculate_geometry)
        layout.addWidget(label)
        layout.addWidget(slider)
        return slider

    def _on_tail_changed(self):
        is_flying_wing = (self.tail_combo.currentText() == "Aile Volante")
        current_airfoil = self.airfoil_combo.currentText()
        self.airfoil_combo.blockSignals(True)
        self.airfoil_combo.clear()
        valid_airfoils = self.db.list_airfoils(require_autostable=is_flying_wing)
        self.airfoil_combo.addItems(valid_airfoils)
        if current_airfoil in valid_airfoils:
            self.airfoil_combo.setCurrentText(current_airfoil)
        self.airfoil_combo.blockSignals(False)
        self.calculate_geometry()

    def _on_unit_changed(self, new_unit):
        """Convertit les valeurs des champs texte à la volée quand l'unité change."""
        try:
            v_stall_val = float(self.vstall_input.text().replace(',', '.'))
            v_cruise_val = float(self.vcruise_input.text().replace(',', '.'))
            
            # On coupe temporairement les signaux pour ne pas lancer 20 calculs d'affilée
            self.vstall_input.blockSignals(True)
            self.vcruise_input.blockSignals(True)
            
            if new_unit == "km/h":
                self.lbl_vstall_title.setText("Vitesse décrochage (km/h) :")
                self.lbl_vcruise_title.setText("Vitesse croisière (km/h) :")
                self.vstall_input.setText(f"{v_stall_val * 3.6:.1f}")
                self.vcruise_input.setText(f"{v_cruise_val * 3.6:.1f}")
            else:
                self.lbl_vstall_title.setText("Vitesse décrochage (m/s) :")
                self.lbl_vcruise_title.setText("Vitesse croisière (m/s) :")
                self.vstall_input.setText(f"{v_stall_val / 3.6:.1f}")
                self.vcruise_input.setText(f"{v_cruise_val / 3.6:.1f}")
                
        except ValueError:
            pass # Si le champ est vide ou invalide, on ne fait rien
            
        finally:
            self.vstall_input.blockSignals(False)
            self.vcruise_input.blockSignals(False)
            self.calculate_geometry()

    def calculate_geometry(self):
        import math
        try:
            mass = float(self.mass_input.text().replace(',', '.'))
            v_stall_raw = float(self.vstall_input.text().replace(',', '.'))
            v_cruise_raw = float(self.vcruise_input.text().replace(',', '.'))
            
            if self.speed_unit_combo.currentText() == "km/h":
                v_stall = v_stall_raw / 3.6
                v_cruise = v_cruise_raw / 3.6
            else:
                v_stall = v_stall_raw
                v_cruise = v_cruise_raw
            
            ar = self.ar_slider.value() / 10.0
            sweep = self.sweep_slider.value() / 10.0
            dihedral = self.dihedral_slider.value() / 10.0
            kink_pos = self.kink_pos_slider.value() / 100.0
            kink_angle = self.kink_angle_slider.value() / 10.0
            washout = self.washout_slider.value() / 10.0
            
            tail_arm = self.tailarm_slider.value() / 100.0
            nose = self.nose_slider.value() / 100.0
            h_sweep = self.htail_sweep_slider.value() / 10.0
            vh = self.vh_slider.value() / 100.0
            vv = self.vv_slider.value() / 1000.0
            
            m_motor = float(self.m_motor_input.text().replace(',', '.'))
            m_batt = float(self.m_batt_input.text().replace(',', '.'))
            m_payload = float(self.m_payload_input.text().replace(',', '.'))
            
            x_motor = self.x_motor_slider.value() / 100.0
            x_batt = self.x_batt_slider.value() / 100.0
            x_payload = self.x_payload_slider.value() / 100.0
            
            eta_prop = self.eta_prop_slider.value() / 100.0
            eta_motor = self.eta_motor_slider.value() / 100.0
            
            tail_type = self.tail_combo.currentText()
            wing_shape = self.wing_shape_combo.currentText()
            has_winglets = self.winglets_cb.isChecked()
            
            is_flying_wing = (tail_type == "Aile Volante")
            is_lambda = (wing_shape == "Lambda")
            is_delta = (wing_shape == "Delta")
            has_tail = not is_flying_wing
            
            self.sweep_label.setVisible(not is_delta)
            self.sweep_slider.setVisible(not is_delta)
            self.washout_label.setVisible(is_flying_wing)
            self.washout_slider.setVisible(is_flying_wing)
            self.winglets_cb.setVisible(is_flying_wing)
            self.kink_pos_label.setVisible(is_lambda)
            self.kink_pos_slider.setVisible(is_lambda)
            self.kink_angle_label.setVisible(is_lambda)
            self.kink_angle_slider.setVisible(is_lambda)
            self.tailarm_label.setVisible(has_tail)
            self.tailarm_slider.setVisible(has_tail)
            self.htail_sweep_label.setVisible(has_tail)
            self.htail_sweep_slider.setVisible(has_tail)
            self.vh_label.setVisible(has_tail)
            self.vh_slider.setVisible(has_tail)
            self.vv_label.setVisible(has_tail)
            self.vv_slider.setVisible(has_tail)
            
            self.ar_label.setText(f"Allongement (AR) : {ar:.1f}")
            self.sweep_label.setText(f"Angle de flèche : {sweep:.1f} °")
            self.dihedral_label.setText(f"Angle de dièdre : {dihedral:.1f} °")
            self.kink_pos_label.setText(f"Position cassure : {kink_pos*100:.0f} %")
            self.kink_angle_label.setText(f"Angle de cassure (BF) : {kink_angle:.1f} °")
            self.washout_label.setText(f"Vrillage (Washout) : {washout:.1f} °")
            self.tailarm_label.setText(f"Bras de levier : {tail_arm:.2f} m")
            self.nose_label.setText(f"Longueur du nez : {nose:.2f} m")
            self.htail_sweep_label.setText(f"Flèche empennage : {h_sweep:.1f} °")
            self.vh_label.setText(f"Volume Horizontal (Vh) : {vh:.2f}")
            self.vv_label.setText(f"Volume Vertical (Vv) : {vv:.3f}")
            self.lbl_x_motor.setText(f"Position Moteur : {x_motor:.2f} m")
            self.lbl_x_batt.setText(f"Position Batterie : {x_batt:.2f} m")
            self.lbl_x_payload.setText(f"Position Charge U. : {x_payload:.2f} m")
            self.lbl_eta_prop.setText(f"Rendement Hélice : {eta_prop*100:.0f} %")
            self.lbl_eta_motor.setText(f"Rendement Moteur : {eta_motor*100:.0f} %")
            
            airfoil_name = self.airfoil_combo.currentText()
            selected_airfoil = self.db.get_airfoil(airfoil_name)
            if not selected_airfoil: return

            drone = Drone(mass=mass, v_stall=v_stall, v_cruise=v_cruise, airfoil=selected_airfoil, 
                          aspect_ratio=ar, sweep_angle=sweep, dihedral_angle=dihedral, 
                          tail_arm=tail_arm, nose_length=nose, tail_type=tail_type,
                          h_tail_sweep=h_sweep, wing_shape=wing_shape,
                          washout=washout, kink_pos=kink_pos, kink_angle=kink_angle,
                          vh=vh, vv=vv, has_winglets=has_winglets,
                          m_motor=m_motor, x_motor=x_motor,
                          m_batt=m_batt, x_batt=x_batt,
                          m_payload=m_payload, x_payload=x_payload,
                          eta_prop=eta_prop, eta_motor=eta_motor)

            min_x_cm = int(-nose * 100)
            if is_flying_wing:
                max_x_cm = int(drone.main_wing.root_chord * 100)
            else:
                tail_chord = drone.h_tail.root_chord if drone.h_tail else 0
                max_x_cm = int((tail_arm + tail_chord) * 100)

            self.x_motor_slider.blockSignals(True)
            self.x_batt_slider.blockSignals(True)
            self.x_payload_slider.blockSignals(True)
            
            self.x_motor_slider.setRange(min_x_cm, max_x_cm)
            self.x_batt_slider.setRange(min_x_cm, max_x_cm)
            self.x_payload_slider.setRange(min_x_cm, max_x_cm)
            
            self.x_motor_slider.blockSignals(False)
            self.x_batt_slider.blockSignals(False)
            self.x_payload_slider.blockSignals(False)

            self.lbl_surface.setText(f"{drone.required_surface:.3f} m²")
            self.lbl_wing_span.setText(f"{drone.main_wing.span:.2f} m")
            self.lbl_wing_root.setText(f"{drone.main_wing.root_chord:.2f} m")
            self.lbl_wing_tip.setText(f"{drone.main_wing.tip_chord:.2f} m")
            self.lbl_wing_inc.setText(f"{drone.wing_incidence:.1f}°")

            if tail_type in ["Classique", "Empennage en T"]:
                self.lbl_tail_type.setText(tail_type)
                self.lbl_tail_span.setText(f"{drone.h_tail.span:.2f} m")
                self.lbl_tail_root.setText(f"{drone.h_tail.root_chord:.2f} m")
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

            longueur_totale = nose + drone.main_wing.root_chord + (tail_arm if not is_flying_wing else 0)
            self.lbl_length.setText(f"{longueur_totale:.2f} m")
            self.lbl_np.setText(f"{drone.neutral_point_x:.3f} m")
            self.lbl_cg.setText(f"{drone.cg_x:.3f} m")

            self.lbl_cz.setText(f"{drone.cz_cruise:.3f}")
            self.lbl_finesse.setText(f"{drone.finesse:.1f}")
            self.lbl_power.setText(f"{drone.power_required:.1f} W")
            self.lbl_thrust.setText(f"{drone.thrust_req_g:.0f} g")
            self.lbl_elec_power.setText(f"{drone.elec_power_req:.1f} W")

            if drone.m_structure < 0:
                self.lbl_alert.setText("⚠️ AVERTISSEMENT : La somme des composants dépasse la masse totale !")
            elif drone.actual_static_margin < 5:
                self.lbl_alert.setText("⚠️ AVERTISSEMENT : Drone instable (Marge statique < 5%) !")
            elif is_flying_wing and selected_airfoil.cm_0 < 0:
                self.lbl_alert.setText("⚠️ Profil instable (Cm0 < 0)")
            else:
                self.lbl_alert.setText("")

            unit_str = self.speed_unit_combo.currentText()
            v_stall_display = self.vstall_input.text()
            v_cruise_display = self.vcruise_input.text()
            
            export_str = "=========================================\n"
            export_str += "       NOTE DE CALCUL - WYNG V1.0        \n"
            export_str += "=========================================\n\n"
            export_str += "[ PARAMÈTRES GLOBAUX ]\n"
            export_str += f"Masse cible         : {mass} kg\n"
            export_str += f"Vitesse décrochage  : {v_stall_display} {unit_str}\n"
            export_str += f"Vitesse croisière   : {v_cruise_display} {unit_str}\n"
            export_str += f"Profil aérodynamique: {selected_airfoil.name} (Cz_max = {selected_airfoil.cl_max})\n"
            export_str += f"Surface requise     : {drone.required_surface:.3f} m²\n\n"
            
            export_str += "[ AILE PRINCIPALE ]\n"
            for key, value in drone.main_wing.get_summary().items():
                export_str += f"- {key:<18}: {value}\n"
            export_str += f"- Calage requis     : {drone.wing_incidence:.1f} °\n\n"
            
            export_str += "[ EMPENNAGE ]\n"
            export_str += f"- Architecture      : {tail_type}\n"
            if tail_type in ["Classique", "Empennage en T"]:
                export_str += "  > Horizontal :\n"
                for key, value in drone.h_tail.get_summary().items():
                    export_str += f"    * {key:<14}: {value}\n"
                export_str += "  > Vertical :\n"
                for key, value in drone.v_tail.get_summary().items():
                    export_str += f"    * {key:<14}: {value}\n"
            elif tail_type == "Empennage en V":
                export_str += f"  > Angle d'ouverture : {drone.v_angle:.1f} °\n"
                for key, value in drone.v_tail_obj.get_summary().items():
                    export_str += f"    * {key:<14}: {value}\n"
            
            self.export_text = export_str
            self.export_button.setEnabled(True)
            
            # --- GÉNÉRATION DES DONNÉES CAO ---
            cad_str = "Section;Y_Envergure_m;X_Bord_Attaque_m;Z_Elevation_m;Corde_m\n"
            cad_str += f"Emplanture;0.000;0.000;0.000;{drone.main_wing.root_chord:.4f}\n"
            
            if wing_shape == "Lambda":
                y_kink = drone.main_wing.outline_y[1]
                x_kink_le = drone.main_wing.outline_x[1]
                x_kink_te = drone.main_wing.outline_x[4]
                c_kink = x_kink_te - x_kink_le
                z_kink = y_kink * math.tan(drone.main_wing.dihedral_angle_rad)
                cad_str += f"Cassure;{y_kink:.4f};{x_kink_le:.4f};{z_kink:.4f};{c_kink:.4f}\n"
                
            b2 = drone.main_wing.span / 2
            tip_x = drone.main_wing.tip_offset_x
            tip_z = drone.main_wing.tip_offset_z
            tip_c = drone.main_wing.tip_chord
            cad_str += f"Saumon;{b2:.4f};{tip_x:.4f};{tip_z:.4f};{tip_c:.4f}\n"
            
            self.export_cad_text = cad_str
            self.export_cad_button.setEnabled(True)
            
            self._draw_drone(drone)

        except ValueError:
            pass

    def _draw_drone(self, drone):
        self.ax_top.clear()
        self.ax_front.clear()
        
        b2 = drone.main_wing.span / 2
        cr = drone.main_wing.root_chord

        # 1. VUE DE DESSUS
        self.ax_top.set_title("Schéma 2D (Vue de dessus)")
        self.ax_top.set_ylabel("Envergure Y (m)")

        x_right = drone.main_wing.outline_x
        y_right = drone.main_wing.outline_y
        x_left = x_right[::-1] 
        y_left = [-y for y in y_right[::-1]]
        x_wing_full = x_right + x_left
        y_wing_full = y_right + y_left
        
        self.ax_top.fill(x_wing_full, y_wing_full, color='skyblue', edgecolor='blue', alpha=0.6)

        if drone.tail_type != "Aile Volante":
            arm = drone.tail_arm
            hb2 = drone.h_tail.span / 2
            hcr = drone.h_tail.root_chord
            hct = drone.h_tail.tip_chord
            h_offset = drone.h_tail.tip_offset_x 
            
            x_htail = [arm, arm + h_offset, arm + h_offset + hct, arm + hcr, arm + h_offset + hct, arm + h_offset]
            y_htail = [0, hb2, hb2, 0, -hb2, -hb2]
            
            if drone.tail_type in ["Classique", "Empennage en T"]:
                self.ax_top.fill(x_htail, y_htail, color='lightcoral', edgecolor='red', alpha=0.6)
                self.ax_top.plot([arm, arm+hcr], [0, 0], color='red', linewidth=2)
            elif drone.tail_type == "Empennage en V":
                self.ax_top.fill(x_htail, y_htail, color='mediumorchid', edgecolor='purple', alpha=0.6)

        if drone.tail_type == "Aile Volante":
            self.ax_top.plot([-drone.nose_length, cr], [0, 0], color='black', linewidth=3, linestyle='-.')
        else:
            self.ax_top.plot([-drone.nose_length, arm + (drone.h_tail.root_chord if drone.h_tail else 0)], 
                             [0, 0], color='black', linewidth=3, linestyle='-.')

        # Tracé des points de référence aérodynamiques
        self.ax_top.plot(drone.neutral_point_x, 0, marker='x', color='blue', markersize=8, markeredgewidth=2, label="Foyer (NP)")
        # On ajoute le label "CG Cible" au rond blanc
        self.ax_top.plot(drone.cg_x, 0, marker='o', color='black', markerfacecolor='white', markersize=8, label="CG Cible (Idéal)")
        
        # Tracé des composants internes
        self.ax_top.plot(drone.x_motor, 0, marker='s', color='orange', markersize=10, label="Moteur")
        self.ax_top.plot(drone.x_batt, 0, marker='s', color='green', markersize=12, label="Batterie")
        self.ax_top.plot(drone.x_payload, 0, marker='^', color='cyan', markersize=10, label="Charge Utile")
        
        # Tracé du CG RÉEL (Cible rouge)
        self.ax_top.plot(drone.actual_cg_x, 0, marker='+', color='red', markersize=15, markeredgewidth=3, label="CG Réel (Masses)")
        
        self.ax_top.axis('equal')
        self.ax_top.grid(True, linestyle=':')
        self.ax_top.legend(loc='upper right', fontsize='small') # Force l'affichage de la légende

        # 2. VUE DE FACE
        self.ax_front.set_title("Élévation (Vue de face)")
        self.ax_front.set_xlabel("Envergure Y (m)")
        self.ax_front.set_ylabel("Hauteur Z (m)")
        
        self.ax_front.plot(0, 0, marker='o', color='black', markersize=10)

        z_tip = drone.main_wing.tip_offset_z
        self.ax_front.plot([0, b2], [0, z_tip], color='blue', linewidth=3, label="Aile Principale")
        self.ax_front.plot([0, -b2], [0, z_tip], color='blue', linewidth=3)
        
        # Dessin des Winglets
        if drone.main_wing.has_winglets:
            winglet_h = b2 * 0.15
            self.ax_front.plot([b2, b2], [z_tip, z_tip + winglet_h], color='darkblue', linewidth=2, label="Winglet")
            self.ax_front.plot([-b2, -b2], [z_tip, z_tip + winglet_h], color='darkblue', linewidth=2)

        if drone.tail_type == "Classique":
            self.ax_front.plot([-drone.h_tail.span/2, drone.h_tail.span/2], [0, 0], color='red', linewidth=2, label="H-Tail")
            self.ax_front.plot([0, 0], [0, drone.v_tail.span], color='darkred', linewidth=2, label="V-Tail")
            
        elif drone.tail_type == "Empennage en T":
            # Le H-Tail est perché tout en haut du V-Tail
            z_htail = drone.v_tail.span
            self.ax_front.plot([0, 0], [0, z_htail], color='darkred', linewidth=2, label="V-Tail")
            self.ax_front.plot([-drone.h_tail.span/2, drone.h_tail.span/2], [z_htail, z_htail], color='red', linewidth=2, label="H-Tail")

        elif drone.tail_type == "Empennage en V":
            import math
            v_span = drone.v_tail_obj.span / 2
            v_angle_rad = math.radians(drone.v_angle)
            z_vtail = v_span * math.sin(v_angle_rad)
            y_vtail = v_span * math.cos(v_angle_rad)
            
            self.ax_front.plot([0, y_vtail], [0, z_vtail], color='purple', linewidth=2, label="V-Tail")
            self.ax_front.plot([0, -y_vtail], [0, z_vtail], color='purple', linewidth=2)

        self.ax_front.axis('equal')
        self.ax_front.grid(True, linestyle=':')
        self.ax_front.legend(loc='upper right', fontsize='small')
        
        self.canvas.draw()

    def export_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.export_text)
                QMessageBox.information(self, "Succès", "Fichier exporté avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'exportation : {e}")
                
    def export_cad(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder les sections CAO", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.export_cad_text)
                QMessageBox.information(self, "Succès", "Données CAO exportées avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'exportation CAO : {e}")