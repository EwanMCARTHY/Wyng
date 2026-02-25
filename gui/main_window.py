import math
import json
import time
import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton,
                             QFileDialog, QMessageBox, QSlider, QCheckBox,
                             QGroupBox, QGridLayout, QFormLayout, QTabWidget,
                             QApplication, QListWidget, QStackedWidget, QProgressBar)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from core.drone import Drone
from core.airfoil import AirfoilDatabase

class WyngWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyng - Dimensionnement Aérodynamique")
        self.setWindowIcon(QIcon('wyng.ico'))
        self.setMinimumSize(1450, 900) 
        
        self.db = AirfoilDatabase()
        self._setup_ui()

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

    def _on_scroll(self, event):
        if not hasattr(self, 'ax') or event.inaxes != self.ax:
            return
            
        scale_factor = 0.9 if event.button == 'up' else 1.1
        
        xlim = self.ax.get_xlim3d()
        ylim = self.ax.get_ylim3d()
        zlim = self.ax.get_zlim3d()
        
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        z_center = (zlim[0] + zlim[1]) / 2
        
        x_range = (xlim[1] - xlim[0]) * scale_factor / 2
        y_range = (ylim[1] - ylim[0]) * scale_factor / 2
        z_range = (zlim[1] - zlim[0]) * scale_factor / 2
        
        self.ax.set_xlim3d([x_center - x_range, x_center + x_range])
        self.ax.set_ylim3d([y_center - y_range, y_center + y_range])
        self.ax.set_zlim3d([z_center - z_range, z_center + z_range])
        
        self.canvas_3d.draw()

    def reset_3d_view(self):
        self.view_needs_reset = True
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
        
        # --- MENU LATÉRAL THÈME SOMBRE ---
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(180)
        self.nav_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #1e1e1e;
                border-radius: 5px;
                background-color: #2b2b2b;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #3a3a3a;
                color: #e0e0e0;
                font-weight: bold;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
                border-bottom: 1px solid #005a9e;
            }
            QListWidget::item:hover:!selected {
                background-color: #3e3e42;
            }
        """)
        
        self.stacked_widget = QStackedWidget()
        
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

        tab_propulsion = QWidget()
        layout_propulsion = QVBoxLayout(tab_propulsion)
        self.lbl_eta_prop = QLabel("Rendement Hélice : 70 %")
        self.eta_prop_slider = self._create_slider(40, 90, 70, layout_propulsion, self.lbl_eta_prop)
        self.lbl_eta_motor = QLabel("Rendement Moteur : 80 %")
        self.eta_motor_slider = self._create_slider(50, 95, 80, layout_propulsion, self.lbl_eta_motor)
        layout_propulsion.addStretch()
        
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
        layout_opti.addStretch()

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
        # NOUVELLES LIGNES POUR LA DÉRIVE
        self.lbl_vtail_span = QLabel("-") 
        self.lbl_vtail_root = QLabel("-")
        self.lbl_tail_angle = QLabel("-")
        self.tail_layout.addRow("Architecture :", self.lbl_tail_type)
        self.tail_layout.addRow("Envergure (H) :", self.lbl_tail_span)
        self.tail_layout.addRow("Corde emp (H) :", self.lbl_tail_root)
        self.tail_layout.addRow("Envergure (V) :", self.lbl_vtail_span)
        self.tail_layout.addRow("Corde emp (V) :", self.lbl_vtail_root)
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
        
        self.plot_tabs = QTabWidget()
        
        self.tab_3d = QWidget()
        layout_3d = QVBoxLayout(self.tab_3d)
        self.figure_3d = Figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.mpl_connect('scroll_event', self._on_scroll)
        layout_3d.addWidget(self.canvas_3d)
        self.btn_reset_view = QPushButton("Réinitialiser la vue 3D")
        self.btn_reset_view.clicked.connect(self.reset_3d_view)
        layout_3d.addWidget(self.btn_reset_view)
        
        self.tab_vn = QWidget()
        layout_vn = QVBoxLayout(self.tab_vn)
        self.figure_vn = Figure()
        self.canvas_vn = FigureCanvas(self.figure_vn)
        self.ax_vn = self.figure_vn.add_subplot(111)
        layout_vn.addWidget(self.canvas_vn)
        
        self.tab_polars = QWidget()
        layout_polars = QVBoxLayout(self.tab_polars)
        self.figure_polars = Figure()
        self.canvas_polars = FigureCanvas(self.figure_polars)
        layout_polars.addWidget(self.canvas_polars)
        
        self.tab_struct = QWidget()
        layout_struct = QVBoxLayout(self.tab_struct)
        self.figure_struct = Figure()
        self.canvas_struct = FigureCanvas(self.figure_struct)
        layout_struct.addWidget(self.canvas_struct)
        
        self.plot_tabs.addTab(self.tab_3d, "Vue 3D")
        self.plot_tabs.addTab(self.tab_vn, "Diagramme V-n")
        self.plot_tabs.addTab(self.tab_polars, "Polaires Aéro")
        self.plot_tabs.addTab(self.tab_struct, "Structure")
        
        right_layout.addWidget(self.plot_tabs)
        
        main_layout.addLayout(left_main_layout, 2) 
        main_layout.addLayout(right_layout, 3)     

        self.view_needs_reset = True
        self.calculate_geometry()

    def run_ai_optimization(self):
        self.btn_run_opti.setEnabled(False)
        self.lbl_opti_results.setStyleSheet("color: #0078d7; font-weight: bold;")
        self.lbl_opti_results.setText("Initialisation du solveur...")
        
        try:
            max_span = float(self.max_span_input.text().replace(',', '.'))
        except:
            max_span = 2.0
            
        target_mode = self.opti_target_combo.currentText()
            
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
                
            kink_pos = self.kink_pos_slider.value() / 100.0
            kink_angle = self.kink_angle_slider.value() / 10.0
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
            has_winglets = self.winglets_cb.isChecked()
            
            airfoil_name = self.airfoil_combo.currentText()
            selected_airfoil = self.db.get_airfoil(airfoil_name)
        except Exception as e:
            self.lbl_opti_results.setText("Erreur dans les paramètres de base.")
            self.btn_run_opti.setEnabled(True)
            return

        POP_SIZE = 40
        GENERATIONS = 15
        MUTATION_RATE = 0.3
        
        self.opti_progress.setMaximum(GENERATIONS)
        self.opti_progress.setValue(0)
        QApplication.processEvents()

        def evaluate(genes):
            g_ar, g_sweep, g_dih, g_wash = genes
            try:
                drone = Drone(mass=mass, v_stall=v_stall, v_cruise=v_cruise, airfoil=selected_airfoil, 
                              aspect_ratio=g_ar, sweep_angle=g_sweep, dihedral_angle=g_dih, 
                              tail_arm=tail_arm, nose_length=nose, tail_type=tail_type,
                              h_tail_sweep=h_sweep, wing_shape=wing_shape,
                              washout=g_wash, kink_pos=kink_pos, kink_angle=kink_angle,
                              vh=vh, vv=vv, has_winglets=has_winglets,
                              m_motor=m_motor, x_motor=x_motor,
                              num_motors=num_motors, y_motor=y_motor,
                              m_batt=m_batt, x_batt=x_batt,
                              m_payload=m_payload, x_payload=x_payload,
                              eta_prop=eta_prop, eta_motor=eta_motor)
                
                if target_mode == "Maximiser la Finesse globale (L/D)":
                    score = drone.finesse
                elif target_mode == "Minimiser la Puissance requise (Autonomie)":
                    score = 10000.0 / max(1.0, drone.power_required) 
                else: 
                    score = drone.actual_static_margin
                
                if drone.main_wing.span > max_span:
                    score -= (drone.main_wing.span - max_span) * 50
                if drone.actual_static_margin < 5.0:
                    score -= (5.0 - drone.actual_static_margin) * 50
                if drone.actual_static_margin > 25.0: 
                     score -= (drone.actual_static_margin - 25.0) * 10
                     
                return max(0.01, score)
            except:
                return 0.01

        population = []
        for _ in range(POP_SIZE):
            population.append([
                random.uniform(4.0, 20.0),  
                random.uniform(0.0, 45.0),  
                random.uniform(0.0, 15.0),  
                random.uniform(-10.0, 0.0)  
            ])
            
        best_genes = None
        best_fitness = -1

        for gen in range(GENERATIONS):
            scored_pop = [(evaluate(ind), ind) for ind in population]
            scored_pop.sort(key=lambda x: x[0], reverse=True)
            
            current_best_fit = scored_pop[0][0]
            if current_best_fit > best_fitness:
                best_fitness = current_best_fit
                best_genes = scored_pop[0][1]
                
            self.opti_progress.setValue(gen + 1)
            self.lbl_opti_results.setText(f"Génération {gen+1}/{GENERATIONS} en cours de calcul...")
            QApplication.processEvents()
            time.sleep(0.02) 
            
            survivors = [ind for fit, ind in scored_pop[:POP_SIZE//2]]
            new_pop = survivors.copy()
            
            while len(new_pop) < POP_SIZE:
                p1, p2 = random.sample(survivors, 2)
                child = [p1[i] if random.random() > 0.5 else p2[i] for i in range(4)]
                
                if random.random() < MUTATION_RATE:
                    child[0] += random.uniform(-1.5, 1.5)
                    child[1] += random.uniform(-5.0, 5.0)
                    child[2] += random.uniform(-2.0, 2.0)
                    child[3] += random.uniform(-2.0, 2.0)
                    
                child[0] = max(4.0, min(child[0], 20.0))
                child[1] = max(0.0, min(child[1], 45.0))
                child[2] = max(0.0, min(child[2], 15.0))
                child[3] = max(-10.0, min(child[3], 0.0))
                
                new_pop.append(child)
                
            population = new_pop

        self.lbl_opti_results.setStyleSheet("color: green; font-weight: bold;")
        self.lbl_opti_results.setText("Conception générative terminée avec succès.")
        QApplication.processEvents()
        
        if best_genes:
            self.ar_slider.blockSignals(True)
            self.sweep_slider.blockSignals(True)
            self.dihedral_slider.blockSignals(True)
            self.washout_slider.blockSignals(True)
            
            self.ar_slider.setValue(int(best_genes[0] * 10))
            self.sweep_slider.setValue(int(best_genes[1] * 10))
            self.dihedral_slider.setValue(int(best_genes[2] * 10))
            self.washout_slider.setValue(int(best_genes[3] * 10))
            
            self.ar_slider.blockSignals(False)
            self.sweep_slider.blockSignals(False)
            self.dihedral_slider.blockSignals(False)
            self.washout_slider.blockSignals(False)
            
            self.view_needs_reset = True
            self.calculate_geometry()
            
        self.btn_run_opti.setEnabled(True)

    def calculate_geometry(self):
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
                          h_tail_sweep=h_sweep, wing_shape=wing_shape,
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

            # --- CORRECTION DE L'AFFICHAGE DES DIMENSIONS EMPENNAGES ---
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
            self._draw_vn(drone)
            self._draw_polars(drone)
            self._draw_structure(drone)

        except ValueError:
            pass

    def _draw_drone(self, drone):
        if not hasattr(self, 'ax'):
            self.ax = self.figure_3d.add_subplot(111, projection='3d')
            self.view_needs_reset = True
            
        if getattr(self, 'view_needs_reset', False):
            saved_elev = None
            saved_azim = None
            saved_xlim = None
            saved_ylim = None
            saved_zlim = None
        else:
            saved_elev = self.ax.elev
            saved_azim = self.ax.azim
            saved_xlim = self.ax.get_xlim()
            saved_ylim = self.ax.get_ylim()
            saved_zlim = self.ax.get_zlim()
            
        self.ax.clear()
        self.ax.set_title("Visualisation 3D du Projet")
        self.ax.set_xlabel("Axe Longitudinal X (m)")
        self.ax.set_ylabel("Envergure Y (m)")
        self.ax.set_zlabel("Hauteur Z (m)")
        
        def add_symmetric_poly(x_coords, y_coords, z_coords, color, alpha=0.6):
            verts_right = list(zip(x_coords, y_coords, z_coords))
            self.ax.add_collection3d(Poly3DCollection([verts_right], facecolors=color, edgecolors='black', alpha=alpha))
            verts_left = list(zip(x_coords, [-y for y in y_coords], z_coords))
            self.ax.add_collection3d(Poly3DCollection([verts_left], facecolors=color, edgecolors='black', alpha=alpha))

        y_coords = drone.main_wing.outline_y
        x_coords = drone.main_wing.outline_x
        z_coords = [y * math.tan(drone.main_wing.dihedral_angle_rad) for y in y_coords]
        add_symmetric_poly(x_coords, y_coords, z_coords, 'skyblue')

        if drone.main_wing.has_winglets:
            b2 = drone.main_wing.span / 2
            tip_x = drone.main_wing.tip_offset_x
            tip_c = drone.main_wing.tip_chord
            tip_z = b2 * math.tan(drone.main_wing.dihedral_angle_rad)
            winglet_h = b2 * 0.15
            w_x = [tip_x, tip_x + tip_c, tip_x + tip_c * 0.5, tip_x]
            w_y = [b2, b2, b2, b2]
            w_z = [tip_z, tip_z, tip_z + winglet_h, tip_z + winglet_h]
            add_symmetric_poly(w_x, w_y, w_z, 'darkblue', 0.8)

        if drone.tail_type != "Aile Volante":
            arm = drone.tail_arm
            hb2 = drone.h_tail.span / 2
            hcr = drone.h_tail.root_chord
            hct = drone.h_tail.tip_chord
            hoff = drone.h_tail.tip_offset_x
            
            if drone.tail_type in ["Classique", "Empennage en T"]:
                z_htail = 0 if drone.tail_type == "Classique" else drone.v_tail.span
                hx = [arm, arm + hoff, arm + hoff + hct, arm + hcr]
                hy = [0, hb2, hb2, 0]
                hz = [z_htail, z_htail, z_htail, z_htail]
                add_symmetric_poly(hx, hy, hz, 'lightcoral')
                
                vx = [arm, arm + drone.v_tail.tip_offset_x, arm + drone.v_tail.tip_offset_x + drone.v_tail.tip_chord, arm + drone.v_tail.root_chord]
                vy = [0, 0, 0, 0]
                vz = [0, drone.v_tail.span, drone.v_tail.span, 0]
                verts_v = list(zip(vx, vy, vz))
                self.ax.add_collection3d(Poly3DCollection([verts_v], facecolors='darkred', edgecolors='black', alpha=0.6))
                
            elif drone.tail_type == "Empennage en V":
                v_span = drone.v_tail_obj.span / 2
                v_angle_rad = math.radians(drone.v_angle)
                z_tip = v_span * math.sin(v_angle_rad)
                y_tip = v_span * math.cos(v_angle_rad)
                vcr = drone.v_tail_obj.root_chord
                vct = drone.v_tail_obj.tip_chord
                voff = drone.v_tail_obj.tip_offset_x
                vx = [arm, arm + voff, arm + voff + vct, arm + vcr]
                vy = [0, y_tip, y_tip, 0]
                vz = [0, z_tip, z_tip, 0]
                add_symmetric_poly(vx, vy, vz, 'mediumorchid')

        if drone.num_motors == 1:
            self.ax.scatter([drone.x_motor], [0], [0], color='orange', s=40, label='Moteur')
        else:
            z_m = drone.y_motor * math.tan(drone.main_wing.dihedral_angle_rad)
            self.ax.scatter([drone.x_motor, drone.x_motor], [drone.y_motor, -drone.y_motor], [z_m, z_m], color='orange', s=40, label='Moteurs')
            
        self.ax.scatter([drone.x_batt], [0], [0], color='green', s=40, label='Batterie')
        self.ax.scatter([drone.x_payload], [0], [0], color='cyan', s=40, label='Charge U.')
        self.ax.scatter([drone.neutral_point_x], [0], [0], color='blue', marker='x', s=60, label='Foyer')
        self.ax.scatter([drone.cg_x], [0], [0], color='black', marker='o', s=40, label='CG Cible')
        self.ax.scatter([drone.actual_cg_x], [0], [0], color='red', marker='+', s=100, label='CG Réel')

        end_x = drone.tail_arm + (drone.h_tail.root_chord if drone.tail_type != "Aile Volante" else 0)
        self.ax.plot([-drone.nose_length, end_x], [0, 0], [0, 0], color='black', linewidth=1, linestyle='-.')

        if saved_xlim is not None and saved_ylim is not None and saved_zlim is not None:
            self.ax.set_xlim(saved_xlim)
            self.ax.set_ylim(saved_ylim)
            self.ax.set_zlim(saved_zlim)
        else:
            all_x = [-drone.nose_length, end_x, drone.main_wing.root_chord]
            all_y = [-drone.main_wing.span/2, drone.main_wing.span/2]
            all_z = [-0.2, drone.main_wing.tip_offset_z + 0.3]
            
            max_range = max(max(all_x)-min(all_x), max(all_y)-min(all_y)) / 2.0
            mid_x = (max(all_x) + min(all_x)) * 0.5
            mid_y = (max(all_y) + min(all_y)) * 0.5
            mid_z = (max(all_z) + min(all_z)) * 0.5
            
            self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
            self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

        if saved_elev is not None and saved_azim is not None:
            self.ax.view_init(elev=saved_elev, azim=saved_azim)
        else:
            self.ax.view_init(elev=30, azim=-60)

        self.view_needs_reset = False
        
        self.ax.legend(loc='upper right', fontsize='x-small')
        self.canvas_3d.draw()

    def _draw_vn(self, drone):
        self.ax_vn.clear()
        v_list, n_pos, n_neg, v_s, v_a, v_ne, n_max, n_min = drone.get_vn_data()
        
        self.ax_vn.plot(v_list, n_pos, color='blue', linewidth=2, label="Limite Positive (+5g)")
        self.ax_vn.plot(v_list, n_neg, color='red', linewidth=2, label="Limite Négative (-2g)")
        
        self.ax_vn.plot([v_ne, v_ne], [n_min, n_max], color='black', linewidth=2, linestyle='--', label=f"VNE ({v_ne:.1f} m/s)")
        self.ax_vn.plot([v_a, v_a], [0, n_max], color='green', linestyle=':', label=f"Va ({v_a:.1f} m/s)")
        self.ax_vn.plot([v_s, v_s], [0, 1], color='orange', linestyle=':', label=f"Vs ({v_s:.1f} m/s)")
        
        self.ax_vn.axhline(0, color='black', linewidth=1)
        self.ax_vn.axhline(1, color='gray', linewidth=1, linestyle=':')
        
        self.ax_vn.set_title("Diagramme V-n (Enveloppe de vol)")
        self.ax_vn.set_xlabel("Vitesse V (m/s)")
        self.ax_vn.set_ylabel("Facteur de charge n (g)")
        self.ax_vn.grid(True, linestyle='--')
        self.ax_vn.legend(loc='lower left', fontsize='small')
        
        self.ax_vn.fill_between(v_list, n_neg, n_pos, color='green', alpha=0.1)
        
        self.canvas_vn.draw()

    def _draw_polars(self, drone):
        self.figure_polars.clear()
        
        ax1 = self.figure_polars.add_subplot(131)
        ax2 = self.figure_polars.add_subplot(132)
        ax3 = self.figure_polars.add_subplot(133)
        
        alphas, cz_list, cd_list, finesse_list = drone.get_polar_data()
        
        ax1.plot(alphas, cz_list, 'b-', linewidth=2)
        ax1.axhline(0, color='black', linewidth=0.8)
        ax1.axvline(0, color='black', linewidth=0.8)
        ax1.set_title("Portance (Cz) vs Angle (α)")
        ax1.set_xlabel("Angle d'attaque α (°)")
        ax1.set_ylabel("Cz")
        ax1.grid(True, linestyle=':')
        
        ax2.plot(cd_list, cz_list, 'r-', linewidth=2)
        ax2.set_title("Polaire (Cz vs Cx)")
        ax2.set_xlabel("Traînée Cx")
        ax2.set_ylabel("Portance Cz")
        ax2.grid(True, linestyle=':')
        
        ax3.plot(alphas, finesse_list, 'g-', linewidth=2)
        ax3.set_title("Finesse (L/D) vs Angle (α)")
        ax3.set_xlabel("Angle d'attaque α (°)")
        ax3.set_ylabel("Finesse")
        ax3.grid(True, linestyle=':')
        
        self.figure_polars.subplots_adjust(wspace=0.35, bottom=0.15)
        self.canvas_polars.draw()

    def _draw_structure(self, drone):
        self.figure_struct.clear()
        
        ax1 = self.figure_struct.add_subplot(131)
        ax2 = self.figure_struct.add_subplot(132)
        ax3 = self.figure_struct.add_subplot(133)
        
        y_vals, l_dist, v_dist, m_dist, max_shear, max_moment = drone.get_structural_data()
        
        ax1.plot(y_vals, l_dist, 'b-', linewidth=2)
        ax1.fill_between(y_vals, 0, l_dist, color='blue', alpha=0.1)
        ax1.set_title("Répartition de Portance (Schrenk)")
        ax1.set_xlabel("Demi-envergure y (m)")
        ax1.set_ylabel("Portance linéaire L' (N/m)")
        ax1.grid(True, linestyle=':')
        
        ax2.plot(y_vals, v_dist, 'r-', linewidth=2)
        ax2.fill_between(y_vals, 0, v_dist, color='red', alpha=0.1)
        ax2.set_title(f"Effort Tranchant (Max: {max_shear:.0f} N)")
        ax2.set_xlabel("Demi-envergure y (m)")
        ax2.set_ylabel("Effort V (N)")
        ax2.grid(True, linestyle=':')
        
        ax3.plot(y_vals, m_dist, 'g-', linewidth=2)
        ax3.fill_between(y_vals, 0, m_dist, color='green', alpha=0.1)
        ax3.set_title(f"Moment Fléchissant (Max: {max_moment:.1f} N.m)")
        ax3.set_xlabel("Demi-envergure y (m)")
        ax3.set_ylabel("Moment M (N.m)")
        ax3.grid(True, linestyle=':')
        
        self.figure_struct.subplots_adjust(wspace=0.35, bottom=0.15)
        self.canvas_struct.draw()

    def export_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la Note de Calcul", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.export_text)
                QMessageBox.information(self, "Succès", "Note de calcul exportée avec succès.")
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

    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder le projet Wyng", "", "Wyng Project (*.wyng)")
        if file_path:
            try:
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
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=4)
                QMessageBox.information(self, "Succès", "Projet sauvegardé avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde : {e}")

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un projet Wyng", "", "Wyng Project (*.wyng)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                widgets = [
                    self.mass_input, self.vstall_input, self.vcruise_input, self.speed_unit_combo,
                    self.airfoil_combo, self.wing_shape_combo, self.ar_slider, self.sweep_slider,
                    self.dihedral_slider, self.kink_pos_slider, self.kink_angle_slider, self.washout_slider,
                    self.winglets_cb, self.tail_combo, self.tailarm_slider, self.nose_slider,
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
                    
                self.view_needs_reset = True
                self.calculate_geometry()
                QMessageBox.information(self, "Succès", "Projet chargé avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement : {e}")