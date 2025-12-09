import statistics
from typing import List, Dict, Optional
from abc import ABC, abstractmethod  # Importar el módulo ABC y el decorador abstractmethod
from datetime import datetime  # Reimportar correctamente datetime

# ----------------------
# Clases del modelo
# ----------------------

class Persona(ABC):
    """Clase abstracta padre que representa a una persona en la organización."""
    def __init__(self, id_: str, nombre: str, equipo_id: Optional[str] = None):
        self.id = id_
        self.nombre = nombre
        self.equipo_id = equipo_id

    @abstractmethod
    def mostrar_info(self):
        """Método abstracto que debe ser implementado por las clases hijas."""
        pass


class Agente(Persona):
    """Representa a un agente de ventas monitorizado."""
    def __init__(self, id_: str, nombre: str, equipo_id: Optional[str] = None,
                 llamadas_atendidas: int = 0, total_time_seconds: int = 0,
                 ventas_realizadas: int = 0, meta_ventas: int = 0):
        super().__init__(id_, nombre, equipo_id)
        
        # Verificar si alguno de los valores es negativo
        if llamadas_atendidas < 0 or total_time_seconds < 0 or ventas_realizadas < 0 or meta_ventas < 0:
            raise ValueError("Los valores de llamadas, tiempo, ventas y meta no pueden ser negativos.")
        
        self.llamadas_atendidas = int(llamadas_atendidas)
        self.total_time_seconds = int(total_time_seconds)
        self.ventas_realizadas = int(ventas_realizadas)
        self.meta_ventas = int(meta_ventas)
        # valores calculados
        self.tma = 0.0  # tiempo medio atención (segundos)
        self.tasa_conversion = 0.0  # en %
        self.eficiencia = 0.0  # score compuesto
        self.estado_actual = "OK"  # OK / Atencion / Critico

    def calcular_kpis(self, pesos: Dict[str, float] = None):
        """Calcula TMA, tasa de conversión y eficiencia con pesos opcionales."""
        if self.llamadas_atendidas > 0:
            self.tma = self.total_time_seconds / self.llamadas_atendidas
            self.tasa_conversion = (self.ventas_realizadas / self.llamadas_atendidas) * 100.0
        else:
            self.tma = 0.0
            self.tasa_conversion = 0.0

        # Normalizaciones simples para eficiencia (evitar división por cero)
        # Normalizamos sobre escalas razonables: llamadas (0-100), conversión (0-100), tma inv (0-1)
        def norm_calls(x):
            return min(x / 100.0, 1.0)

        def norm_conv(x):
            return min(x / 100.0, 1.0)

        def norm_tma_inv(tma_seconds):
            # Consideramos 0-600s (10 min) como rango razonable; menor tma -> mejor
            if tma_seconds <= 0:
                return 0.0
            score = max(0.0, min(1.0, (600 - tma_seconds) / 600))
            return score

        if pesos is None:
            pesos = {"llamadas": 0.35, "conversion": 0.45, "tma": 0.20}

        s_ll = norm_calls(self.llamadas_atendidas) * pesos["llamadas"]
        s_cv = norm_conv(self.tasa_conversion) * pesos["conversion"]
        s_tma = norm_tma_inv(self.tma) * pesos["tma"]

        self.eficiencia = (s_ll + s_cv + s_tma) * 100.0  # escala 0-100

        # Estado según umbrales
        if self.eficiencia >= 70:
            self.estado_actual = "OK"
        elif 50 <= self.eficiencia < 70:
            self.estado_actual = "Atención"
        else:
            self.estado_actual = "Crítico"

    def mostrar_info(self):
        """Implementación del método abstracto de la clase base"""
        return f"Agente {self.nombre}, ID: {self.id}, Ventas: {self.ventas_realizadas}"


