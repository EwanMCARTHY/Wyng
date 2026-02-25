import random
from PyQt6.QtCore import QThread, pyqtSignal
from core.drone import Drone

class GeneticOptimizer(QThread):
    # Les signaux permettent à l'IA de parler à l'interface sans la bloquer
    progress_signal = pyqtSignal(int, str)
    plot_signal = pyqtSignal(list, list)
    finished_signal = pyqtSignal(list, float)
    error_signal = pyqtSignal(str)

    def __init__(self, target_mode, max_span, drone_params, selected_airfoil, min_xbatt, max_xbatt, pop_size=80, generations=30, mutation_rate=0.3):
        super().__init__()
        self.target_mode = target_mode
        self.max_span = max_span
        self.drone_params = drone_params
        self.selected_airfoil = selected_airfoil
        self.min_xbatt = min_xbatt
        self.max_xbatt = max_xbatt
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_rate = mutation_rate

    def evaluate(self, genes):
        g_ar, g_sweep, g_dih, g_wash, g_xbatt = genes
        try:
            # Copie des paramètres de base et injection de l'ADN généré
            dp = self.drone_params.copy()
            dp['aspect_ratio'] = g_ar
            dp['sweep_angle'] = g_sweep
            dp['dihedral_angle'] = g_dih
            dp['washout'] = g_wash
            dp['x_batt'] = g_xbatt
            dp['airfoil'] = self.selected_airfoil
            
            drone = Drone(**dp)
            
            if self.target_mode == "Maximiser la Finesse globale (L/D)":
                score = drone.finesse
            elif self.target_mode == "Minimiser la Puissance requise (Autonomie)":
                score = 10000.0 / max(1.0, drone.power_required) 
            else: 
                score = drone.actual_static_margin
            
            # Pénalités sévères pour les contraintes structurelles
            penalty_factor = 1.0
            if drone.main_wing.span > self.max_span:
                penalty_factor *= 0.01 / (1.0 + (drone.main_wing.span - self.max_span)**2)
            if drone.actual_static_margin < 5.0:
                penalty_factor *= 0.01 / (1.0 + (5.0 - drone.actual_static_margin)**2)
            if drone.actual_static_margin > 25.0: 
                penalty_factor *= 0.5 
                 
            score = score * penalty_factor
            
            # Pénalité de complexité pour éviter la dérive génétique
            complexity_penalty = (abs(g_dih) * 0.5) + (abs(g_sweep) * 0.1) + (abs(g_wash) * 0.5)
            score = score * (1.0 - (complexity_penalty / 100.0))
            
            return max(0.01, score)
        except Exception:
            return 0.01

    def run(self):
        try:
            population = []
            for _ in range(self.pop_size):
                population.append([
                    random.uniform(4.0, 20.0),  
                    random.uniform(0.0, 45.0),  
                    random.uniform(0.0, 15.0),  
                    random.uniform(-10.0, 0.0),
                    random.uniform(self.min_xbatt, self.max_xbatt) 
                ])
                
            best_genes = None
            best_fitness = -1
            best_history = []
            avg_history = []

            for gen in range(self.generations):
                scored_pop = [(self.evaluate(ind), ind) for ind in population]
                scored_pop.sort(key=lambda x: x[0], reverse=True)
                
                current_best_fit = scored_pop[0][0]
                avg_fit = sum(s[0] for s in scored_pop) / self.pop_size
                
                if current_best_fit > best_fitness:
                    best_fitness = current_best_fit
                    best_genes = scored_pop[0][1]
                    
                best_history.append(best_fitness)
                avg_history.append(avg_fit)
                
                # Mise à jour de l'interface en temps réel
                self.plot_signal.emit(best_history, avg_history)
                self.progress_signal.emit(gen + 1, f"Génération {gen+1}/{self.generations} en cours...")
                
                # Évolution et sélection naturelle
                new_pop = [scored_pop[0][1].copy(), scored_pop[1][1].copy()]
                survivors = [ind for fit, ind in scored_pop[:self.pop_size//2]]
                
                while len(new_pop) < self.pop_size:
                    p1, p2 = random.sample(survivors, 2)
                    child = [p1[i] if random.random() > 0.5 else p2[i] for i in range(5)]
                    
                    if random.random() < self.mutation_rate:
                        child[0] += random.uniform(-2.0, 2.0)
                        child[1] += random.uniform(-5.0, 5.0)
                        child[2] += random.uniform(-2.0, 2.0)
                        child[3] += random.uniform(-2.0, 2.0)
                        child[4] += random.uniform(-0.1, 0.1)
                        
                    child[0] = max(4.0, min(child[0], 20.0))
                    child[1] = max(0.0, min(child[1], 45.0))
                    child[2] = max(0.0, min(child[2], 15.0))
                    child[3] = max(-10.0, min(child[3], 0.0))
                    child[4] = max(self.min_xbatt, min(child[4], self.max_xbatt))
                    
                    new_pop.append(child)
                    
                population = new_pop

            self.finished_signal.emit(best_genes, best_fitness)
        except Exception as e:
            self.error_signal.emit(str(e))