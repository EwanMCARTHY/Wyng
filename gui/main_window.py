from PyQt6.QtCore import Qt
import math
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton,
                             QMessageBox, QSlider, QCheckBox,
                             QGroupBox, QGridLayout, QFormLayout, QTabWidget,
                             QApplication, QListWidget, QStackedWidget, QProgressBar)

from core.drone import Drone
from core.airfoil import AirfoilDatabase
from core.optimizer import GeneticOptimizer
from gui.plot_manager import PlotManager
from gui.file_manager import FileManager # Import de notre nouveau gestionnaire de fichiers !

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.setWindowIcon(QIcon('wyng.ico'))
        self.setMinimumSize(1450, 900) 
        
        self.db = AirfoilDatabase()
        self.plot_manager = PlotManager() 
        self.optimizer_thread = None
        
        self.export_text = ""
        self.export_cad_text = ""
        
        self._setup_ui()
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
        try:
            v_stall_val = float(self.vstall_input.text().replace(',', '.'))
            v_cruise_val = float(self.vcruise_input.text().replace(',', '.'))
            
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
            pass
        finally:
            self.vstall_input.blockSignals(False)
            self.vcruise_input.blockSignals(False)
            self.calculate_geometry()

    def reset_3d_view(self):
        self.plot_manager.reset_3d_view()
        self.calculate_geometry()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        left_main_layout = QVBoxLayout()
        
        project_layout = QHBoxLayout()
        self.btn_load_proj = QPushButton("Ouvrir Projet")
        self.btn_load_proj.clicked.connect(self.load_project)
        self.btn_save_proj = QPushButton("Sauvegarder Projet")
        self.btn_save_proj.clicked.connect(self.save_project)
        project_layout.addWidget(self.btn_load_proj)
        project_layout.addWidget(self.btn_save_proj)
        left_main_layout.addLayout(project_layout)
        
        settings_layout = QHBoxLayout()
        
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(220) 
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.nav_list.setStyleSheet("""
            QListWidget { border: 1px solid #1e1e1e; border-radius: 5px; background-color: #2b2b2b; outline: none; }
            QListWidget::item { padding: 12px 15px; border-bottom: 1px solid #3a3a3a; color: #e0e0e0; font-weight: bold; }
            QListWidget::item:selected { background-color: #0078d7; color: white; border-bottom: 1px solid #005a9e; }
            QListWidget::item:hover:!selected { background-color: #3e3e42; }
        """)
        
        self.stacked_widget = QStackedWidget()
        
        # --- TAB: GENERAL ---
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
        
        # --- TAB: WING ---
        tab_wing = QWidget()
        layout_wing = QVBoxLayout(tab_wing)
        self.wing_shape_combo = QComboBox()
        self.wing_shape_combo.addItems(["Droite", "Trapézoïdale", "Delta", "Lambda"])
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
        
        # --- TAB: TAIL ---
        tab_tail = QWidget()
        layout_tail = QVBoxLayout(tab_tail)
        self.tail_combo = QComboBox()
        self.tail_combo.addItems(["Classique", "Empennage en T", "Empennage en V", "Aile Volante"])
        self.tail_combo.currentTextChanged.connect(self._on_tail_changed)
        layout_tail.addWidget(QLabel("Architecture :"))
        layout_tail.addWidget(self.tail_combo)
        self.lbl_htail_shape = QLabel("Forme de l'empennage H. :")
        self.htail_shape_combo = QComboBox()
        self.htail_shape_combo.addItems(["Droite", "Trapézoïdale", "Delta"])
        self.htail_shape_combo.currentTextChanged.connect(self.calculate_geometry)
        layout_tail.addWidget(self.lbl_htail_shape)
        layout_tail.addWidget(self.htail_shape_combo)
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
        
        # --- TAB: MASS ---
        tab_mass = QWidget()
        layout_mass = QVBoxLayout(tab_mass)
        layout_mass.addWidget(QLabel("Configuration Moteurs :"))
        self.motor_config_combo = QComboBox()
        self.motor_config_combo.addItems(["Monomoteur", "Bimoteur"])
        self.motor_config_combo.currentTextChanged.connect(self.calculate_geometry)
        layout_mass.addWidget(self.motor_config_combo)
        layout_mass.addWidget(QLabel("Moteur (Masse unitaire en kg puis Pos. X) :"))
        self.m_motor_input = QLineEdit("0.15")
        self.m_motor_input.textChanged.connect(self.calculate_geometry)
        layout_mass.addWidget(self.m_motor_input)
        self.lbl_x_motor = QLabel("Position Moteur : -0.20 m")
        self.x_motor_slider = self._create_slider(-50, 100, -20, layout_mass, self.lbl_x_motor)
        self.lbl_y_motor = QLabel("Position Y Moteurs : 0.00 m")
        self.y_motor_slider = self._create_slider(0, 100, 20, layout_mass, self.lbl_y_motor)
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

        # --- TAB: PROPULSION ---
        tab_propulsion = QWidget()
        layout_propulsion = QVBoxLayout(tab_propulsion)
        self.lbl_eta_prop = QLabel("Rendement Hélice : 70 %")
        self.eta_prop_slider = self._create_slider(40, 90, 70, layout_propulsion, self.lbl_eta_prop)
        self.lbl_eta_motor = QLabel("Rendement Moteur : 80 %")
        self.eta_motor_slider = self._create_slider(50, 95, 80, layout_propulsion, self.lbl_eta_motor)
        layout_propulsion.addStretch()
        
        # --- TAB: OPTIMISATION ---
        tab_opti = QWidget()
        layout_opti = QVBoxLayout(tab_opti)
        layout_opti.addWidget(QLabel("Objectif d'optimisation :"))
        self.opti_target_combo = QComboBox()
        self.opti_target_combo.addItems([
            "Maximiser la Finesse globale (L/D)",
            "Minimiser la Puissance requise (Autonomie)",
            "Maximiser la Marge Statique (Stabilité)"
        ])
        layout_opti.addWidget(self.opti_target_combo)
        layout_opti.addWidget(QLabel("Contrainte : Envergure maximale (m) :"))
        self.max_span_input = QLineEdit("2.0")
        layout_opti.addWidget(self.max_span_input)
        
        self.btn_run_opti = QPushButton("Exécuter le Solveur Génétique")
        self.btn_run_opti.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_run_opti.clicked.connect(self.run_ai_optimization)
        layout_opti.addWidget(self.btn_run_opti)
        
        self.opti_progress = QProgressBar()
        self.opti_progress.setValue(0)
        self.opti_progress.setTextVisible(True)
        layout_opti.addWidget(self.opti_progress)
        
        self.lbl_opti_results = QLabel("Solveur en attente.")
        self.lbl_opti_results.setStyleSheet("color: #333; font-style: italic;")
        layout_opti.addWidget(self.lbl_opti_results)
        
        layout_opti.addWidget(self.plot_manager.canvas_opti)
        layout_opti.addStretch() 

        # --- ASSEMBLAGE GAUCHE ---
        self.stacked_widget.addWidget(tab_general)
        self.stacked_widget.addWidget(tab_wing)
        self.stacked_widget.addWidget(tab_tail)
        self.stacked_widget.addWidget(tab_mass)
        self.stacked_widget.addWidget(tab_propulsion)
        self.stacked_widget.addWidget(tab_opti)
        
        self.nav_list.addItems(["Général", "Aile Principale", "Empennage", "Masses & Centrage", "Propulsion", "Optimisation"])
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        settings_layout.addWidget(self.nav_list)
        settings_layout.addWidget(self.stacked_widget)
        left_main_layout.addLayout(settings_layout)
        
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Note de Calcul (.txt)")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        self.export_cad_button = QPushButton("Export CAO (.csv)")
        self.export_cad_button.clicked.connect(self.export_cad)
        self.export_cad_button.setEnabled(False)
        export_layout.addWidget(self.export_button)
        export_layout.addWidget(self.export_cad_button)
        left_main_layout.addLayout(export_layout)
        
        # --- ASSEMBLAGE DROITE (Résultats & Graphiques) ---
        right_layout = QVBoxLayout()
        self.results_box = QGroupBox("Paramètres Géométriques")
        results_layout = QGridLayout()

        wing_group = QGroupBox("Aile Principale")
        wing_layout = QFormLayout()
        self.lbl_surface, self.lbl_wing_span, self.lbl_wing_root = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_wing_tip, self.lbl_wing_inc = QLabel("-"), QLabel("-")
        wing_layout.addRow("Surface :", self.lbl_surface)
        wing_layout.addRow("Envergure :", self.lbl_wing_span)
        wing_layout.addRow("Corde emplanture :", self.lbl_wing_root)
        wing_layout.addRow("Corde saumon :", self.lbl_wing_tip)
        wing_layout.addRow("Calage requis :", self.lbl_wing_inc)
        wing_group.setLayout(wing_layout)

        tail_group = QGroupBox("Empennage")
        self.tail_layout = QFormLayout()
        self.lbl_tail_type, self.lbl_tail_span, self.lbl_tail_root = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_vtail_span, self.lbl_vtail_root, self.lbl_tail_angle = QLabel("-"), QLabel("-"), QLabel("-")
        self.tail_layout.addRow("Architecture :", self.lbl_tail_type)
        self.tail_layout.addRow("Envergure (H) :", self.lbl_tail_span)
        self.tail_layout.addRow("Corde emp (H) :", self.lbl_tail_root)
        self.tail_layout.addRow("Envergure (V) :", self.lbl_vtail_span)
        self.tail_layout.addRow("Corde emp (V) :", self.lbl_vtail_root)
        self.tail_layout.addRow("Angle V-Tail :", self.lbl_tail_angle)
        tail_group.setLayout(self.tail_layout)

        stab_group = QGroupBox("Corps & Stabilité")
        stab_layout = QFormLayout()
        self.lbl_length, self.lbl_np, self.lbl_cg = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_alert = QLabel("")
        self.lbl_alert.setStyleSheet("color: red; font-weight: bold;")
        stab_layout.addRow("Longueur totale :", self.lbl_length)
        stab_layout.addRow("Foyer (X_NP) :", self.lbl_np)
        stab_layout.addRow("CG cible (X_CG) :", self.lbl_cg)
        stab_layout.addRow("", self.lbl_alert)
        stab_group.setLayout(stab_layout)

        perf_group = QGroupBox("Performances de Vol (Croisière)")
        perf_layout = QFormLayout()
        self.lbl_cz, self.lbl_finesse, self.lbl_power = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_thrust, self.lbl_elec_power = QLabel("-"), QLabel("-")
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
        
        self.plot_tabs = QTabWidget()
        
        self.tab_3d = QWidget()
        layout_3d = QVBoxLayout(self.tab_3d)
        layout_3d.addWidget(self.plot_manager.canvas_3d)
        self.btn_reset_view = QPushButton("Réinitialiser la vue 3D")
        self.btn_reset_view.clicked.connect(self.reset_3d_view)
        layout_3d.addWidget(self.btn_reset_view)
        
        self.tab_vn = QWidget()
        layout_vn = QVBoxLayout(self.tab_vn)
        layout_vn.addWidget(self.plot_manager.canvas_vn)
        
        self.tab_polars = QWidget()
        layout_polars = QVBoxLayout(self.tab_polars)
        layout_polars.addWidget(self.plot_manager.canvas_polars)
        
        self.tab_struct = QWidget()
        layout_struct = QVBoxLayout(self.tab_struct)
        layout_struct.addWidget(self.plot_manager.canvas_struct)
        
        self.plot_tabs.addTab(self.tab_3d, "Vue 3D")
        self.plot_tabs.addTab(self.tab_vn, "Diagramme V-n")
        self.plot_tabs.addTab(self.tab_polars, "Polaires Aéro")
        self.plot_tabs.addTab(self.tab_struct, "Structure")
        
        right_layout.addWidget(self.plot_tabs)
        
        main_layout.addLayout(left_main_layout, 2) 
        main_layout.addLayout(right_layout, 3)     

    def calculate_geometry(self, force_reset_view=True):
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
            
            num_motors = 1 if self.motor_config_combo.currentText() == "Monomoteur" else 2
            m_motor = float(self.m_motor_input.text().replace(',', '.'))
            m_batt = float(self.m_batt_input.text().replace(',', '.'))
            m_payload = float(self.m_payload_input.text().replace(',', '.'))
            
            x_motor = self.x_motor_slider.value() / 100.0
            y_motor = self.y_motor_slider.value() / 100.0
            x_batt = self.x_batt_slider.value() / 100.0
            x_payload = self.x_payload_slider.value() / 100.0
            
            eta_prop = self.eta_prop_slider.value() / 100.0
            eta_motor = self.eta_motor_slider.value() / 100.0
            
            tail_type = self.tail_combo.currentText()
            wing_shape = self.wing_shape_combo.currentText()
            htail_shape = self.htail_shape_combo.currentText()
            has_winglets = self.winglets_cb.isChecked()
            
            is_flying_wing = (tail_type == "Aile Volante")
            is_lambda = (wing_shape == "Lambda")
            is_delta = (wing_shape == "Delta")
            has_tail = not is_flying_wing
            is_bimotor = (num_motors == 2)
            
            self.sweep_label.setVisible(not is_delta)
            self.sweep_slider.setVisible(not is_delta)
            self.washout_label.setVisible(is_flying_wing)
            self.washout_slider.setVisible(is_flying_wing)
            self.winglets_cb.setVisible(is_flying_wing)
            self.kink_pos_label.setVisible(is_lambda)
            self.kink_pos_slider.setVisible(is_lambda)
            self.kink_angle_label.setVisible(is_lambda)
            self.kink_angle_slider.setVisible(is_lambda)
            
            self.lbl_htail_shape.setVisible(has_tail)
            self.htail_shape_combo.setVisible(has_tail)
            self.tailarm_label.setVisible(has_tail)
            self.tailarm_slider.setVisible(has_tail)
            self.htail_sweep_label.setVisible(has_tail)
            self.htail_sweep_slider.setVisible(has_tail)
            self.vh_label.setVisible(has_tail)
            self.vh_slider.setVisible(has_tail)
            self.vv_label.setVisible(has_tail)
            self.vv_slider.setVisible(has_tail)
            
            self.lbl_y_motor.setVisible(is_bimotor)
            self.y_motor_slider.setVisible(is_bimotor)
            
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
            self.lbl_y_motor.setText(f"Position Y Moteurs : {y_motor:.2f} m")
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
                          h_tail_sweep=h_sweep, wing_shape=wing_shape, htail_shape=htail_shape,
                          washout=washout, kink_pos=kink_pos, kink_angle=kink_angle,
                          vh=vh, vv=vv, has_winglets=has_winglets,
                          m_motor=m_motor, x_motor=x_motor,
                          num_motors=num_motors, y_motor=y_motor,
                          m_batt=m_batt, x_batt=x_batt,
                          m_payload=m_payload, x_payload=x_payload,
                          eta_prop=eta_prop, eta_motor=eta_motor)

            min_x_cm = int(-nose * 100)
            if is_flying_wing:
                max_x_cm = int(drone.main_wing.root_chord * 100)
            else:
                tail_chord = drone.h_tail.root_chord if drone.h_tail else 0
                max_x_cm = int((tail_arm + tail_chord) * 100)
                
            max_y_cm = int(drone.main_wing.span / 2 * 100)

            self.x_motor_slider.blockSignals(True)
            self.y_motor_slider.blockSignals(True)
            self.x_batt_slider.blockSignals(True)
            self.x_payload_slider.blockSignals(True)
            
            self.x_motor_slider.setRange(min_x_cm, max_x_cm)
            self.y_motor_slider.setRange(0, max_y_cm)
            self.x_batt_slider.setRange(min_x_cm, max_x_cm)
            self.x_payload_slider.setRange(min_x_cm, max_x_cm)
            
            self.x_motor_slider.blockSignals(False)
            self.y_motor_slider.blockSignals(False)
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
                self.lbl_vtail_span.setText(f"{drone.v_tail.span:.2f} m")
                self.lbl_vtail_root.setText(f"{drone.v_tail.root_chord:.2f} m")
                self.lbl_tail_angle.setText("N/A")
            elif tail_type == "Empennage en V":
                self.lbl_tail_type.setText("V-Tail")
                self.lbl_tail_span.setText(f"{drone.v_tail_obj.span:.2f} m")
                self.lbl_tail_root.setText(f"{drone.v_tail_obj.root_chord:.2f} m")
                self.lbl_vtail_span.setText("N/A")
                self.lbl_vtail_root.setText("N/A")
                self.lbl_tail_angle.setText(f"{drone.v_angle:.1f}°")
            elif tail_type == "Aile Volante":
                self.lbl_tail_type.setText("Aucun")
                self.lbl_tail_span.setText("N/A")
                self.lbl_tail_root.setText("N/A")
                self.lbl_vtail_span.setText("N/A")
                self.lbl_vtail_root.setText("N/A")
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

            # --- GÉNÉRATION DE LA NOTE DE CALCUL ---
            unit_str = self.speed_unit_combo.currentText()
            v_stall_display = self.vstall_input.text()
            v_cruise_display = self.vcruise_input.text()
            
            export_str = "=========================================\n"
            export_str += "       NOTE DE CALCUL - WYNG V1.0        \n"
            export_str += "   Conçu par : Ewan Mac-Carthy (ENSAM)   \n"
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
            
            # --- GÉNÉRATION DE L'EXPORT CAO ---
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
            
            # Délégation graphique pure
            self.plot_manager.draw_drone(drone, force_reset=force_reset_view)
            self.plot_manager.draw_vn(drone)
            self.plot_manager.draw_polars(drone)
            self.plot_manager.draw_structure(drone)

        except ValueError:
            pass

    def run_ai_optimization(self):
        self.btn_run_opti.setEnabled(False)
        self.lbl_opti_results.setStyleSheet("color: #0078d7; font-weight: bold;")
        self.lbl_opti_results.setText("Initialisation du solveur...")
        self.plot_manager.clear_opti_plot()
        
        try:
            max_span = float(self.max_span_input.text().replace(',', '.'))
            mass = float(self.mass_input.text().replace(',', '.'))
            v_stall_raw = float(self.vstall_input.text().replace(',', '.'))
            v_cruise_raw = float(self.vcruise_input.text().replace(',', '.'))
            v_stall = v_stall_raw / 3.6 if self.speed_unit_combo.currentText() == "km/h" else v_stall_raw
            v_cruise = v_cruise_raw / 3.6 if self.speed_unit_combo.currentText() == "km/h" else v_cruise_raw
            
            drone_params = {
                'mass': mass, 'v_stall': v_stall, 'v_cruise': v_cruise,
                'tail_arm': self.tailarm_slider.value() / 100.0,
                'nose_length': self.nose_slider.value() / 100.0,
                'tail_type': self.tail_combo.currentText(),
                'h_tail_sweep': self.htail_sweep_slider.value() / 10.0,
                'wing_shape': self.wing_shape_combo.currentText(),
                'htail_shape': self.htail_shape_combo.currentText(),
                'kink_pos': self.kink_pos_slider.value() / 100.0,
                'kink_angle': self.kink_angle_slider.value() / 10.0,
                'vh': self.vh_slider.value() / 100.0,
                'vv': self.vv_slider.value() / 1000.0,
                'has_winglets': self.winglets_cb.isChecked(),
                'm_motor': float(self.m_motor_input.text().replace(',', '.')),
                'x_motor': self.x_motor_slider.value() / 100.0,
                'num_motors': 1 if self.motor_config_combo.currentText() == "Monomoteur" else 2,
                'y_motor': self.y_motor_slider.value() / 100.0,
                'm_batt': float(self.m_batt_input.text().replace(',', '.')),
                'm_payload': float(self.m_payload_input.text().replace(',', '.')),
                'x_payload': self.x_payload_slider.value() / 100.0,
                'eta_prop': self.eta_prop_slider.value() / 100.0,
                'eta_motor': self.eta_motor_slider.value() / 100.0
            }
            
            min_xbatt = self.x_batt_slider.minimum() / 100.0
            max_xbatt = self.x_batt_slider.maximum() / 100.0
            selected_airfoil = self.db.get_airfoil(self.airfoil_combo.currentText())
            target_mode = self.opti_target_combo.currentText()
            
        except Exception:
            self.lbl_opti_results.setText("Erreur : Vérifiez vos données d'entrée.")
            self.btn_run_opti.setEnabled(True)
            return

        self.opti_progress.setMaximum(30)
        self.opti_progress.setValue(0)
        
        # On passe la main à notre QThread
        self.optimizer_thread = GeneticOptimizer(
            target_mode, max_span, drone_params, selected_airfoil, min_xbatt, max_xbatt
        )
        
        self.optimizer_thread.progress_signal.connect(self._on_opti_progress)
        self.optimizer_thread.plot_signal.connect(self.plot_manager.update_opti_plot)
        self.optimizer_thread.finished_signal.connect(self._on_opti_finished)
        self.optimizer_thread.error_signal.connect(self._on_opti_error)
        
        self.optimizer_thread.start()

    def _on_opti_progress(self, val, msg):
        self.opti_progress.setValue(val)
        self.lbl_opti_results.setText(msg)

    def _on_opti_error(self, msg):
        self.lbl_opti_results.setStyleSheet("color: red; font-weight: bold;")
        self.lbl_opti_results.setText(f"Erreur IA : {msg}")
        self.btn_run_opti.setEnabled(True)

    def _on_opti_finished(self, best_genes, best_fitness):
        self.lbl_opti_results.setStyleSheet("color: green; font-weight: bold;")
        self.lbl_opti_results.setText(f"Conception générative terminée ! Score : {best_fitness:.2f}")
        
        if best_genes:
            self.ar_slider.blockSignals(True)
            self.sweep_slider.blockSignals(True)
            self.dihedral_slider.blockSignals(True)
            self.washout_slider.blockSignals(True)
            self.x_batt_slider.blockSignals(True)
            
            self.ar_slider.setValue(int(best_genes[0] * 10))
            self.sweep_slider.setValue(int(best_genes[1] * 10))
            self.dihedral_slider.setValue(int(best_genes[2] * 10))
            self.washout_slider.setValue(int(best_genes[3] * 10))
            self.x_batt_slider.setValue(int(best_genes[4] * 100))
            
            self.ar_slider.blockSignals(False)
            self.sweep_slider.blockSignals(False)
            self.dihedral_slider.blockSignals(False)
            self.washout_slider.blockSignals(False)
            self.x_batt_slider.blockSignals(False)
            
            self.plot_manager.view_needs_reset = False
            self.calculate_geometry(force_reset_view=False)
            
        self.btn_run_opti.setEnabled(True)

    # --- DÉLÉGATION AU FILE MANAGER ---
    def export_results(self):
        if hasattr(self, 'export_text'):
            FileManager.export_results(self, self.export_text)

    def export_cad(self):
        if hasattr(self, 'export_cad_text'):
            FileManager.export_cad(self, self.export_cad_text)

    def save_project(self):
        state = {
            'mass': self.mass_input.text(),
            'v_stall': self.vstall_input.text(),
            'v_cruise': self.vcruise_input.text(),
            'speed_unit': self.speed_unit_combo.currentText(),
            'airfoil': self.airfoil_combo.currentText(),
            'wing_shape': self.wing_shape_combo.currentText(),
            'ar': self.ar_slider.value(),
            'sweep': self.sweep_slider.value(),
            'dihedral': self.dihedral_slider.value(),
            'kink_pos': self.kink_pos_slider.value(),
            'kink_angle': self.kink_angle_slider.value(),
            'washout': self.washout_slider.value(),
            'has_winglets': self.winglets_cb.isChecked(),
            'tail_type': self.tail_combo.currentText(),
            'htail_shape': self.htail_shape_combo.currentText(),
            'tail_arm': self.tailarm_slider.value(),
            'nose': self.nose_slider.value(),
            'h_sweep': self.htail_sweep_slider.value(),
            'vh': self.vh_slider.value(),
            'vv': self.vv_slider.value(),
            'motor_config': self.motor_config_combo.currentText(),
            'm_motor': self.m_motor_input.text(),
            'x_motor': self.x_motor_slider.value(),
            'y_motor': self.y_motor_slider.value(),
            'm_batt': self.m_batt_input.text(),
            'x_batt': self.x_batt_slider.value(),
            'm_payload': self.m_payload_input.text(),
            'x_payload': self.x_payload_slider.value(),
            'eta_prop': self.eta_prop_slider.value(),
            'eta_motor': self.eta_motor_slider.value(),
            'opti_target': self.opti_target_combo.currentText(),
            'opti_span': self.max_span_input.text()
        }
        FileManager.save_project(self, state)

    def load_project(self):
        state = FileManager.load_project(self)
        if state:
            widgets = [
                self.mass_input, self.vstall_input, self.vcruise_input, self.speed_unit_combo,
                self.airfoil_combo, self.wing_shape_combo, self.ar_slider, self.sweep_slider,
                self.dihedral_slider, self.kink_pos_slider, self.kink_angle_slider, self.washout_slider,
                self.winglets_cb, self.tail_combo, self.htail_shape_combo, self.tailarm_slider, self.nose_slider,
                self.htail_sweep_slider, self.vh_slider, self.vv_slider, self.motor_config_combo, 
                self.m_motor_input, self.x_motor_slider, self.y_motor_slider, self.m_batt_input, 
                self.x_batt_slider, self.m_payload_input, self.x_payload_slider, 
                self.eta_prop_slider, self.eta_motor_slider, self.opti_target_combo
            ]
            
            for w in widgets:
                w.blockSignals(True)
            
            self.mass_input.setText(state.get('mass', '2.5'))
            self.vstall_input.setText(state.get('v_stall', '10.0'))
            self.vcruise_input.setText(state.get('v_cruise', '15.0'))
            self.speed_unit_combo.setCurrentText(state.get('speed_unit', 'm/s'))
            self.tail_combo.setCurrentText(state.get('tail_type', 'Classique'))
            self.htail_shape_combo.setCurrentText(state.get('htail_shape', 'Trapézoïdale'))
            
            is_flying_wing = (self.tail_combo.currentText() == "Aile Volante")
            self.airfoil_combo.clear()
            self.airfoil_combo.addItems(self.db.list_airfoils(require_autostable=is_flying_wing))
            self.airfoil_combo.setCurrentText(state.get('airfoil', 'Clark Y'))
            
            self.wing_shape_combo.setCurrentText(state.get('wing_shape', 'Trapézoïdale'))
            self.ar_slider.setValue(state.get('ar', 80))
            self.sweep_slider.setValue(state.get('sweep', 0))
            self.dihedral_slider.setValue(state.get('dihedral', 0))
            self.kink_pos_slider.setValue(state.get('kink_pos', 45))
            self.kink_angle_slider.setValue(state.get('kink_angle', -300))
            self.washout_slider.setValue(state.get('washout', 0))
            self.winglets_cb.setChecked(state.get('has_winglets', False))
            self.tailarm_slider.setValue(state.get('tail_arm', 100))
            self.nose_slider.setValue(state.get('nose', 20))
            self.htail_sweep_slider.setValue(state.get('h_sweep', 0))
            self.vh_slider.setValue(state.get('vh', 50))
            self.vv_slider.setValue(state.get('vv', 40))
            self.motor_config_combo.setCurrentText(state.get('motor_config', 'Monomoteur'))
            self.m_motor_input.setText(state.get('m_motor', '0.15'))
            self.x_motor_slider.setValue(state.get('x_motor', -20))
            self.y_motor_slider.setValue(state.get('y_motor', 0))
            self.m_batt_input.setText(state.get('m_batt', '0.40'))
            self.x_batt_slider.setValue(state.get('x_batt', 0))
            self.m_payload_input.setText(state.get('m_payload', '0.25'))
            self.x_payload_slider.setValue(state.get('x_payload', 10))
            self.eta_prop_slider.setValue(state.get('eta_prop', 70))
            self.eta_motor_slider.setValue(state.get('eta_motor', 80))
            
            if 'opti_target' in state:
                self.opti_target_combo.setCurrentText(state['opti_target'])
            if 'opti_span' in state:
                self.max_span_input.setText(state['opti_span'])
            
            for w in widgets:
                w.blockSignals(False)
                
            self.plot_manager.view_needs_reset = True
            self.calculate_geometry()