class JefeEquipo(Persona):
    """Representa a un jefe de equipo que supervisa agentes."""
    def __init__(self, id_: str, nombre: str, equipo_id: Optional[str] = None):
        super().__init__(id_, nombre, equipo_id)
        self.agentes_a_cargo: List[Agente] = []

    def asignar_agente(self, agente: Agente):
        agente.equipo_id = self.equipo_id
        self.agentes_a_cargo.append(agente)

    def mostrar_info(self):
        """Implementación del método abstracto de la clase base"""
        return f"Jefe de equipo: {self.nombre}, ID: {self.id}"


class Equipo:
    """Representa un equipo de ventas."""
    def __init__(self, id_equipo: str, nombre_equipo: str, jefe: Optional[JefeEquipo] = None):
        self.id_equipo = id_equipo
        self.nombre_equipo = nombre_equipo
        self.jefe_equipo = jefe
        if jefe:
            jefe.equipo_id = id_equipo
        self.lista_agentes: List[Agente] = []
        self.promedio_eficiencia: float = 0.0

    def agregar_agente(self, agente: Agente):
        self.lista_agentes.append(agente)

    def calcular_eficiencia_equipo(self):
        if not self.lista_agentes:
            self.promedio_eficiencia = 0.0
            return
        for a in self.lista_agentes:
            a.calcular_kpis()
        vals = [a.eficiencia for a in self.lista_agentes]
        self.promedio_eficiencia = statistics.mean(vals) if vals else 0.0
        return self.promedio_eficiencia


class Reporte:
    """Reporte generado por MonitorDesempeno."""
    def __init__(self, id_reporte: str, tipo: str, fecha: Optional[datetime] = None):
        self.id_reporte = id_reporte
        self.tipo = tipo  # 'individual' o 'equipo'
        self.fecha_generacion = fecha or datetime.now()  # Usar datetime correctamente
        self.datos: Dict = {}

    def agregar_dato(self, clave: str, valor):
        self.datos[clave] = valor

# ----------------------
# Monitor principal
# ----------------------

class MonitorDesempeno:
    """Clase que ingesta datos, calcula KPIs, genera reportes y alertas."""
    def __init__(self, pesos: Dict[str, float] = None, config_umbral: Dict[str, float] = None):
        self.lista_equipos: Dict[str, Equipo] = {}
        self.config_umbral = config_umbral or {"eficiencia_atencion": 70.0, "eficiencia_critico": 50.0}
        self.pesos = pesos or {"llamadas": 0.35, "conversion": 0.45, "tma": 0.20}
        self.reportes_generados: List[Reporte] = []

    def registrar_equipo(self, equipo: Equipo):
        self.lista_equipos[equipo.id_equipo] = equipo

    def procesar_todos(self):
        """Calcula KPIs por agente, eficiencia por equipo y crea reportes básicos."""
        # calcular agentes
        for equipo in self.lista_equipos.values():
            for agente in equipo.lista_agentes:
                agente.calcular_kpis(self.pesos)

        # calcular por equipo
        for equipo in self.lista_equipos.values():
            equipo.calcular_eficiencia_equipo()

        # generar reportes
        self.generar_reportes()

    def generar_reportes(self):
        """Genera reportes por agente y por equipo."""
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")  # Usar datetime correctamente
        agentes_rows = []
        equipos_rows = []

        for equipo in self.lista_equipos.values():
            for agente in equipo.lista_agentes:
                rep = Reporte(f"RAG-{agente.id}-{time_str}", "individual")
                rep.agregar_dato("agente_id", agente.id)
                rep.agregar_dato("agente_nombre", agente.nombre)
                rep.agregar_dato("equipo_id", agente.equipo_id)
                rep.agregar_dato("llamadas_atendidas", agente.llamadas_atendidas)
                rep.agregar_dato("total_time_seconds", agente.total_time_seconds)
                rep.agregar_dato("tma_seconds", round(agente.tma, 2))
                rep.agregar_dato("ventas_realizadas", agente.ventas_realizadas)
                rep.agregar_dato("tasa_conversion_pct", round(agente.tasa_conversion, 2))
                rep.agregar_dato("eficiencia", round(agente.eficiencia, 2))
                rep.agregar_dato("estado_actual", agente.estado_actual)
                self.reportes_generados.append(rep)
                agentes_rows.append(rep.datos)

            # reporte por equipo
            rep_eq = Reporte(f"REQ-{equipo.id_equipo}-{time_str}", "equipo")
            rep_eq.agregar_dato("equipo_id", equipo.id_equipo)
            rep_eq.agregar_dato("equipo_nombre", equipo.nombre_equipo)
            rep_eq.agregar_dato("promedio_eficiencia", round(equipo.promedio_eficiencia, 2))
            rep_eq.agregar_dato("num_agentes", len(equipo.lista_agentes))
            rep_eq.agregar_dato("fecha", rep_eq.fecha_generacion.isoformat())
            self.reportes_generados.append(rep_eq)
            equipos_rows.append(rep_eq.datos)

        # Imprimir el reporte en consola
        self.imprimir_resumen_consola()

    def imprimir_resumen_consola(self):
        """Imprime un resumen amigable por consola."""
        print("\n==== REPORTE RESUMEN (CONSOLA) ====")
        for equipo in self.lista_equipos.values():
            print(f"\n-- Equipo: {equipo.id_equipo} - {equipo.nombre_equipo}")
            print(f"Promedio eficiencia equipo: {round(equipo.promedio_eficiencia, 2)}")
            if not equipo.lista_agentes:
                print(" (sin agentes)")
                continue
            print("Agentes:")
            for a in sorted(equipo.lista_agentes, key=lambda x: x.eficiencia, reverse=True):
                tma_min = round(a.tma / 60.0, 2)
                print(f"  {a.id} | {a.nombre} | Llamadas: {a.llamadas_atendidas} | "
                      f"Ventas: {a.ventas_realizadas} | TMA: {tma_min} min | "
                      f"Conv: {round(a.tasa_conversion, 2)}% | Efic: {round(a.eficiencia, 2)} | Estado: {a.estado_actual}")
        print("====================================\n")

