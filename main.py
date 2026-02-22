import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import WyngWindow

if __name__ == "__main__":
    # Initialise l'application Qt
    app = QApplication(sys.argv)
    
    # Crée et affiche la fenêtre principale
    window = WyngWindow()
    window.showMaximized()
    
    # Lance la boucle d'événements de l'application
    sys.exit(app.exec())