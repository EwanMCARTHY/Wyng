import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox

class FileManager:
    """Classe utilitaire gérant toutes les entrées/sorties de fichiers de l'application."""

    @staticmethod
    def export_results(parent_window, export_text):
        file_path, _ = QFileDialog.getSaveFileName(parent_window, "Sauvegarder la Note de Calcul", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_text)
                QMessageBox.information(parent_window, "Succès", "Note de calcul exportée avec succès.")
            except Exception as e:
                QMessageBox.critical(parent_window, "Erreur", f"Erreur lors de l'exportation : {e}")

    @staticmethod
    def export_cad(parent_window, export_cad_text):
        file_path, _ = QFileDialog.getSaveFileName(parent_window, "Sauvegarder les sections CAO", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_cad_text)
                QMessageBox.information(parent_window, "Succès", "Données CAO exportées avec succès.")
            except Exception as e:
                QMessageBox.critical(parent_window, "Erreur", f"Erreur lors de l'exportation CAO : {e}")

    @staticmethod
    def save_project(parent_window, state_dict):
        file_path, _ = QFileDialog.getSaveFileName(parent_window, "Sauvegarder le projet Wyng", "", "Wyng Project (*.wyng)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_dict, f, indent=4)
                QMessageBox.information(parent_window, "Succès", "Projet sauvegardé avec succès.")
            except Exception as e:
                QMessageBox.critical(parent_window, "Erreur", f"Erreur lors de la sauvegarde : {e}")

    @staticmethod
    def load_project(parent_window):
        file_path, _ = QFileDialog.getOpenFileName(parent_window, "Ouvrir un projet Wyng", "", "Wyng Project (*.wyng)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                return state
            except Exception as e:
                QMessageBox.critical(parent_window, "Erreur", f"Erreur lors du chargement : {e}")
                return None
        return None