# ----------------------
# Flujo principal de ejecución
# ----------------------

def main():
    def ingresar_agente_manual() -> Agente:
        """Permite ingresar los datos de un agente manualmente."""
        print("Ingresar datos de agente (presione ENTER para valores por defecto 0):")
        id_ = input("ID (ej: A07): ").strip() or "Axx"
        name = input("Nombre: ").strip() or "Sin Nombre"
        calls = int(input("Llamadas atendidas (int): ") or 0)
        total_time = int(input("Total tiempo en segundos (int): ") or 0)
        sales = int(input("Ventas realizadas (int): ") or 0)
        meta = int(input("Meta ventas (int): ") or 0)
        
        # Validación de valores negativos
        if calls < 0 or total_time < 0 or sales < 0 or meta < 0:
            raise ValueError("No se permiten valores negativos para llamadas, tiempo, ventas o metas.")
        
        return Agente(id_, name, llamadas_atendidas=calls, total_time_seconds=total_time,
                      ventas_realizadas=sales, meta_ventas=meta)

    monitor = MonitorDesempeno()
    print("=== Monitoreo Konecta ===")
    print("  1) Ingresar agentes manualmente")
    choice = input("Elija (1): ").strip() or "1"

    equipo = Equipo("E01", "Ventas - Equipo 1")
    jefe = JefeEquipo("J01", "Sonia Alvarez", equipo_id=equipo.id_equipo)
    equipo.jefe_equipo = jefe
    monitor.registrar_equipo(equipo)

    agentes = []
    if choice == "1":
        n = int(input("¿Cuántos agentes desea ingresar? (ej: 2): ") or 0)
        for _ in range(n):
            try:
                ag = ingresar_agente_manual()
                agentes.append(ag)
            except ValueError as e:
                print(f"Error al ingresar datos del agente: {e}")

    for ag in agentes:
        equipo.agregar_agente(ag)

    # Procesar todo
    monitor.procesar_todos()

if __name__ == "__main__":
    main()

